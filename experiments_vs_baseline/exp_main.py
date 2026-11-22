"""Experiments 1-3 for one language: per-char perplexity, keystroke savings (5 predictions), next-word hit rates, latency, ablation."""
import sys, json, time, math, random
from lib import *
lang = sys.argv[1]
train = sents(lang, "train"); dev = sents(lang, "dev")
tests = {"aac": sents(lang, "test", ("aac",)), "care": sents(lang, "test", ("care",))}
tests["all"] = tests["aac"] + tests["care"]
res = {"lang": lang, "n_train": len(train), "n_dev": len(dev), **{f"n_test_{k}": len(v) for k, v in tests.items()},
       "test_words": {k: sum(len(s.split()) for s in v) for k, v in tests.items()},
       "test_chars": {k: sum(len(s) for s in v) for k, v in tests.items()}}
t0 = time.time()
cm = CharNgram(12).train(train)
e = make_engine(train, lang)
pool = Pool(train, 300)
oov = {k: 100 * sum(w not in pool.freq for s in v for w in s.split()) / sum(len(s.split()) for s in v) for k, v in tests.items()}
res["oov_rate_pct"] = oov

# ── Exp 1: per-character perplexity (dev-tuned mixing weights for the open-vocab ∞-gram) ──
best = None
for mu in (0.02, 0.1, 0.3, 0.5):
    for eps in (0.05, 0.1, 0.3, 0.5, 0.7):
        p, _ = char_ppl(inf_logp_fn(e, cm, mu, eps), dev[:200])
        if best is None or p < best[0]: best = (p, mu, eps)
res["inf_dev_tuned"] = dict(dev_ppl=best[0], mu=best[1], eps=best[2])
lp_inf = inf_logp_fn(e, cm, best[1], best[2])
lp_chr = lambda s: cm.logp_str("", s)
res["perplexity"] = {}
for k, v in tests.items():
    pc, n = char_ppl(lp_chr, v); pi, _ = char_ppl(lp_inf, v)
    res["perplexity"][k] = {"char12_ngram": pc, "inf_gram_openvocab": pi}
print("ppl", res["perplexity"], flush=True)

# ── Exp 2: keystroke savings with 5 word predictions + next-word hit rates ──
uni = collections.Counter(pool.freq)
sys_pred = {
    "freq_only": predictor_from_scorer(lambda ctx, c: [uni[w] for w in c], pool),
    "char12_ngram": predictor_from_scorer(charlm_scorer(cm), pool),
    "inf_gram_shipped": predictor_from_scorer(inf_shipped_scorer(e, pool), pool),
}
# ablation: cap the context depth (2-gram / 4-gram-like) vs arbitrary depth
for n in (1, 2, 3):
    sc = inf_shipped_scorer(e, pool)
    sys_pred[f"inf_gram_ctx_cap{n}"] = predictor_from_scorer((lambda sc, n: (lambda ctx, c: sc(ctx[-n:], c)))(sc, n), pool)
res["ksr"] = {}
for name, pr in sys_pred.items():
    res["ksr"][name] = {}
    for k, v in tests.items():
        s, ka, kp, hits, nw = ksr(v, pr)
        res["ksr"][name][k] = dict(ksr_pct=s, ka=ka, kp=kp, nwords=nw, hit_at_empty_prefix_pct=hits)
    print(name, {k: round(res["ksr"][name][k]["ksr_pct"], 2) for k in tests}, flush=True)

# ── Exp 3: latency (ms per prediction, CPU) ──
ctxs = [s.split()[:j] for s in tests["all"][:200] for j in range(1, min(len(s.split()), 6))]
def timeit(f, n=len(ctxs)):
    t = time.perf_counter()
    for c in ctxs: f(c)
    return 1000 * (time.perf_counter() - t) / max(n, 1)
res["latency_ms"] = {"inf_gram_next_word_top10": timeit(lambda c: e.predict_next(c, language=e.tag, top_k=10)),
                     "char12_ngram_per_char": None}
t = time.perf_counter(); cm.memo.clear(); nchar = 0
for s in tests["all"][:100]:
    for i in range(len(s)): cm.p(s[:i], s[i]); nchar += 1
res["latency_ms"]["char12_ngram_per_char"] = 1000 * (time.perf_counter() - t) / nchar
res["build_s"] = time.time() - t0
json.dump(res, open(f"results/main_{lang}.json", "w"), indent=1)
print(json.dumps(res, indent=1)[:3000])
