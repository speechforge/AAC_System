"""Step 9: 5-fold block cross-validation of A (shipped), E (improved CPU stack), E+COV. Pools train+dev+test sentences (original order) and uses 5 contiguous blocks
as test folds (dialogue turns are contiguous, so leakage is limited to block borders; conversation ids are not stored in the data files).
Hyper-parameters are the ones tuned once on the original dev split (final_<lang>.json) - NOT re-tuned per fold.   python exp_cv.py <lang>"""
import sys, json, statistics as st, time
from lib import *
from exp_improve_lib import softnorm
from exp_final import capped_scorer, mix, run_stream
src = open("exp_step4.py").read(); exec(src[src.index("class ExtPool"):src.index("def es(base")])
lang = sys.argv[1]
allS = [s for sp in ("train", "dev", "test") for s in sents(lang, sp)]; n = len(allS); tuned = json.load(open(f"results/final_{lang}.json"))[lang]["tuned"]
C, a_ = tuned["step1+5 ctx_cap,alpha"]; wch = tuned["step2 mix_weight_infgram"]; out = {"lang": lang, "n_sentences": n, "folds": []}; t0 = time.time()
for f in range(5):
    lo, hi = f * n // 5, (f + 1) * n // 5; test = allS[lo:hi]; train = allS[:lo] + allS[hi:]
    e = make_engine(train, lang); cm = CharNgram(12).train(train); pool = Pool(train, 300); xp = ExtPool(pool, cm, M=5)
    chs = lambda ctx, cands, g=charlm_scorer(cm): softnorm(g(ctx, cands)); cpu = mix(capped_scorer(e, C, a_), chs, wch)
    r = {"A": run_stream(test, inf_shipped_scorer(e, pool), pool)[0], "E": run_stream(test, cpu, pool)[0], "E+COV": run_stream(test, cpu, xp)[0]}
    out["folds"].append(r); print(lang, f, {k: round(v, 2) for k, v in r.items()}, round(time.time() - t0), "s", flush=True)
for k in ("A", "E", "E+COV"):
    v = [r[k] for r in out["folds"]]; out[k] = {"mean": st.mean(v), "sd": st.stdev(v)}
for k in ("E", "E+COV"):
    d = [r[k] - r["A"] for r in out["folds"]]; out[k + "_minus_A"] = {"mean": st.mean(d), "sd": st.stdev(d), "folds_positive": sum(x > 0 for x in d)}
json.dump(out, open(f"results/cv_{lang}.json", "w"), indent=1)
