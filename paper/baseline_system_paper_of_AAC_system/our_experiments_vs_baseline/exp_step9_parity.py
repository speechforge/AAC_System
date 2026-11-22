"""Plan step 4 parity check: the SHIPPED-APP module backend/predictor_v2.py, trained on the train split only, must reproduce the
experiment numbers (results/step4_<lang>.json, systems 'E improved CPU stack' and 'E+COV').   python exp_step9_parity.py en hi mr gu"""
import sys, json, time
from lib import *
from exp_final import run_stream
import predictor_v2 as P     # lib.py put backend/ on sys.path
out = {}
for lang in sys.argv[1:]:
    train = sents(lang, "train"); tests = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}
    ref = json.load(open(f"results/step4_{lang}.json"))["systems"]
    res = {}
    for nm, cov, key in (("E (no COV)", False, "E improved CPU stack"), ("E+COV", True, "E+COV (+5 char-LM completions)")):
        t0 = time.time(); m = P.LangModel(lang, train, cov=cov)
        class PoolShim:                                   # run_stream only needs .get(prefix)
            get = staticmethod(m.candidates)
        ks = {k: run_stream(v, lambda ctx, cands: m.score(ctx, cands), PoolShim)[0] for k, v in tests.items()}
        avg = (ks["aac"] + ks["care"]) / 2
        res[nm] = dict(app_module_ksr=avg, experiment_ksr=ref[key]["avg_ksr"], abs_diff=abs(avg - ref[key]["avg_ksr"]), seconds=round(time.time() - t0))
        print(lang, nm, round(avg, 3), "experiment", round(ref[key]["avg_ksr"], 3), flush=True)
    out[lang] = res
    json.dump(out, open("results/step9_parity_" + "_".join(sys.argv[1:]) + ".json", "w"), indent=1)
