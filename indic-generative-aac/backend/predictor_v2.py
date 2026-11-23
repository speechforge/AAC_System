"""
predictor_v2.py - improved CPU next-word / word-completion predictor (en, hi, mr, gu), no GPU needed.

Measured against the shipped infinity_gram.py predictor in paper/baseline_system_paper_of_AAC_system/20_nov_changes.md
(KSR, higher is better; full test sets, mean of AAC+caregiver):  en 56.29 -> 57.49,  hi 56.74 -> 58.28,
mr 48.73 -> 51.86,  gu 53.04 -> 55.60.

What it adds over the shipped predictor
  1. One model per language (the shipped engine sends Gujarati to the English trie and Marathi to the Hindi trie).
  2. Already-selected words are NOT excluded (a repeated word such as "to ... to" is legitimate); callers dedupe if they want.
  3. Context is capped (per language, tuned on dev) before the infinity-gram back-off.
  4. Word distribution = w * infinity-gram + (1 - w) * character 12-gram (Witten-Bell), tuned on dev.
  5. Coverage fallback: when a typed prefix of >= 2 characters is given, up to 5 character-12-gram beam-search completions that
     are NOT in the training vocabulary join the candidate pool (words never seen in training).

Public API:  predict(words, language, prefix="", top_k=10) -> list of {"word","prob","emoji","order","order_label","source"}
The module is import-safe: nothing is trained until the first request for a language (lazy, thread-safe).
"""
import collections
import json
import math
import os
import re
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "predictor_data")

# Knobs tuned on DEV only (paper/.../our_experiments_vs_baseline/results/final_<lang>.json, step4_<lang>.json).
PARAMS = {
    "en": {"ctx_cap": 3, "backoff": 0.2, "w_inf": 0.85},
    "hi": {"ctx_cap": 4, "backoff": 0.2, "w_inf": 0.70},
    "mr": {"ctx_cap": 2, "backoff": 0.2, "w_inf": 0.70},
    "gu": {"ctx_cap": 2, "backoff": 0.6, "w_inf": 0.70},
}
POOL_N = 300          # candidate pool: most frequent training words that match the typed prefix
COV_M = 5             # extra out-of-vocabulary completions
COV_MINLEN = 2        # only when at least this many characters were typed
COV_WIDTH, COV_STEPS = 8, 10

SCRIPT = {"en": r"[a-z']+", "hi": r"[ऀ-ॣ०-ॿ]+", "mr": r"[ऀ-ॣ०-ॿ]+", "gu": r"[઀-૰૱-૿]+"}
LANGS = tuple(SCRIPT)


def words_of(text, lang):
    t = text.lower() if lang == "en" else text
    if lang == "en":
        t = t.replace("’", "'")
    return re.findall(SCRIPT[lang], t)


class CharNgram:
    """Character n-gram, Witten-Bell interpolation."""

    def __init__(self, order=12):
        self.n = order
        self.cnt = collections.defaultdict(collections.Counter)
        self.alpha = set()
        self.memo = {}

    def train(self, sentences):
        for s in sentences:
            t = "^" * (self.n - 1) + s
            for i in range(self.n - 1, len(t)):
                c = t[i]
                self.alpha.add(c)
                for k in range(0, self.n):
                    self.cnt[t[i - k:i]][c] += 1
        self.alpha.add(" ")
        self.V = len(self.alpha) + 1
        self.tot = {h: sum(c.values()) for h, c in self.cnt.items()}
        self.typ = {h: len(c) for h, c in self.cnt.items()}
        return self

    def p(self, hist, c):
        h = ("^" * (self.n - 1) + hist)[-(self.n - 1):] if self.n > 1 else ""
        key = (h, c)
        r = self.memo.get(key)
        if r is not None:
            return r
        pr = 1.0 / self.V
        for k in range(0, self.n):
            ctx = h[len(h) - k:] if k else ""
            T = self.tot.get(ctx)
            if not T:
                break
            lam = T / (T + self.typ[ctx])
            pr = lam * (self.cnt[ctx].get(c, 0) / T) + (1 - lam) * pr
        if len(self.memo) > 400000:        # bounded cache for a long-running server
            self.memo.clear()
        self.memo[key] = pr
        return pr

    def logp_str(self, hist, s):
        lp = 0.0
        for i, c in enumerate(s):
            lp += math.log(self.p(hist + s[:i], c))
        return lp


class _Node:
    __slots__ = ("count", "children")

    def __init__(self):
        self.count = 0
        self.children = {}


def _softnorm(sc):
    m = max(sc)
    e = [math.exp(x - m) for x in sc]
    z = sum(e)
    return [x / z for x in e]


