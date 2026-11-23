"""Step 17b (review): KSR of the EVALUATED build of the v3 paper (archived commit fe4e185), for the paper's Table "tab:ksr".
That client sent no typed letters (fetchPredictions(currentWords) only) and showed the first 7 predictions of the shipped
infinity-gram engine unchanged (archived backend/app.py /predict_next: no concept merge). So the shelf ignores typed letters.
Same simulator and test sets as exp_step16_final.py; also re-reports the 16-22 Nov build (OLD there) for comparison.
   python exp_step17_evaluated_build.py en hi mr gu"""
import sys, json
from lib import *
from exp_final import boot_ci
out = {}
for lang in sys.argv[1:]:
    train = sents(lang, "train"); tests = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}
    e = make_engine(train, lang); pool = Pool(train, 300); old = inf_shipped_scorer(e, pool); memo = {}; res = {}
    for split, data in tests.items():
        ka = kp = 0
        for s in data:
            ws = s.split()
            for i, w in enumerate(ws):
                ka += len(w) + 1; ctx = tuple(ws[:i])
                if ctx not in memo:
                    c = pool.get(""); sc = old(list(ctx), c); memo[ctx] = [x for _, x in sorted(zip(sc, c), key=lambda x: -x[0])][:7]
                kp += 1 if w in memo[ctx] else len(w) + 1        # typed letters never change the shelf
        res[split] = round(100.0 * (ka - kp) / ka, 3)
    res["avg"] = round((res["aac"] + res["care"]) / 2, 3); out[lang] = res; print(lang, res, flush=True)
json.dump(out, open("results/step17_evaluated_build_ksr.json", "w"), indent=1)
