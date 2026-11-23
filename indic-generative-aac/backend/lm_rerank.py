"""
lm_rerank.py - optional GPU re-ranker for the next-word shortlist (best system "I" in paper/.../20_nov_changes.md).

The CPU predictor (predictor_v2.py) proposes candidates; this module re-scores the top K of them with BLOOM-560m + a small
LoRA adapter per language (adapters in lm_adapters/, trained on the AAC train split) and mixes: 0.1 * CPU + 0.9 * LM.
Measured (full test sets, KSR, CPU-only -> with LM, K=20): en 57.5 -> ~61, hi 58.3 -> 60.6, mr 51.9 -> 54.1, gu 55.6 -> 57.4.

Switch:   AAC_LM=auto (default: on when CUDA + base model + adapter are available) | 1 (same, but log why it is off) | 0 (off)
Tunables: AAC_LM_K (shortlist size, default 50: best on dev in all 4 languages, Step 12), AAC_LM_W (CPU weight, default 0.1)
Any failure (no GPU, out of memory, bad adapter) -> the caller keeps the CPU ranking; after an error the LM is skipped for 60 s.
"""
import collections
import math
import os
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ADAPTERS = os.path.join(HERE, "lm_adapters")
MODEL = os.environ.get("AAC_LM_MODEL", "bigscience/bloom-560m")
K = int(os.environ.get("AAC_LM_K", "50"))
W_CPU = float(os.environ.get("AAC_LM_W", "0.1"))
MODE = os.environ.get("AAC_LM", "auto").lower()
CHUNK = 16                           # candidates per GPU batch
CACHE_MAX = 2000                     # contexts kept in the score cache (experiments raise it)

_lock = threading.Lock()
_state = {"ready": False, "failed": None, "retry_at": 0.0, "lang": None}
_m = _tok = _bos = None
_adapters = {}                       # lang -> {param name: cuda tensor}
_cache = collections.OrderedDict()   # (lang, ctx) -> {word: logp}
_last_ms = [0.0]


def _load():
    """Load the base model once and wrap its linear layers with (switchable) LoRA parameters."""
    global _m, _tok, _bos
    import torch
    import torch.nn as nn
    from transformers import AutoModelForCausalLM, AutoTokenizer
    if not torch.cuda.is_available():
        raise RuntimeError("no CUDA device")
    _tok = AutoTokenizer.from_pretrained(MODEL)
    _bos = _tok.bos_token_id if _tok.bos_token_id is not None else _tok.eos_token_id
    m = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16).cuda().eval()
    m.requires_grad_(False)

    class LoRA(nn.Module):
        def __init__(self, base, r=16, alpha=32):
            super().__init__()
            self.base = base
            self.A = nn.Parameter(torch.zeros(base.in_features, r, device="cuda"), requires_grad=False)
            self.B = nn.Parameter(torch.zeros(r, base.out_features, device="cuda"), requires_grad=False)
            self.s = alpha / r

        def forward(self, x):
            y = self.base(x)
            return y + ((x.float() @ self.A) @ self.B * self.s).to(y.dtype)

    for mod in list(m.modules()):
        for nm, ch in list(mod.named_children()):
            if nm in ("query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h") and isinstance(ch, nn.Linear):
                setattr(mod, nm, LoRA(ch))
    for lang in ("en", "hi", "mr", "gu"):
        p = os.path.join(ADAPTERS, lang + ".pt")
        if os.path.exists(p):
            _adapters[lang] = {k: v.cuda() for k, v in torch.load(p, map_location="cpu").items()}
    if not _adapters:
        raise RuntimeError("no adapters in " + ADAPTERS)
    _m = m


def _ensure():
    if time.time() < _state["retry_at"]:                         # paused after an error
        return False
    if _state["ready"]:
        return True
    with _lock:
        if _state["ready"]:
            return True
        try:
            _load()
            _state["ready"] = True
            _state["failed"] = None
        except Exception as e:                                   # no GPU / no model / no adapters: stay on CPU
            _state["failed"] = repr(e)[:200]
            _state["retry_at"] = time.time() + (3600 if "no CUDA" in _state["failed"] else 300)   # e.g. GPU full: try again in 5 min
            _adapters.clear()
            try:
                import torch
                torch.cuda.empty_cache()                         # release the half-loaded model
            except Exception:
                pass
            if MODE == "1":
                print("[lm_rerank] disabled:", _state["failed"])
    return _state["ready"]


