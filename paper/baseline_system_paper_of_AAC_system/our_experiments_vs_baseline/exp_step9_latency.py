"""CPU latency + build time of backend/predictor_v2.py (cold = caches empty, the realistic first-call cost; warm = repeated call).
Compares with the shipped infinity_gram predict_next. Test contexts: real test sentences, every word position, empty prefix and 2-char prefix."""
import sys, json, time, statistics as st
from lib import *
import predictor_v2 as P
out = {}
for lang in ("en", "hi", "mr", "gu"):
    train = sents(lang, "train"); test = sents(lang, "test", ("aac",))[:60]
    t0 = time.time(); m = P.LangModel(lang, train); build = time.time() - t0
    e = make_engine(train, lang)
    cases = [(s.split()[:i], s.split()[i]) for s in test for i in range(len(s.split()))]
    cold, ship, cov = [], [], []
    for ctx, w in cases:
        m._pool_cache.clear(); m._cand_cache.clear(); m.cm.memo.clear()       # worst case: nothing cached
        t = time.perf_counter(); m.rank(ctx, ""); cold.append((time.perf_counter() - t) * 1000)
        m._pool_cache.clear(); m._cand_cache.clear()
        t = time.perf_counter(); m.rank(ctx, w[:2]); cov.append((time.perf_counter() - t) * 1000)
        t = time.perf_counter(); e.predict_next(ctx, language=e.tag, top_k=10); ship.append((time.perf_counter() - t) * 1000)
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]
    out[lang] = dict(build_s=round(build, 2), n=len(cases), v2_nextword_p50_ms=q(cold, .5), v2_nextword_p95_ms=q(cold, .95),
                     v2_prefix2_cov_p50_ms=q(cov, .5), v2_prefix2_cov_p95_ms=q(cov, .95), shipped_p50_ms=q(ship, .5), shipped_p95_ms=q(ship, .95))
    out[lang]["cpu_ms_for_table"] = out[lang]["v2_nextword_p50_ms"]
    print(lang, {k: round(v, 2) if isinstance(v, float) else v for k, v in out[lang].items()}, flush=True)
json.dump({l: v["cpu_ms_for_table"] for l, v in out.items()}, open("results/step9_latency.json", "w"))
json.dump(out, open("results/step9_latency_full.json", "w"), indent=1)
