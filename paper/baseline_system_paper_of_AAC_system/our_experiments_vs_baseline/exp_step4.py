"""Step 4 (CPU, all 4 languages), every variant is built on E = improved CPU stack (no personalisation) and judged on FULL test sets:
  ES   expected-savings re-ranking: score = p(w) * (len(w)-len(prefix)+1)**gamma  (gamma tuned on dev, 0 = off)
  COV  vocabulary-coverage fallback: add the M most probable char-12-gram completions (beam search) of the typed prefix that are NOT in the pool
  LC   learning curve: A and E retrained on 25/50/75/100% of train
   python exp_step4.py <lang>"""
import sys, json, math, random, time
from lib import *
from exp_improve_lib import softnorm
from exp_final import capped_scorer, mix, run_stream, boot_ci
lang = sys.argv[1]
train = sents(lang, "train"); dev = sents(lang, "dev"); tests = {k: sents(lang, "test", (k,)) for k in ("aac", "care")}
tuned = json.load(open(f"results/final_{lang}.json"))[lang]["tuned"]; C, a_ = tuned["step1+5 ctx_cap,alpha"]; wch = tuned["step2 mix_weight_infgram"]

def build(train_sents):
    e = make_engine(train_sents, lang); cm = CharNgram(12).train(train_sents); pool = Pool(train_sents, 300)
    chs = lambda ctx, cands, f=charlm_scorer(cm): softnorm(f(ctx, cands))
    return e, cm, pool, mix(capped_scorer(e, C, a_), chs, wch)

class ExtPool:
    """pool + M char-LM completions of the prefix that the pool does not contain (words outside the training vocabulary)."""
    def __init__(self, pool, cm, M=5, minlen=2, width=8, extra=10):
        self.pool, self.cm, self.M, self.minlen, self.width, self.extra = pool, cm, M, minlen, width, extra; self.freq = pool.freq; self.cache = {}
    def get(self, prefix):
        r = self.cache.get(prefix)
        if r is None:
            r = list(self.pool.get(prefix))
            if len(prefix) >= self.minlen and self.M > 0:
                beams = [(0.0, prefix)]; done = []
                for _ in range(self.extra):
                    nb = []
                    for lp, w in beams:
                        for c in self.cm.alpha:
                            q = lp + math.log(self.cm.p(" " + w, c))
                            (done if c == " " else nb).append((q, w if c == " " else w + c))
                    beams = sorted(nb, reverse=True)[: self.width]
                    if not beams: break
                seen = set(r)
                for _, w in sorted(done, reverse=True):
                    if w not in seen and w != prefix: r.append(w); seen.add(w)
                    if len(r) >= len(self.pool.get(prefix)) + self.M: break
            self.cache[prefix] = r
        return r

def es(base, gamma):
    if gamma == 0: return base
    def sc(ctx, cands, prefix):
        p = base(ctx, cands); return [x * (max(len(w) - len(prefix), 0) + 1) ** gamma for x, w in zip(p, cands)]
    sc.wants_prefix = True; return sc

def evaluate(sc, pool):
    r = {}; per = {}
    for k, v in tests.items():
        s, p, h = run_stream(v, sc, pool); r[k] = dict(ksr_pct=s, top1=h[1], top3=h[3], top5=h[5], top10=h[10]); per[k] = p
    r["avg_ksr"] = (r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2; return r, per

t0 = time.time(); res = {"lang": lang}; e, cm, pool, cpu = build(train)
bg = (-1, 0)
for g in (0, 0.5, 1.0, 1.5, 2.0):
    s = run_stream(dev, es(cpu, g), pool)[0]; print("dev gamma", g, round(s, 2), flush=True)
    if s > bg[0] + 1e-9: bg = (s, g)
gamma = bg[1]; res["gamma"] = gamma; res["dev_ksr_by_gamma"] = None
xp = ExtPool(pool, cm, M=5)
bm = (run_stream(dev, es(cpu, gamma), pool)[0], 0)
s = run_stream(dev, es(cpu, gamma), xp)[0]; print("dev COV M=5", round(s, 2), flush=True); res["dev_cov_ksr"] = s; res["dev_nocov_ksr"] = bm[0]
use_cov = s > bm[0]; res["coverage_used"] = use_cov
variants = [("A shipped infinity-gram", inf_shipped_scorer(e, pool), pool), ("E improved CPU stack", cpu, pool), (f"E+ES gamma={gamma}", es(cpu, gamma), pool),
            ("E+COV (+5 char-LM completions)", cpu, xp), (f"E+ES+COV", es(cpu, gamma), xp)]
res["systems"] = {}; per = {}
for nm, sc, pl in variants:
    r, p = evaluate(sc, pl); res["systems"][nm] = r; per[nm] = p; print(lang, nm, round(r["avg_ksr"], 2), round((r["aac"]["top5"] + r["care"]["top5"]) / 2, 1), round(time.time() - t0), "s", flush=True)
for nm in list(res["systems"])[1:]:
    res["systems"][nm]["gain_vs_shipped_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per["A shipped infinity-gram"][k], per[nm][k])] for k in tests}
    if nm != "E improved CPU stack": res["systems"][nm]["gain_vs_E_95ci_pp"] = {k: [round(x, 2) for x in boot_ci(per["E improved CPU stack"][k], per[nm][k])] for k in tests}
lc = {}
for frac in (0.25, 0.5, 0.75, 1.0):
    sub = train[: int(len(train) * frac)]; e2, cm2, pool2, cpu2 = build(sub)
    lc[frac] = {"A": evaluate(inf_shipped_scorer(e2, pool2), pool2)[0]["avg_ksr"], "E": evaluate(cpu2, pool2)[0]["avg_ksr"]}; print("LC", frac, lc[frac], flush=True)
res["learning_curve_ksr"] = lc; res["seconds"] = time.time() - t0
json.dump(res, open(f"results/step4_{lang}.json", "w"), indent=1)
