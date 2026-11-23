"""Step 12 (DEV only, no test data touched): cheap levers on the shipped stack (backend predictor_v2 + lm_rerank).
Grid (run 2): shortlist K in {0,20,50} with 7 suggestions (what the UI shows); run 1 grid was K in {20,50,100}; suggestions shown n_pred in {5 (baseline protocol), 7 (what the UI shows)}; recency cache lam in {0, 0.15}.
   python exp_step12_dev.py en hi mr gu"""
import sys, json, time
from lib import *
from exp_final import run_stream
import predictor_v2 as P
import lm_rerank as L
L.CACHE_MAX = 10**7        # keep every scored context during the experiment
out = {}
for lang in sys.argv[1:]:
    train = sents(lang, "train"); dev = sents(lang, "dev")
    m = P.LangModel(lang, train, cov=True)
    class PoolShim:
        get = staticmethod(m.candidates)
    def make(K):
        def sc(ctx, cands):
            s = m.score(ctx, cands); ranked = sorted(zip(s, cands), key=lambda x: -x[0])
            if K == 0: return s
            r = L.rerank(lang, ctx, ranked, k=K); assert r is not None, L.status()
            d = {w: v for v, w in r[:K]}; return [d.get(w, -1.0) for w in cands]
        return sc
    res = {}; t0 = time.time()
    for K in (0, 20, 50):          # run 1 (stopped, too slow on the shared GPU) also had K=100, n=5 and a recency cache
        for n in (7,):
            for lam in (0.0,):
                k_, _, hits = run_stream(dev, make(K), PoolShim, lam=lam, n_pred=n)
                key = f"K{K}_n{n}_lam{lam}"; res[key] = round(k_, 3); print(lang, key, round(k_, 2), round(time.time() - t0), "s", flush=True)
                out[lang] = res; json.dump(out, open("results/step12_dev_" + "_".join(sys.argv[1:]) + ".json", "w"), indent=1)
