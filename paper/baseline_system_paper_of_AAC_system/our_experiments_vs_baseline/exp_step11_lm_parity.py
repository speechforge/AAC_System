"""Plan step 3 in the app: the SHIPPED module backend/lm_rerank.py (adapters copied to backend/lm_adapters/) on top of backend/predictor_v2.py,
trained on the train split only, must reproduce the experiment numbers (results/step8_<lang>_K20.json / step7 K=50).   python exp_step11_lm_parity.py mr gu hi en"""
import sys, json, time, glob
from lib import *
from exp_final import run_stream
import predictor_v2 as P
import lm_rerank as L
K = int(__import__("os").environ.get("AAC_LM_K", "20")); out = {}
for lang in sys.argv[1:]:
    train = sents(lang, "train"); tests = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}
    m = P.LangModel(lang, train, cov=True); ms = []
    class PoolShim:
        get = staticmethod(m.candidates)
    def scorer(ctx, cands):
        sc = m.score(ctx, cands); ranked = sorted(zip(sc, cands), key=lambda x: -x[0])
        t = time.perf_counter(); r = L.rerank(lang, ctx, ranked, k=K); ms.append(1000 * (time.perf_counter() - t))
        assert r is not None, L.status()
        d = {w: s for s, w in r[:K]}; return [d.get(w, -1.0) for w in cands]
    t0 = time.time(); ks = {k: run_stream(v, scorer, PoolShim)[0] for k, v in tests.items()}; avg = (ks["aac"] + ks["care"]) / 2
    ref = None
    for f in (f"results/step8_{lang}_K{K}.json",):
        try:
            j = json.load(open(f)); ref = next(v["avg_ksr"] for kk, v in j["systems"].items() if kk.startswith("I")) if "systems" in j else None
        except Exception as e: ref = None
    ms.sort(); out[lang] = dict(app_module_ksr=avg, experiment_ksr=ref, K=K, lm_ms_p50=ms[len(ms)//2], lm_ms_p95=ms[int(.95*len(ms))], calls=len(ms), seconds=round(time.time()-t0))
    print(lang, out[lang], flush=True); json.dump(out, open("results/step11_lm_parity_" + "_".join(sys.argv[1:]) + ".json", "w"), indent=1)