class LangModel:
    """Everything for one language, built from a list of normalised sentences (words joined by single spaces)."""

    def __init__(self, lang, sentences, params=None, cov=True):
        self.lang = lang
        self.params = dict(PARAMS[lang], **(params or {}))
        self.use_cov = cov
        self.root = _Node()
        self.uni = collections.Counter()
        self.start = collections.Counter()
        for s in sentences:
            ws = s.split()
            if not ws:
                continue
            self.start[ws[0]] += 1
            self.uni.update(ws)
            for i in range(len(ws)):               # all suffixes -> longest-suffix lookup
                node = self.root
                node.count += 1
                for w in ws[i:]:
                    node = node.children.setdefault(w, _Node())
                    node.count += 1
        self.T = sum(self.uni.values()) or 1
        self.cm = CharNgram(12).train(sentences)
        self.ranked = [w for w, _ in self.uni.most_common()]
        self._pool_cache, self._cand_cache = {}, {}
        self.n_sentences = len(sentences)

    # ---- candidates -------------------------------------------------------------------------------------------------------
    def pool(self, prefix):
        r = self._pool_cache.get(prefix)
        if r is None:
            r = [w for w in self.ranked if w.startswith(prefix)][:POOL_N]
            if len(self._pool_cache) > 5000:
                self._pool_cache.clear()
            self._pool_cache[prefix] = r
        return r

    def candidates(self, prefix):
        """Pool plus up to COV_M out-of-vocabulary completions found by char-12-gram beam search."""
        r = self._cand_cache.get(prefix)
        if r is not None:
            return r
        base = self.pool(prefix)
        r = list(base)
        if self.use_cov and len(prefix) >= COV_MINLEN and COV_M > 0:
            beams, done = [(0.0, prefix)], []
            for _ in range(COV_STEPS):
                nb = []
                for lp, w in beams:
                    for c in self.cm.alpha:
                        q = lp + math.log(self.cm.p(" " + w, c))
                        (done if c == " " else nb).append((q, w if c == " " else w + c))
                beams = sorted(nb, reverse=True)[:COV_WIDTH]
                if not beams:
                    break
            seen = set(r)
            for _, w in sorted(done, reverse=True):
                if w not in seen and w != prefix:
                    r.append(w)
                    seen.add(w)
                if len(r) >= len(base) + COV_M:
                    break
        if len(self._cand_cache) > 5000:
            self._cand_cache.clear()
        self._cand_cache[prefix] = r
        return r

    # ---- scoring ----------------------------------------------------------------------------------------------------------
    def _inf_dist(self, ctx):
        cand = collections.defaultdict(float)
        weight, alpha = 1.0, self.params["backoff"]
        for st in range(len(ctx)):
            node = self.root
            for w in ctx[st:]:
                node = node.children.get(w)
                if node is None:
                    break
            if node is not None and node.children:
                tt = sum(c.count for c in node.children.values())
                for w, c in node.children.items():
                    cand[w] += c.count / tt * weight
            weight *= alpha
        if not ctx:
            t = sum(self.start.values()) or 1
            for w, c in self.start.items():
                cand[w] += c / t
        z = sum(cand.values()) or 1.0
        return {w: v / z for w, v in cand.items()}

    def score(self, ctx, cands):
        """Probability-like score of each candidate word given the context words (sums to 1 over cands)."""
        cap = self.params["ctx_cap"]
        c = ctx[-cap:] if cap else ctx
        d = self._inf_dist(c)
        raw = [d.get(w, 0.0) + 1e-6 * self.uni.get(w, 0) / self.T + 1e-12 for w in cands]
        z = sum(raw)
        inf = [x / z for x in raw]
        hist = " ".join(ctx) + (" " if ctx else "")
        chs = _softnorm([self.cm.logp_str(hist, w + " ") for w in cands])
        w_inf = self.params["w_inf"]
        return [w_inf * a + (1 - w_inf) * b for a, b in zip(inf, chs)]

    def rank(self, ctx, prefix=""):
        cands = self.candidates(prefix)
        if not cands:
            return []
        sc = self.score(list(ctx), cands)
        return sorted(zip(sc, cands), key=lambda x: -x[0])


# ───────────────────────────────────────────────── loading / serving ─────────────────────────────────────────────────────
_models = {}
_lock = threading.Lock()


def load_sentences(lang):
    """Training sentences for a language: predictor_data/<lang>.txt (one normalised sentence per line)."""
    p = os.path.join(DATA_DIR, f"{lang}.txt")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def get_model(lang):
    m = _models.get(lang)
    if m is None:
        with _lock:
            m = _models.get(lang)
            if m is None:
                sents = load_sentences(lang)
                if not sents:
                    return None
                m = LangModel(lang, sents)
                _models[lang] = m
    return m


def available(lang):
    return os.path.exists(os.path.join(DATA_DIR, f"{lang}.txt"))


def predict(words, language, prefix="", top_k=10, emojis=None, use_lm=True):
    """Ranked predictions for the next word (prefix == "") or the completion of a typed prefix.
    Returns [] when the language has no training data (caller falls back to the legacy predictor)."""
    if language not in LANGS:
        return []
    m = get_model(language)
    if m is None:
        return []
    ctx = [w for t in words for w in words_of(t, language)]
    pre = "".join(words_of(prefix or "", language)) if prefix else ""
    full = m.rank(ctx, pre)
    src = "model"
    if use_lm and full:                                    # optional GPU re-ranking of the shortlist (lm_rerank.py)
        try:
            import lm_rerank
            lm = lm_rerank.rerank(language, ctx, full)
            if lm is not None:
                full, src = lm, "model+lm"
        except Exception:
            pass                                           # any LM problem: keep the CPU ranking
    ranked = full[:top_k]
    tot = sum(s for s, _ in ranked) or 1.0
    emojis = emojis or {}
    return [{"word": w, "prob": round(s / tot, 3), "emoji": emojis.get(w, "✨" if language != "en" else "💬"),
             "order": 0, "order_label": "v2", "source": src} for s, w in ranked]


def stats():
    return {"languages_loaded": {l: {"sentences": m.n_sentences, "vocab": len(m.uni)} for l, m in _models.items()},
            "languages_available": [l for l in LANGS if available(l)], "params": PARAMS, "cov_m": COV_M}
