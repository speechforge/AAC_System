"""(shared setup copied from exp_step2.py) Step 2: adapt a multilingual LM (BLOOM-560m, LoRA) on the language's AAC train text and use it as the next-word ranker.
Controls: shipped CPU engine (A), improved CPU stack (E), pretrained BLOOM (zero-shot), adapted BLOOM, CPU stack + adapted BLOOM hybrid.
All knobs (epochs, mix weight) chosen on DEV. Test = random N+N test sentences (same sample for every system) + per-character perplexity on the FULL test set.
   python exp_step2.py <lang> [N]"""
import sys, json, math, random, time, torch, torch.nn as nn
from lib import *
from exp_improve_lib import softnorm
from exp_final import capped_scorer, mix, run_stream, boot_ci
from transformers import AutoTokenizer, AutoModelForCausalLM
lang = sys.argv[1]; N = 100; KK = int(sys.argv[2])
random.seed(0); torch.manual_seed(0)
train = sents(lang, "train"); dev = sents(lang, "dev"); full = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}
sub = full   # step 3: FULL test sets
name = "bigscience/bloom-560m"; tok = AutoTokenizer.from_pretrained(name); BOS = tok.bos_token_id if tok.bos_token_id is not None else tok.eos_token_id
m = AutoModelForCausalLM.from_pretrained(name, torch_dtype=torch.float16).cuda(); m.requires_grad_(False)
LORA_ON = [False]
class LoRA(nn.Module):
    def __init__(self, base, r=16, alpha=32):
        super().__init__(); self.base = base; self.A = nn.Parameter(torch.randn(base.in_features, r, device="cuda") * 0.01); self.B = nn.Parameter(torch.zeros(r, base.out_features, device="cuda")); self.s = alpha / r
    def forward(self, x):
        y = self.base(x)
        return y + ((x.float() @ self.A) @ self.B * self.s).to(y.dtype) if LORA_ON[0] else y
n_l = 0
for mod in list(m.modules()):
    for nm_, ch in list(mod.named_children()):
        if nm_ in ("query_key_value", "dense", "dense_h_to_4h", "dense_4h_to_h") and isinstance(ch, nn.Linear): setattr(mod, nm_, LoRA(ch)); n_l += 1
params = [p for p in m.parameters() if p.requires_grad]; print("lora layers", n_l, "trainable", sum(p.numel() for p in params), flush=True)

def enc_batch(texts):
    ids = [[BOS] + tok(t, add_special_tokens=False)["input_ids"] for t in texts]; L = max(map(len, ids))
    x = torch.full((len(ids), L), tok.pad_token_id); a = torch.zeros((len(ids), L), dtype=torch.long)
    for i, s in enumerate(ids): x[i, :len(s)] = torch.tensor(s); a[i, :len(s)] = 1
    return x.cuda(), a.cuda()
def seq_logp(texts, bs=4):          # per-sentence natural-log prob of all tokens after BOS
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), bs):
            x, a = enc_batch(texts[i:i+bs]); lg = m(input_ids=x, attention_mask=a).logits[:, :-1].float()
            lp = torch.log_softmax(lg, -1).gather(-1, x[:, 1:, None])[..., 0] * a[:, 1:]; out += lp.sum(1).tolist()
    return out
def char_ppl_lm(texts):
    lp = seq_logp(texts); n = sum(len(t) for t in texts); return math.exp(-sum(lp) / n)

cache = {}
@torch.no_grad()
def lm_scorer(ctx, cands):
    key = (LORA_ON[0], tuple(ctx)); sc = cache.setdefault(key, {}); miss = [w for w in cands if w not in sc]
    text = " ".join(ctx); base_ids = [BOS] + (tok(text, add_special_tokens=False)["input_ids"] if text else [])
    for i in range(0, len(miss), 64):
        ch = miss[i:i+64]; ws = [tok((" " if ctx else "") + w, add_special_tokens=False)["input_ids"] for w in ch]
        L = len(base_ids) + max(map(len, ws)); ids = torch.full((len(ch), L), tok.pad_token_id); att = torch.zeros((len(ch), L), dtype=torch.long)
        for j, w in enumerate(ws): s_ = base_ids + w; ids[j, :len(s_)] = torch.tensor(s_); att[j, :len(s_)] = 1
        h = m.transformer(input_ids=ids.cuda(), attention_mask=att.cuda()).last_hidden_state[:, len(base_ids)-1:]
        lp = torch.log_softmax(m.lm_head(h).float(), -1)
        for j, w in enumerate(ws): sc[ch[j]] = sum(lp[j, k, t].item() for k, t in enumerate(w))
    return softnorm([sc[w] for w in cands])


