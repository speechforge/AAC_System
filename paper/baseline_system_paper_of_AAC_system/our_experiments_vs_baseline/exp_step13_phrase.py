"""Step 13 (DEV first): phrase suggestions. Besides the n word suggestions, up to P extra slots offer the top word(s) extended by
the infinity-gram's most likely continuation (only while its conditional probability >= min_p, up to max_extra words).
Choosing a phrase costs one selection and enters all its words. KSR as before (chars+spaces saved).
   python exp_step13_phrase.py <split dev|test> <K: 0=CPU only, 20/50=LM shortlist> lang..."""
import sys, json, time
from lib import *
import predictor_v2 as P
import lm_rerank as L
split, K = sys.argv[1], int(sys.argv[2]); out = {}

def extend(m, ctx, w, min_p, max_extra):
    ph = [w]
    for _ in range(max_extra):
        cap = m.params["ctx_cap"]; d = m._inf_dist((ctx + ph)[-cap:])
        if not d: break
        nw, p = max(d.items(), key=lambda x: x[1])
        if p < min_p: break
        ph.append(nw)
    return ph

def run(sentences, m, lang, n=5, P_=2, min_p=0.5, max_extra=2):
    ka = kp = 0; memo = {}
    def rank(ctx, pre):
        key = (tuple(ctx), pre)
        if key not in memo:
            cands = m.candidates(pre)
            if not cands: memo[key] = []; return []
            sc = m.score(list(ctx), cands); r = sorted(zip(sc, cands), key=lambda x: -x[0])
            if K: r = L.rerank(lang, list(ctx), r, k=K) or r
            memo[key] = [w for _, w in r]
        return memo[key]
    for s in sentences:
        ws = s.split(); i = 0
        while i < len(ws):
            w = ws[i]; cost = len(w) + 1; adv = 1
            for k in range(len(w)):
                preds = rank(ws[:i], w[:k])[:n]
                phr = [extend(m, ws[:i], x, min_p, max_extra) for x in preds[:P_]] if P_ else []
                phr = [p for p in phr if len(p) > 1]
                best = max((p for p in phr if ws[i:i + len(p)] == p), key=len, default=None)
                if best: cost = k + 1; adv = len(best); break
                if w in preds: cost = k + 1; break
            ka += sum(len(x) + 1 for x in ws[i:i + adv]); kp += cost; i += adv
    return 100.0 * (ka - kp) / ka

for lang in sys.argv[3:]:
    train = sents(lang, "train")
    data = sents(lang, "dev") if split == "dev" else sents(lang, "test", ("aac",)) + sents(lang, "test", ("care",))
    m = P.LangModel(lang, train, cov=True); res = {}; t0 = time.time()
    grid = [(5, 0, 0.5), (7, 0, 0.5)] + [(5, 2, mp) for mp in (0.3, 0.5, 0.7)] + [(7, 2, 0.5)]
    if split == "test": grid = [tuple(x) for x in json.loads(sys.argv[0] and __import__("os").environ.get("GRID", "[[5,0,0.5],[5,2,0.5],[7,0,0.5],[7,2,0.5]]"))]
    for n, P_, mp in grid:
        key = f"n{n}_phr{P_}_minp{mp}"; res[key] = round(run(data, m, lang, n, P_, mp), 3)
        print(lang, split, f"K{K}", key, res[key], round(time.time() - t0), "s", flush=True)
        out[lang] = res; json.dump(out, open(f"results/step13_phrase_{split}_K{K}_" + "_".join(sys.argv[3:]) + ".json", "w"), indent=1)
