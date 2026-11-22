"""Executes plan steps 1,5,7,9 together on CPU (all 4 languages): builds a stack of improvements over the shipped
infinity-gram predictor, tunes every knob on DEV only, evaluates on the full TEST sets, and gives paired bootstrap CIs
of the gain over the shipped system.   python exp_final.py en hi mr gu"""
import sys, json, math, random, collections
from lib import *
from exp_improve_lib import softnorm

def capped_scorer(e, C, alpha):
    uni = e.unigrams_hi if e.tag == "hi" else e.unigrams_en; T = sum(uni.values())
    def sc(ctx, cands):
        c = ctx[-C:] if C else ctx
        d = inf_dist(e, c, alpha)
        if C and len(ctx) > C: pass
        raw = [d.get(w, 0.0) + 1e-6 * uni.get(w, 0) / T + 1e-12 for w in cands]; z = sum(raw); return [x / z for x in raw]
    return sc
def mix(sa, sb, w):
    return lambda ctx, cands: [w * x + (1 - w) * y for x, y in zip(sa(ctx, cands), sb(ctx, cands))]

def run_stream(sentences, base_score, pool, lam=0.0, learn=True, n_pred=5, cache_boost=2.0):
    """Sequential KSR. If lam>0 the system is personalised: words/bigrams of the user's previous sentences form a recency
    cache that is interpolated with the base scores. Returns per-sentence (ka, kp) plus empty-prefix hit rates."""
    uc = collections.Counter(); bc = collections.Counter(); per = []; hits = collections.Counter(); nw = 0
    memo = {}
    def base(ctx, prefix):
        k = (tuple(ctx[-3:]) if True else tuple(ctx), prefix, len(ctx) > 0)
        return None
    for s in sentences:
        ws = s.split(); ka = kp = 0; bmemo = {}
        def rank(ctx, prefix):
            cands = pool.get(prefix)
            if not cands: return []
            key = (tuple(ctx), prefix)
            if key not in bmemo:
                sc = base_score(list(ctx), cands, prefix) if getattr(base_score, 'wants_prefix', False) else base_score(list(ctx), cands)
                if lam > 0 and uc:
                    prev = ctx[-1] if ctx else "<s>"
                    cs = [uc[w] + cache_boost * bc[(prev, w)] for w in cands]; z = sum(cs)
                    if z > 0: sc = [(1 - lam) * a + lam * c / z for a, c in zip(sc, cs)]
                bmemo[key] = [w for _, w in sorted(zip(sc, cands), key=lambda x: -x[0])]
            return bmemo[key]
        for i, w in enumerate(ws):
            ka += len(w) + 1; best = len(w) + 1
            for k in range(len(w)):
                preds = rank(ws[:i], w[:k])[:n_pred]
                if k == 0:
                    t10 = rank(ws[:i], "")[:10]; nw += 1
                    for K in (1, 3, 5, 10):
                        if w in t10[:K]: hits[K] += 1
                if w in preds: best = k + 1; break
            kp += best
        per.append((ka, kp))
        if learn and lam > 0:
            prev = "<s>"
            for w in ws: uc[w] += 1; bc[(prev, w)] += 1; prev = w
    ka = sum(a for a, _ in per); kp = sum(b for _, b in per)
    return 100.0 * (ka - kp) / ka, per, {K: 100.0 * hits[K] / max(nw, 1) for K in (1, 3, 5, 10)}

def boot_ci(per_a, per_b, n=1000, seed=0):
    """paired bootstrap over sentences of KSR(b)-KSR(a) (percentage points)."""
    r = random.Random(seed); N = len(per_a); ds = []
    for _ in range(n):
        idx = [r.randrange(N) for _ in range(N)]
        ka = sum(per_a[i][0] for i in idx); ksa = sum(per_a[i][1] for i in idx); ksb = sum(per_b[i][1] for i in idx)
        ds.append(100.0 * (ksa - ksb) / ka)
    ds.sort(); return ds[int(.025 * n)], ds[int(.975 * n)]

if __name__ == "__main__":
    out = {}
    for lang in sys.argv[1:]:
        train = sents(lang, "train"); dev = sents(lang, "dev"); tests = {"aac": sents(lang, "test", ("aac",)), "care": sents(lang, "test", ("care",))}
        e = make_engine(train, lang); cm = CharNgram(12).train(train); pool = Pool(train, 300)
        chs = lambda ctx, cands, f=charlm_scorer(cm): softnorm(f(ctx, cands))
        D = dev[:300]; shipped = inf_shipped_scorer(e, pool)
        log = {}
        # --- tune on dev only
        best = (-1, None)
        for C in (2, 3, 4, None):
            for a in (0.2, 0.4, 0.6):
                s = run_stream(D, capped_scorer(e, C, a), pool)[0]
                if s > best[0]: best = (s, (C, a))
        C, a = best[1]; log["step1+5 ctx_cap,alpha"] = [C, a]; capd = capped_scorer(e, C, a)
        bw = (-1, None)
        for w in (0.3, 0.5, 0.7, 0.85):
            s = run_stream(D, mix(capd, chs, w), pool)[0]
            if s > bw[0]: bw = (s, w)
        w = bw[1]; log["step2 mix_weight_infgram"] = w; hyb = mix(capd, chs, w)
        bl = (-1, 0.0)
        for lam in (0.1, 0.2, 0.3, 0.45):
            s = run_stream(D, hyb, pool, lam=lam)[0]
            if s > bl[0]: bl = (s, lam)
        lam = bl[1] if bl[0] > run_stream(D, hyb, pool)[0] else 0.0; log["step7 personalisation lambda"] = lam
        systems = [("A shipped infinity-gram", shipped, 0.0), ("B step1: no exclusion", capped_scorer(e, None, 0.4), 0.0),
                   ("C step1+5: no exclusion + tuned context cap/backoff", capd, 0.0), ("D step1+5+2: + char12 hybrid", hyb, 0.0),
                   ("E step1+5+2+7: + personalisation (recency cache)", hyb, lam)]
        res = {"tuned": log, "systems": {}}; pers = {}
        for nm, sc, l in systems:
            r = {}; pers[nm] = {}
            for k, v in tests.items():
                s, per, h = run_stream(v, sc, pool, lam=l); r[k] = dict(ksr_pct=s, top1=h[1], top3=h[3], top5=h[5], top10=h[10]); pers[nm][k] = per
            r["avg_ksr"] = (r["aac"]["ksr_pct"] + r["care"]["ksr_pct"]) / 2; res["systems"][nm] = r; print(lang, nm, round(r["avg_ksr"], 2), flush=True)
        a0 = systems[0][0]
        for nm, _, _ in systems[1:]:
            ci = {}
            for k in tests:
                lo, hi = boot_ci(pers[a0][k], pers[nm][k]); ci[k] = [round(lo, 2), round(hi, 2)]
            res["systems"][nm]["gain_vs_shipped_95ci_pp"] = ci
        out[lang] = res
        json.dump(out, open("results/final_" + "_".join(sys.argv[1:]) + ".json", "w"), indent=1)
