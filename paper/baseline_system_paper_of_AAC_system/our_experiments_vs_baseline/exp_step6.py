"""Step 6: learned re-ranker (logistic regression, pointwise LTR) over CPU features on top of E+COV. Trained on DEV queries only (engine has not seen dev), applied once to FULL test.
Features per candidate: log p(CPU stack), log p(infinity-gram), log p(char-12), log unigram freq, remaining chars, prefix length, OOV flag, CPU rank, word already in sentence.
   python exp_step6.py <lang>   (needs scikit-learn -> taac_env)"""
import sys, json, math, time, numpy as np
from lib import *
from exp_improve_lib import softnorm
from exp_final import capped_scorer, mix, run_stream, boot_ci
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
src = open("exp_step4.py").read(); exec(src[src.index("class ExtPool"):src.index("def es(base")])
lang = sys.argv[1]; K = 30
train = sents(lang, "train"); dev = sents(lang, "dev"); tests = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}
tuned = json.load(open(f"results/final_{lang}.json"))[lang]["tuned"]; C, a_ = tuned["step1+5 ctx_cap,alpha"]; wch = tuned["step2 mix_weight_infgram"]
e = make_engine(train, lang); cm = CharNgram(12).train(train); pool = Pool(train, 300); xp = ExtPool(pool, cm, M=5)
inf_s = capped_scorer(e, C, a_); chf = charlm_scorer(cm); chs = lambda ctx, cands: softnorm(chf(ctx, cands)); cpu = mix(inf_s, chs, wch); freq = pool.freq
def feats(ctx, cands, prefix):
    c = cpu(ctx, cands); i_ = inf_s(ctx, cands); h = chs(ctx, cands); order = sorted(range(len(cands)), key=lambda i: -c[i])[:K]; seen = set(ctx)
    X = np.array([[math.log(c[i] + 1e-12), math.log(i_[i] + 1e-12), math.log(h[i] + 1e-12), math.log(1 + freq.get(cands[i], 0)), len(cands[i]) - len(prefix), len(prefix),
                   float(cands[i] not in freq), math.log1p(r), float(cands[i] in seen)] for r, i in enumerate(order)])
    return order, X
# training data from DEV: every word, prefix lengths 0..min(len,4)-1
Xs, ys = [], []
for s in dev:
    ws = s.split()
    for i, w in enumerate(ws):
        for k in range(min(len(w), 4)):
            cands = xp.get(w[:k])
            if not cands: continue
            order, X = feats(ws[:i], cands, w[:k]); Xs.append(X); ys += [1 if cands[j] == w else 0 for j in order]
X = np.vstack(Xs); y = np.array(ys); sc_ = StandardScaler().fit(X); print("train rows", X.shape, "pos", y.sum(), flush=True)
best = None
for Cc in (0.01, 0.1, 1.0):                 # pick C by 2-fold held-out log-loss on dev rows (by contiguous halves)
    h = len(X) // 2; ll = 0
    for a, b in ((slice(0, h), slice(h, None)), (slice(h, None), slice(0, h))):
        lr = LogisticRegression(C=Cc, max_iter=500).fit(sc_.transform(X[a]), y[a]); p = lr.predict_proba(sc_.transform(X[b]))[:, 1]
        ll += -np.mean(y[b] * np.log(p + 1e-9) + (1 - y[b]) * np.log(1 - p + 1e-9))
    print("C", Cc, "held-out logloss", round(ll / 2, 4), flush=True)
    if best is None or ll < best[0]: best = (ll, Cc)
lr = LogisticRegression(C=best[1], max_iter=500).fit(sc_.transform(X), y); coef = dict(zip(["log_cpu", "log_inf", "log_char", "log_freq", "remaining", "prefix_len", "oov", "log_rank", "in_sentence"], lr.coef_[0].round(3).tolist()))
def ltr(ctx, cands, prefix):
    order, Xq = feats(ctx, cands, prefix); p = lr.predict_proba(sc_.transform(Xq))[:, 1]; out = [-1.0] * len(cands)
    for r, i in enumerate(order): out[i] = float(p[r])
    return out
ltr.wants_prefix = True
res = {"lang": lang, "C": best[1], "coef": coef, "train_rows": int(len(y)), "systems": {}}; per = {}; t0 = time.time()
for nm, sc, pl in (("A shipped infinity-gram", inf_shipped_scorer(e, pool), pool), ("E+COV (CPU)", cpu, xp), ("L = E+COV + learned re-ranker (top-30)", ltr, xp)):
    r = {}; per[nm] = {}
    for k, v in tests.items():
        s_, p, h_ = run_stream(v, sc, pl); r[k] = dict(ksr_pct=s_, top1=h_[1], top3=h_[3], top5=h_[5], top10=h_[10]); per[nm][k] = p
    r["avg_ksr"] = (r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2; res["systems"][nm] = r; print(lang, nm, round(r["avg_ksr"], 2), round((r["aac"]["top5"] + r["care"]["top5"]) / 2, 1), round(time.time() - t0), "s", flush=True)
n = list(res["systems"])
res["systems"][n[2]]["gain_vs_E+COV_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per[n[1]][k], per[n[2]][k])] for k in tests}
res["systems"][n[2]]["gain_vs_shipped_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per[n[0]][k], per[n[2]][k])] for k in tests}
json.dump(res, open(f"results/step6_{lang}.json", "w"), indent=1)
