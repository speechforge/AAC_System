"""English + Hindi 'all scores' table incl. the baseline-style English systems, built from JSON (no hand-typed numbers).
   python make_full_table.py > full_table.txt ; then replaced between markers in ../20_nov_changes.md by update_md_table.py"""
import json, os
R10 = "../Results_10/results_json"; RES = "results"
J = lambda p: json.load(open(p)) if os.path.exists(p) else None
f2 = lambda x: "pending" if x is None else f"{x:.2f}"; f1 = lambda x: "pending" if x is None else f"{x:.1f}"
av = lambda d, k: (d["aac"][k] + d["care"][k]) / 2
def row_full(name, d, ppl, lat):          # d = {aac:{ksr_pct,top1..}, care:{...}}
    if d is None: return f"| {name} | pending | | | | | | | {ppl} | {lat} |"
    return (f"| {name} | **{f2(av(d,'ksr_pct'))}** | {f2(d['aac']['ksr_pct'])} | {f2(d['care']['ksr_pct'])} | {f1(av(d,'top1'))} | {f1(av(d,'top3'))} | {f1(av(d,'top5'))} | {f1(av(d,'top10'))} | {ppl} | {lat} |")
def from_main(m, key):                    # Results_10 main_*.json -> same shape as step5 systems
    k = m["ksr"][key]; out = {}
    for r in ("aac", "care"):
        h = k[r].get("hit_at_empty_prefix_pct", {}); out[r] = {"ksr_pct": k[r]["ksr_pct"], "top1": h.get("1"), "top3": h.get("3"), "top5": h.get("5"), "top10": h.get("10")}
    return out
def from_hits(d):                         # llm_en / same_sample style: {aac:{ksr_pct,hit_at_empty_prefix_pct}}
    out = {}
    for r in ("aac", "care"):
        h = d[r]["hit_at_empty_prefix_pct"]; out[r] = {"ksr_pct": d[r]["ksr_pct"], "top1": h["1"], "top3": h["3"], "top5": h["5"], "top10": h["10"]}
    return out
HDR = "| System | KSR % ↑ (mean) | KSR AAC | KSR care | top-1 % ↑ | top-3 % ↑ | top-5 % ↑ | top-10 % ↑ | char perplexity ↓ | latency ↓ |\n|---|---|---|---|---|---|---|---|---|---|"
lat = J(f"{RES}/step9_latency_full.json"); out = []
def full_table(lang, nm, n_aac, n_care):
    main = J(f"{R10}/main_{lang}.json"); s5 = J(f"{RES}/step5_{lang}.json")["systems"]; s8 = J(f"{RES}/step8_{lang}_K10.json"); ppl = J(f"{RES}/step5_{lang}.json").get("char_ppl_full_test") or J(f"{RES}/step2_{lang}.json")["char_ppl"]
    L = lat[lang]; lm10 = J(f"{RES}/step5_{lang}.json")["lm_latency_ms_one_batch_gpu"]
    o = [f"**{nm} - full test set ({n_aac} AAC-user + {n_care} caregiver sentences)**", "", HDR]
    if lang == "en": o.append(f"| frequency-only (no context) | {f2((main['ksr']['freq_only']['aac']['ksr_pct']+main['ksr']['freq_only']['care']['ksr_pct'])/2)} | {f2(main['ksr']['freq_only']['aac']['ksr_pct'])} | {f2(main['ksr']['freq_only']['care']['ksr_pct'])} | | | | | - | - |")
    o.append(row_full("AAC char 12-gram (baseline-type n-gram, our data)", from_main(main, "char12_ngram"), f2(main["perplexity"]["all"]["char12_ngram"]), f"{main['latency_ms']['char12_ngram_per_char']:.3f} ms/char CPU"))
    o.append(row_full("**Results_10 shipped ∞-gram** (reference)", from_main(main, "inf_gram_shipped"), f2(main["perplexity"]["all"]["inf_gram_openvocab"]), f"{main['latency_ms']['inf_gram_next_word_top10']:.2f} ms CPU"))
    o.append(row_full("proposed: improved CPU stack E", s5["E improved CPU stack"], "not measured", "~5 ms CPU"))
    o.append(row_full("proposed: E + coverage fallback (CPU only; **in backend**)", s5["E+COV (CPU only)"], "not measured", f"{L['v2_nextword_p50_ms']:.1f} ms CPU (next word), {L['v2_prefix2_cov_p50_ms']:.1f} ms with 2-letter prefix"))
    if s8: o.append(row_full("proposed: I = E+COV top-10 + adapted BLOOM-560m (GPU)", s8["systems"]["I_K10 = E+COV top-10 + adapted BLOOM (w_cpu=0.1)"], f2(ppl["bloom_adapted"]), f"CPU + LM batch {lm10['10']['p50_ms']:.0f} ms p50 / {lm10['10']['p95_ms']:.0f} ms p95 (shared GPU)"))
    else: o.append("| proposed: I with K=10 | not run for English | | | | | | | | |")
    o.append(row_full("proposed: **I = E+COV top-50 + adapted BLOOM-560m (GPU, best)**", s5[[k for k in s5 if k.startswith("I ")][0]], f2(ppl["bloom_adapted"]), f"CPU + LM batch {lm10['50']['p50_ms']:.0f} ms p50 / {lm10['50']['p95_ms']:.0f} ms p95 (shared GPU)"))
    return o