def enabled(lang):
    if MODE in ("0", "off", "false"):
        return False
    return os.path.exists(os.path.join(ADAPTERS, lang + ".pt"))


def warm_up(langs=("en", "hi", "mr", "gu")):
    """Load the model and run one query per language (called from a background thread at start-up)."""
    if MODE in ("0", "off", "false") or not _ensure():
        return
    for l in langs:
        if l in _adapters:
            try:
                _logp(l, [], ["a"])
            except Exception:
                pass


def _logp(lang, ctx, cands):
    import torch
    key = (lang, tuple(ctx))
    sc = _cache.get(key)
    if sc is None:
        sc = _cache[key] = {}
        if len(_cache) > CACHE_MAX:
            _cache.popitem(last=False)
    else:
        _cache.move_to_end(key)
    miss = [w for w in cands if w not in sc]
    if miss:
        with _lock, torch.no_grad():
            if _state["lang"] != lang:                           # swap the 25 MB adapter in place (a few ms)
                _m.load_state_dict(_adapters[lang], strict=False)
                _state["lang"] = lang
            text = " ".join(ctx)
            base = [_bos] + (_tok(text, add_special_tokens=False)["input_ids"] if text else [])
            for c0 in range(0, len(miss), CHUNK):                # small batches: the 250k-word output layer is large
                part = miss[c0:c0 + CHUNK]
                ws = [_tok((" " if ctx else "") + w, add_special_tokens=False)["input_ids"] for w in part]
                L = len(base) + max(map(len, ws))
                ids = torch.full((len(part), L), _tok.pad_token_id)
                att = torch.zeros((len(part), L), dtype=torch.long)
                for j, w in enumerate(ws):
                    s_ = base + w
                    ids[j, :len(s_)] = torch.tensor(s_)
                    att[j, :len(s_)] = 1
                h = _m.transformer(input_ids=ids.cuda(), attention_mask=att.cuda()).last_hidden_state[:, len(base) - 1:]
                lp = torch.log_softmax(_m.lm_head(h).float(), -1)
                for j, w in enumerate(ws):
                    sc[part[j]] = sum(lp[j, k, t].item() for k, t in enumerate(w))
                del h, lp
    return [sc[w] for w in cands]


def rerank(lang, ctx, ranked, k=None, w_cpu=None):
    """ranked: [(cpu_score, word), ...] best first.  Returns the same kind of list, with the top k re-scored by the LM
    (and the rest left after them), or None when the LM is unavailable so the caller keeps the CPU order."""
    k = k or K
    w_cpu = W_CPU if w_cpu is None else w_cpu
    if not ranked or not enabled(lang) or not _ensure() or lang not in _adapters:
        return None
    head = ranked[:k]
    try:
        t0 = time.perf_counter()
        lp = _logp(lang, list(ctx), [w for _, w in head])
        _last_ms[0] = 1000 * (time.perf_counter() - t0)
    except Exception as e:                                       # e.g. CUDA out of memory: fall back, retry later
        _state["failed"] = repr(e)[:200]
        _state["retry_at"] = time.time() + 60
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass
        return None
    mx = max(lp)
    e = [math.exp(x - mx) for x in lp]
    z = sum(e)
    zc = sum(s for s, _ in head) or 1.0
    mixed = [(w_cpu * s / zc + (1 - w_cpu) * p / z, w) for (s, w), p in zip(head, e)]
    mixed.sort(key=lambda x: -x[0])
    return mixed + list(ranked[k:])


def status():
    return {"mode": MODE, "ready": _state["ready"], "failed": _state["failed"], "k": K, "w_cpu": W_CPU,
            "adapters": sorted(_adapters), "last_ms": round(_last_ms[0], 1)}
