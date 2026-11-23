"""Step 15 (TEST, run once after the dev choices): KSR of what the USER SEES (7 suggestions on screen, merged list), full test sets.
  OLD  = the app before Step 9/11/12: shipped infinity-gram, old merge rule, UI did not send typed letters (list ignores them)
  CPU  = the app now without a GPU: predictor_v2, new merge rule, letters sent
  GPU  = the app now with the GPU re-ranker (lm_rerank, K per language chosen on dev)
Personal words are not simulated (no user history in the test data).   python exp_step15_final.py en=50 hi=20 mr=20 gu=20"""
import sys, json, time
from lib import *
from exp_final import boot_ci
import predictor_v2 as P, lm_rerank as L, concept_predict as CP
from aac_lexicon import BOARD, resolve_label
from exp_step14_merge import merged, norm
L.CACHE_MAX = 10**7
out = {}
for arg in sys.argv[1:]:
    lang, K = arg.split("="); K = int(K)
    train = sents(lang, "train"); tests = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}
    m = P.LangModel(lang, train, cov=True); e = make_engine(train, lang); pool = Pool(train, 300); old = inf_shipped_scorer(e, pool)
    def cps(ctx): return [norm(BOARD[resolve_label(x["word"])][lang] if resolve_label(x["word"]) else x["word"], lang) for x in CP.predict(ctx, lang, top_k=10)]
    def shown(system, ctx, pre):
        if system == "OLD":
            c = pool.get(""); sc = old(list(ctx), c); stat = [w for _, w in sorted(zip(sc, c), key=lambda x: -x[0])][:10]
            return merged("current", ctx, stat, cps(ctx), "", True)[:7]       # typed letters never reached the server
        r = m.rank(list(ctx), pre)
        if system == "GPU": r = L.rerank(lang, list(ctx), r, k=K) or r
        return merged("stat_first", ctx, [w for _, w in r[:10]], cps(ctx), pre, False)[:7] if not pre else [w for _, w in r[:7]]
    res = {"K": K}; per = {}
    for system in ("OLD", "CPU", "GPU"):
        t0 = time.time(); res[system] = {}; per[system] = {}
        for split, data in tests.items():
            rows = []; memo = {}
            for s in data:
                ws = s.split(); ka = kp = 0
                for i, w in enumerate(ws):
                    ka += len(w) + 1; best = len(w) + 1
                    for k in range(len(w)):
                        key = (tuple(ws[:i]), w[:k] if system != "OLD" else "")
                        if key not in memo: memo[key] = shown(system, ws[:i], key[1])
                        if w in memo[key]: best = k + 1; break
                    kp += best
                rows.append((ka, kp))
            per[system][split] = rows; ka = sum(a for a, _ in rows); kp = sum(b for _, b in rows)
            res[system][split] = round(100.0 * (ka - kp) / ka, 3)
        res[system]["avg"] = round((res[system]["aac"] + res[system]["care"]) / 2, 3); res[system]["seconds"] = round(time.time() - t0)
        print(lang, system, res[system], flush=True)
        out[lang] = res; json.dump(out, open("results/step15_final.json", "w"), indent=1)
    for a, b in (("OLD", "CPU"), ("OLD", "GPU"), ("CPU", "GPU")):
        res[f"gain_{b}_vs_{a}_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per[a][k], per[b][k])] for k in tests}
    out[lang] = res; json.dump(out, open("results/step15_final.json", "w"), indent=1); print(lang, {k: v for k, v in res.items() if k.startswith("gain")}, flush=True)
