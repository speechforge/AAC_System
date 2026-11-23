"""Step 16 FINAL (TEST, run once after the dev choices of Steps 12-16): KSR of what the USER SEES, full test sets.
  OLD    = the app before Steps 9/11/12: shipped infinity-gram, old merge rule, typed letters never reached the server
  CPU    = the app now without a GPU (predictor_v2, new merge rule, letters sent), new user (no history)
  CPU+P  = CPU for a signed-in user: personal model of their earlier sentences (lam 0.1), their frequent words as sentence
           starters (app rule), and the phrase row (one multi-word suggestion above the 7 words)
  GPU    = CPU + adapted-BLOOM re-ranker (lm_rerank, shortlist K chosen on dev), new user
  GPU+P  = GPU for a signed-in user (as CPU+P)
Simulated user for +P: types the test sentences in order (AAC then caregiver); each sentence joins their history only AFTER
it is typed. Choosing the phrase costs 1 keystroke and enters all its words.   python exp_step16_final.py en=50 hi=50 ..."""
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
    cmemo, bmemo = {}, {"CPU": {}, "GPU": {}}
    def cps(ctx):
        if ctx not in cmemo:
            cmemo[ctx] = [norm(BOARD[resolve_label(x["word"])][lang] if resolve_label(x["word"]) else x["word"], lang)
                          for x in CP.predict(list(ctx), lang, top_k=10)]
        return cmemo[ctx]
    def ranked(engine, ctx, pre):
        d = bmemo[engine]; r = d.get((ctx, pre))
        if r is None:
            r = m.rank(list(ctx), pre)
            if engine == "GPU": r = L.rerank(lang, list(ctx), r, k=K) or r
            r = d[(ctx, pre)] = r[:100]
        return r
    def shown(system, ctx, pre, pm):
        """(the 7 words on screen, the phrase or None) - same rules as app.py /predict_next."""
        if system == "OLD":
            c = pool.get(""); sc = old(list(ctx), c); stat = [w for _, w in sorted(zip(sc, c), key=lambda x: -x[0])][:10]
            return merged("current", ctx, stat, cps(ctx), "", True)[:7], None
        r = ranked(system[:3], ctx, pre)
        if not system.endswith("+P"):
            return (merged("stat_first", ctx, [w for _, w in r[:10]], cps(ctx), pre, False)[:7] if not pre else [w for _, w in r[:7]]), None
        r = P.personalise(r, pm, list(ctx), pre, P.LAM[lang]); stat = [w for _, w in r[:10]]
        freq = [w for w, _ in pm.uni.most_common(7)]
        sel, used = [], set()
        def push(w):
            if (not pre or w.startswith(pre)) and w not in used: used.add(w); sel.append(w)
        if not ctx:
            for w in freq[:2]: push(w)
        if pre:
            for w in stat: push(w)
        else:
            for w in merged("stat_first", ctx, stat, cps(ctx), "", False): push(w)
        for w in freq: push(w)
        return sel[:7], m.phrase(list(ctx), pre, top=r[0][1] if r else None, pm=pm, **P.PHRASE)
    res = {"K": K}; per = {}
    for system in ("OLD", "CPU", "CPU+P", "GPU", "GPU+P"):
        t0 = time.time(); res[system] = {}; per[system] = {}; pm = P.Personal(lang); memo = {}; nph = 0
        for split, data in tests.items():
            rows = []
            for s in data:
                ws = s.split(); ka = kp = 0; i = 0
                while i < len(ws):
                    w = ws[i]; cost = len(w) + 1; adv = 1
                    for k in range(len(w)):
                        ctx, pre = tuple(ws[:i]), (w[:k] if system != "OLD" else "")
                        if system.endswith("+P"): words, phr = shown(system, ctx, pre, pm)
                        else:
                            if (ctx, pre) not in memo: memo[(ctx, pre)] = shown(system, ctx, pre, pm)
                            words, phr = memo[(ctx, pre)]
                        if phr and ws[i:i + len(phr)] == phr: cost = k + 1; adv = len(phr); nph += 1; break
                        if w in words: cost = k + 1; break
                    ka += sum(len(x) + 1 for x in ws[i:i + adv]); kp += cost; i += adv
                rows.append((ka, kp)); pm.add(ws)
            per[system][split] = rows; ka = sum(a for a, _ in rows); kp = sum(b for _, b in rows)
            res[system][split] = round(100.0 * (ka - kp) / ka, 3)
        res[system]["avg"] = round((res[system]["aac"] + res[system]["care"]) / 2, 3)
        res[system]["phrases_used"] = nph; res[system]["seconds"] = round(time.time() - t0)
        print(lang, system, res[system], flush=True)
        out[lang] = res; json.dump(out, open("results/step16_final.json", "w"), indent=1)
    for a, b in (("OLD", "GPU+P"), ("OLD", "CPU"), ("CPU", "CPU+P"), ("CPU", "GPU"), ("GPU", "GPU+P")):
        res[f"gain_{b}_vs_{a}_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per[a][k], per[b][k])] for k in tests}
    out[lang] = res; json.dump(out, open("results/step16_final.json", "w"), indent=1)
    print(lang, {k: v for k, v in res.items() if k.startswith("gain")}, flush=True)