import statistics, os
class ExtPool:
    """pool + M char-LM completions of the prefix that the pool does not contain (words outside the training vocabulary)."""
    def __init__(self, pool, cm, M=5, minlen=2, width=8, extra=10):
        self.pool, self.cm, self.M, self.minlen, self.width, self.extra = pool, cm, M, minlen, width, extra; self.freq = pool.freq; self.cache = {}
    def get(self, prefix):
        r = self.cache.get(prefix)
        if r is None:
            r = list(self.pool.get(prefix))
            if len(prefix) >= self.minlen and self.M > 0:
                beams = [(0.0, prefix)]; done = []
                for _ in range(self.extra):
                    nb = []
                    for lp, w in beams:
                        for c in self.cm.alpha:
                            q = lp + math.log(self.cm.p(" " + w, c))
                            (done if c == " " else nb).append((q, w if c == " " else w + c))
                    beams = sorted(nb, reverse=True)[: self.width]
                    if not beams: break
                seen = set(r)
                for _, w in sorted(done, reverse=True):
                    if w not in seen and w != prefix: r.append(w); seen.add(w)
                    if len(r) >= len(self.pool.get(prefix)) + self.M: break
            self.cache[prefix] = r
        return r


res = {"lang": lang, "model": name, "eval": "FULL test sets", "n_test": {k: len(v) for k, v in full.items()}}
t0 = time.time(); cm = CharNgram(12).train(train)
ckpt = f"results/lora_{lang}.pt"
if os.path.exists(ckpt):
    LORA_ON[0] = True; m.load_state_dict(torch.load(ckpt), strict=False); m.eval(); res["adapter"] = "loaded " + ckpt
else:
    LORA_ON[0] = True; opt = torch.optim.AdamW(params, lr=2e-4, weight_decay=0.0); scaler = torch.cuda.amp.GradScaler(); best = (1e9, None, 0)
    for ep in range(1, 4):
        d = train[:]; random.shuffle(d); m.train()
        for i in range(0, len(d), 16):
            for j in range(i, min(i + 16, len(d)), 4):
                x, a = enc_batch(d[j:j+4]); lg = m(input_ids=x, attention_mask=a).logits[:, :-1].float()
                loss = nn.functional.cross_entropy(lg.reshape(-1, lg.shape[-1]), x[:, 1:].reshape(-1), ignore_index=tok.pad_token_id) / 4
                scaler.scale(loss).backward()
            scaler.step(opt); scaler.update(); opt.zero_grad()
        m.eval(); dp = char_ppl_lm(dev); print("epoch", ep, "dev char-ppl", round(dp, 3), flush=True)
        if dp < best[0]: best = (dp, {k: v.clone() for k, v in m.state_dict().items() if ".A" in k or ".B" in k}, ep)
    m.load_state_dict(best[1], strict=False); torch.save(best[1], ckpt); res["adapter"] = f"trained, best epoch {best[2]}, dev char-ppl {best[0]:.3f}"
    res["char_ppl_full_test"] = {"char12": char_ppl(lambda s: cm.logp_str("", s), full["aac"] + full["care"])[0], "bloom_adapted": char_ppl_lm(full["aac"] + full["care"])}
e = make_engine(train, lang); pool = Pool(train, 300); xp = ExtPool(pool, cm, M=5); tuned = json.load(open(f"results/final_{lang}.json"))[lang]["tuned"]
C, a_ = tuned["step1+5 ctx_cap,alpha"]; wch = tuned["step2 mix_weight_infgram"]
chs = lambda ctx, cands, f=charlm_scorer(cm): softnorm(f(ctx, cands))
cpu = mix(capped_scorer(e, C, a_), chs, wch); times = []
def prefilter(K, w):
    def sc(ctx, cands):
        c = cpu(ctx, cands); idx = sorted(range(len(cands)), key=lambda i: -c[i])[:K]
        t = time.perf_counter(); l = lm_scorer(ctx, [cands[i] for i in idx]); torch.cuda.synchronize(); times.append(time.perf_counter() - t)
        z = sum(c[i] for i in idx); out = [-1.0] * len(cands)
        for r, i in enumerate(idx): out[i] = w * c[i] / z + (1 - w) * l[r]
        return out
    return sc
res["chosen_cpu_weight"] = w = 0.1; res["K"] = KK; times.clear()
systems = [("A shipped infinity-gram", inf_shipped_scorer(e, pool), pool), ("E+COV (CPU only)", cpu, xp), (f"I_K{KK} = E+COV top-{KK} + adapted BLOOM (w_cpu={w})", prefilter(KK, w), xp)]
res["systems"] = {}; per = {}
for nm, sc, pl in systems:
    r = {}; per[nm] = {}; tt = time.time()
    for k, v in full.items():
        s_, p, h = run_stream(v, sc, pl); r[k] = dict(ksr_pct=s_, top1=h[1], top3=h[3], top5=h[5], top10=h[10]); per[nm][k] = p
    r["avg_ksr"] = (r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2; r["wall_s"] = time.time() - tt; res["systems"][nm] = r
    print(lang, nm, round(r["avg_ksr"], 2), round((r["aac"]["top5"] + r["care"]["top5"]) / 2, 1), round(r["wall_s"]), "s", flush=True)
    json.dump(res, open(f"results/step8_{lang}_K{KK}.json", "w"), indent=1)
names = list(res["systems"])
for nm in names[1:]:
    res["systems"][nm]["gain_vs_shipped_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per[names[0]][k], per[nm][k])] for k in full}
res["systems"][names[2]]["gain_vs_E+COV_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per[names[1]][k], per[names[2]][k])] for k in full}
res["seconds"] = time.time() - t0; json.dump(res, open(f"results/step8_{lang}_K{KK}.json", "w"), indent=1)
