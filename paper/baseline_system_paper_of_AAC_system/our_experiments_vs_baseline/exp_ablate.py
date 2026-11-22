"""Ablation of the shipped infinity-gram predictor: (a) already-selected-word exclusion, (b) backoff alpha."""
import sys, json
from lib import *
res = {}
for lang in sys.argv[1:]:
    train = sents(lang, "train"); tests = {"aac": sents(lang, "test", ("aac",)), "care": sents(lang, "test", ("care",))}
    e = make_engine(train, lang); pool = Pool(train, 300)
    uni = e.unigrams_hi if e.tag == "hi" else e.unigrams_en; T = sum(uni.values())
    def noexcl(alpha):
        def sc(ctx, cands):
            d = inf_dist(e, ctx, alpha)
            return [d.get(w, 0.0) + 1e-6 * uni.get(w, 0) / T for w in cands]
        return sc
    variants = {"shipped (exclude selected words, alpha=0.4)": inf_shipped_scorer(e, pool)}
    for a in (0.1, 0.2, 0.4, 0.7): variants[f"no exclusion, alpha={a}"] = noexcl(a)
    res[lang] = {}
    for nm, sc in variants.items():
        pr = predictor_from_scorer(sc, pool); res[lang][nm] = {}
        for k, v in tests.items():
            s, ka, kp, hits, nw = ksr(v, pr); res[lang][nm][k] = dict(ksr_pct=s, hit=hits)
        print(lang, nm, {k: round(x["ksr_pct"], 2) for k, x in res[lang][nm].items()}, flush=True)
    json.dump(res, open("results/ablate_" + "_".join(sys.argv[1:]) + ".json", "w"), indent=1)
