"""Step 14: what the USER sees. app.py merges the concept grammar, the statistical predictor and personal words, then the UI shows 7.
Simulate KSR of that merged list (CPU predictor, no personal words) for different merge rules.   python exp_step14_merge.py <dev|test> lang..."""
import sys, json, time
from lib import *
import predictor_v2 as P
import concept_predict as CP
from aac_lexicon import BOARD, resolve_label
split = sys.argv[1] if len(sys.argv) > 1 else "dev"; out = {}

def norm(w, lang): return w.lower() if lang == "en" else w

def merged(rule, words, stat, ctx_preds, prefix, exclude):
    sel, used = [], set(); inside = set(words)
    def push(w):
        if prefix and not w.startswith(prefix): return
        if w in used or (exclude and w in inside): return
        used.add(w); sel.append(w)
    if rule == "current":                     # app.py before this step: concept first, ONLY odd-ranked statistical words
        if words:
            for i in range(max(len(ctx_preds), len(stat))):
                if i < len(ctx_preds): push(ctx_preds[i])
                if i < len(stat) and i % 2 == 1: push(stat[i])
        else:
            for w in ctx_preds + stat: push(w)
    elif rule == "stat_first":                # statistical words lead, concept words fill every 3rd slot
        c = list(ctx_preds); s = list(stat); i = 0
        while c or s:
            if s and (i % 3 != 2 or not c): push(s.pop(0))
            elif c: push(c.pop(0))
            i += 1
    else:                                      # statistical only
        for w in stat: push(w)
    return sel

if __name__ == "__main__":
    for lang in sys.argv[2:]:
        train = sents(lang, "train")
        data = sents(lang, "dev") if split == "dev" else sents(lang, "test", ("aac",)) + sents(lang, "test", ("care",))
        m = P.LangModel(lang, train, cov=True); res = {}
        for rule, excl in (("current", True), ("stat_first", True), ("stat_first", False), ("stat_only", False)):
            ka = kp = 0; t0 = time.time()
            for s in data:
                ws = s.split()
                for i, w in enumerate(ws):
                    ka += len(w) + 1; best = len(w) + 1
                    cps = [norm(BOARD[resolve_label(x["word"])][lang] if resolve_label(x["word"]) else x["word"], lang) for x in CP.predict(ws[:i], lang, top_k=10)]
                    for k in range(len(w)):
                        stat = [x for _, x in m.rank(ws[:i], w[:k])[:10]]
                        shown = merged(rule, ws[:i], stat, cps, w[:k], excl)[:7]
                        if w in shown: best = k + 1; break
                    kp += best
            key = f"{rule}_exclude{excl}"; res[key] = round(100.0 * (ka - kp) / ka, 3)
            print(lang, split, key, res[key], round(time.time() - t0), "s", flush=True)
            out[lang] = res; json.dump(out, open(f"results/step14_merge_{split}_" + "_".join(sys.argv[2:]) + ".json", "w"), indent=1)
