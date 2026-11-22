"""Builds the Results_10 (frozen) vs current-system comparison table straight from the JSON files (no hand-typed numbers).
   python make_comparison_table.py > ../comparison_table.txt   (stdout is a Markdown table)"""
import json, os
R10 = "../Results_10/results_json"; RES = "results"
L = [("en", "English"), ("hi", "Hindi"), ("mr", "Marathi"), ("gu", "Gujarati")]
I = "I = E+COV top-50 + adapted BLOOM (w_cpu=0.1)"; COV = "E+COV (CPU only)"
def j(p): return json.load(open(p))
def avg(d, k): return (d["aac"][k] + d["care"][k]) / 2
rows = {}
for l, _ in L:
    s5 = j(f"{RES}/step5_{l}.json"); sysd = s5["systems"]; r10 = j(f"{R10}/main_{l}.json")
    A = sysd["A shipped infinity-gram"]; C = sysd[COV]; B = sysd[I]
    ppl_ad = s5.get("char_ppl_full_test", {}).get("bloom_adapted") or j(f"{RES}/step2_{l}.json")["char_ppl"]["bloom_adapted"]
    k10 = s5["lm_latency_ms_one_batch_gpu"]["10"]
    lat = j(f"{RES}/step9_latency.json").get(l) if os.path.exists(f"{RES}/step9_latency.json") else None
    gi = B["gain_vs_shipped_95ci_pp"]; gc = C["gain_vs_shipped_95ci_pp"]
    rows[l] = dict(
        ksr=(A["avg_ksr"], C["avg_ksr"], B["avg_ksr"]), aac=(A["aac"]["ksr_pct"], C["aac"]["ksr_pct"], B["aac"]["ksr_pct"]),
        care=(A["care"]["ksr_pct"], C["care"]["ksr_pct"], B["care"]["ksr_pct"]),
        top={K: (avg(A, f"top{K}"), avg(C, f"top{K}"), avg(B, f"top{K}")) for K in (1, 3, 5, 10)},
        ppl=(r10["perplexity"]["all"]["char12_ngram"], r10["perplexity"]["all"]["inf_gram_openvocab"], ppl_ad),
        lat=(r10["latency_ms"]["inf_gram_next_word_top10"], lat, k10["p50_ms"], k10["p95_ms"]),
        gain_cov=gc, gain_i=gi, oov=r10["oov_rate_pct"]["all"])
f = lambda x: f"{x:.2f}"; sg = lambda x: f"{x:+.2f}"
hdr = "| Metric (↑ higher better, ↓ lower better) | " + " | ".join(n for _, n in L) + " |"
out = ["Each cell: **Results_10 (frozen shipped system) → now CPU-only (E+COV, in backend) → now best (I = E+COV + adapted BLOOM-560m, K=50)**  (change best vs Results_10)", "", hdr, "|---|" + "---|" * len(L)]
def row(name, fn): out.append(f"| {name} | " + " | ".join(fn(rows[l], l) for l, _ in L) + " |")
row("**KSR % ↑** (mean AAC+caregiver)", lambda r, l: f"{f(r['ksr'][0])} → {f(r['ksr'][1])} → **{f(r['ksr'][2])}** (**{sg(r['ksr'][2]-r['ksr'][0])}**)")
row("KSR % ↑ AAC-user turns", lambda r, l: f"{f(r['aac'][0])} → {f(r['aac'][1])} → {f(r['aac'][2])} ({sg(r['aac'][2]-r['aac'][0])})")
row("KSR % ↑ caregiver turns", lambda r, l: f"{f(r['care'][0])} → {f(r['care'][1])} → {f(r['care'][2])} ({sg(r['care'][2]-r['care'][0])})")
for K in (1, 3, 5, 10):
    row(f"top-{K} hit % ↑ (nothing typed)", lambda r, l, K=K: f"{f(r['top'][K][0])} → {f(r['top'][K][1])} → {f(r['top'][K][2])} ({sg(r['top'][K][2]-r['top'][K][0])})")
row("char perplexity ↓ (full test)", lambda r, l: f"{f(r['ppl'][1])} → not measured → **{f(r['ppl'][2])}** ({(r['ppl'][2]/r['ppl'][1]-1)*100:+.0f}%)")
row("(char 12-gram perplexity, for reference)", lambda r, l: f"{f(r['ppl'][0])} (unchanged)")
row("latency ↓ CPU per next-word call (p50)", lambda r, l: f"{r['lat'][0]:.2f} ms → {r['lat'][1]:.1f} ms → {r['lat'][1]:.1f} ms CPU + LM batch {r['lat'][2]:.0f} ms p50 / {r['lat'][3]:.0f} ms p95 (K=10, shared GPU)")
row("95% CI of KSR gain vs Results_10 (pp, AAC / care)", lambda r, l: f"CPU-only [{r['gain_cov']['aac'][0]}, {r['gain_cov']['aac'][1]}] / [{r['gain_cov']['care'][0]}, {r['gain_cov']['care'][1]}]; best [{r['gain_i']['aac'][0]}, {r['gain_i']['aac'][1]}] / [{r['gain_i']['care'][0]}, {r['gain_i']['care'][1]}]")
row("test OOV rate % (never suggestible by a fixed vocabulary)", lambda r, l: f"{r['oov']:.1f} → reachable once ≥2 letters typed (COV) → same")
print("\n".join(out))