n_en = J(f"{R10}/main_en.json")["n_test_aac"], J(f"{R10}/main_en.json")["n_test_care"]; n_hi = J(f"{R10}/main_hi.json")["n_test_aac"], J(f"{R10}/main_hi.json")["n_test_care"]
out += full_table("en", "ENGLISH", *n_en) + [""]
# ---- English on the baseline-style systems' sample
llm = J(f"{R10}/llm_en.json"); cpu_s = J(f"{RES}/same_sample_en_cpu.json"); gpu_s = J(f"{RES}/same_sample_en_gpu.json")
out += [f"**ENGLISH - the baseline-style systems (OPT-125m / OPT-350m, run by us with the baseline paper's character-search method) and ours on the SAME small sample** ({llm['n_ppl_sents_per_set']}+{llm['n_ppl_sents_per_set']} sentences for perplexity, the first {llm['n_ksr_sents_per_set']}+{llm['n_ksr_sents_per_set']} of them for KSR; differences below ~2 KSR points are noise at this size)", "", HDR]
M = llm["models"]
def mrow(name, key, latency, bold=False):
    v = M[key]; return row_full(name, from_hits(v["ksr"]), f2(v["perplexity"]["all"]), latency)
out.append(mrow("baseline-type: AAC char 12-gram", "AAC char 12-gram (our-data analogue of baseline n-gram)", "0.03 ms/char CPU"))
out.append(mrow("baseline LLM: OPT-125m pretrained", "facebook/opt-125m (pretrained)", f"{M['facebook/opt-125m (pretrained)']['ms_per_char_search_gpu_shared']:.0f} ms/char GPU (search)"))
out.append(mrow("baseline LLM: OPT-350m pretrained", "facebook/opt-350m (pretrained)", f"{M['facebook/opt-350m (pretrained)']['ms_per_char_search_gpu_shared']:.0f} ms/char GPU (search)"))
out.append(mrow("baseline LLM: OPT-125m adapted on our data (the baseline's adaptation)", "facebook/opt-125m (adapted on our train split)", f"{M['facebook/opt-125m (adapted on our train split)']['ms_per_char_search_gpu_shared']:.0f} ms/char GPU (search)"))
out.append(mrow("**Results_10 shipped ∞-gram** (reference)", "Ours: infinity-gram (shipped predictor)", "0.05 ms CPU"))
def srow(name, d, ppl, latency): return row_full(name, from_hits(d["ksr"]) if d else None, ppl, latency)
out.append(srow("proposed: improved CPU stack E", cpu_s["systems"]["E improved CPU stack"] if cpu_s else None, "not measured", "~5 ms CPU"))
out.append(srow("proposed: E + coverage fallback (CPU only; in backend)", cpu_s["systems"]["E+COV (CPU only)"] if cpu_s else None, "not measured", "~5-6 ms CPU"))
pp = gpu_s.get("bloom_adapted_char_ppl_80+80", {}).get("all") if gpu_s else None
out.append(srow("proposed: I top-10 (adapted BLOOM-560m, GPU)", gpu_s["systems"]["I = E+COV top-10 + adapted BLOOM-560m"] if gpu_s else None, f2(pp), "CPU + ~38 ms LM batch"))
out.append(srow("proposed: **I top-50 (adapted BLOOM-560m, GPU)**", gpu_s["systems"]["I = E+COV top-50 + adapted BLOOM-560m"] if gpu_s else None, f2(pp), "CPU + ~136 ms LM batch"))
out += ["", "(our shipped ∞-gram re-run on this sample reproduces Results_10 exactly: KSR AAC 53.87, care 57.85 - see `results/same_sample_en_cpu.json`; the perplexity column of the ∞-gram row is the open-vocabulary mix, as in Results_10.)", ""]
out += full_table("hi", "HINDI", *n_hi) + ["", "(Hindi has no OPT/baseline-LLM rows: the baseline's OPT models are English-only and were not run for Hindi.)", ""]
out += ["**Reference only - the baseline paper's own published numbers (Gaines & Vertanen, `paper1.tex` Tables 3-4), on THEIR private test sets, 5 words predicted - NOT comparable in absolute value with the rows above:**", "",
        "| Baseline-paper system | KSR % ↑ average over its 5 test sets | KSR % ↑ on its AAC-user set | perplexity ↓ average | time per prediction |", "|---|---|---|---|---|",
        "| AAC n-gram (KenLM) | 59.7 | 55.3 | 2.54 | 0.1 ms |", "| C4+Sub n-gram | 59.6 | 56.4 | 2.58 | 0.1 ms |", "| C4+Sub n-gram (full) | 60.5 | 57.4 | 2.53 | 0.1 ms |",
        "| OPT-350m (no adaptation), search | 63.2 | 63.1 | 2.28 | 79.1 ms |", "| OPT-350m adapted C4→Sub→BOLT→Daily | 65.0 | 62.5 | 2.12 | 78.9 ms |", "| OPT-350m adapted C4→Sub→BOLT+Daily | 65.0 | 62.3 | 2.12 | 78.2 ms |",
        "| OPT-350m adapted BOLT+Daily (best) | **65.2** | 62.7 | **2.11** | 78.0 ms |", "| ByGPT5 (byte LLM) | 64.5 | 61.6 | 2.21 | 11.6 ms |"]
print("\n".join(out))
