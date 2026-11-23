"""Step 16 (DEV): personal vocabulary + a sentence/phrase suggestion, using the SAME code the app runs (predictor_v2).
Simulated user: types the dev sentences in order (AAC then caregiver). After each sentence it is added to that user's
Personal model (as the app does with saved conversations). Nothing from the dev set is seen before it is typed.
  words  : n word suggestions (7 = what the app shows)
  lam    : weight of the personal model (0 = off)
  phrase : one extra multi-word suggestion (a separate row in the UI); choosing it costs 1 and enters all its words.
  n8     : control - one more WORD slot instead of the phrase row, so the gain of the row is not just "one more slot".
   python exp_step16_dev.py <K: 0 = CPU, 50 = GPU re-ranker> lang..."""
import sys, json, time
from lib import *
import predictor_v2 as P
K = int(sys.argv[1]) if __name__ == "__main__" else 0
if K:
    import lm_rerank as L
    L.CACHE_MAX = 10**7
TOPN = 100


def run(data, m, lang, n=7, lam=0.0, ph=None, base=None):
    pm = P.Personal(lang); ka = kp = 0; rows = []; nph = 0
    for s in data:
        ws = s.split(); i = 0; a0, p0 = ka, kp
        while i < len(ws):
            w = ws[i]; cost = len(w) + 1; adv = 1
            for k in range(len(w)):
                ctx, pre = tuple(ws[:i]), w[:k]
                r = base.get((ctx, pre))
                if r is None:
                    r = m.rank(list(ctx), pre)
                    if K: r = L.rerank(lang, list(ctx), r, k=K) or r
                    r = base[(ctx, pre)] = r[:TOPN]
                if lam: r = P.personalise(r, pm, list(ctx), pre, lam)
                preds = [x for _, x in r[:n]]
                phr = m.phrase(list(ctx), pre, top=preds[0] if preds else None, pm=pm, **ph) if ph else None
                if phr and ws[i:i + len(phr)] == phr: cost = k + 1; adv = len(phr); nph += 1; break
                if w in preds: cost = k + 1; break
            ka += sum(len(x) + 1 for x in ws[i:i + adv]); kp += cost; i += adv
        rows.append((ka - a0, kp - p0)); pm.add(ws)
    return 100.0 * (ka - kp) / ka, rows, nph


if __name__ == "__main__":
    out = {}
    for lang in sys.argv[2:]:
        train = sents(lang, "train"); dev = sents(lang, "dev"); m = P.LangModel(lang, train, cov=True); base = {}
        grid = [("n7", 7, 0, None), ("n8 (control: one more word)", 8, 0, None)]
        grid += [(f"n7 personal lam{l}", 7, l, None) for l in (0.1, 0.2, 0.3, 0.5)]
        grid += [("n7 + phrase: own sentences only", 7, 0, dict(use_train=False, min_p=1.0)),
                 ("n7 + phrase: own + training sentences", 7, 0, dict(use_train=True, min_p=1.0)),
                 ("n7 + phrase: own + training + confident extension p0.5", 7, 0, dict(use_train=True, min_p=0.5)),
                 ("n7 + phrase: own + training + confident extension p0.3", 7, 0, dict(use_train=True, min_p=0.3))]
        res = {}; t0 = time.time()
        for name, n, lam, ph in grid:
            ksr, _, nph = run(dev, m, lang, n, lam, ph, base); res[name] = round(ksr, 3)
            print(lang, f"K{K}", name, res[name], "phrases used", nph, round(time.time() - t0), "s", flush=True)
            out[lang] = res; json.dump(out, open(f"results/step16_dev_K{K}_" + "_".join(sys.argv[2:]) + ".json", "w"), indent=1)
        best_l = max((0.1, 0.2, 0.3, 0.5), key=lambda l: res[f"n7 personal lam{l}"])
        phs = [k for k in res if k.startswith("n7 + phrase")]; best_p = max(phs, key=res.get)
        ph = [g[3] for g in grid if g[0] == best_p][0]
        name = f"n7 personal lam{best_l} + {best_p[5:]}"
        ksr, _, nph = run(dev, m, lang, 7, best_l, ph, base); res[name] = round(ksr, 3)
        print(lang, f"K{K}", name, res[name], "phrases used", nph, round(time.time() - t0), "s", flush=True)
        out[lang] = res; json.dump(out, open(f"results/step16_dev_K{K}_" + "_".join(sys.argv[2:]) + ".json", "w"), indent=1)
