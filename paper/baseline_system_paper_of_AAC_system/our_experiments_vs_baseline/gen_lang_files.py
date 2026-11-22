"""Write one results text file per language from results/*.json."""
import json, os
os.makedirs("results_by_language", exist_ok=True)
R = lambda p: json.load(open(f"results/{p}"))
NM = {"en": "English", "hi": "Hindi", "mr": "Marathi", "gu": "Gujarati"}
f1 = lambda x: f"{x:.1f}"; f2 = lambda x: f"{x:.2f}"
cc = {**R("concept_en_hi.json"), **R("concept_mr.json"), **R("concept_gu.json")}; gen = R("gen.json")
def table(L, head, rows):
    cols = list(zip(*([head] + rows))); w = [max(len(str(c)) for c in col) for col in cols]
    L.append("  " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(head))); L.append("  " + "-+-".join("-" * x for x in w))
    for r in rows: L.append("  " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))
    L.append("")
for l in ("en", "hi", "mr", "gu"):
    m = R(f"main_{l}.json"); ab = R(f"ablate_{l}.json")[l]; L = []
    L += ["=" * 110, f" {NM[l].upper()} RESULTS - Indic AAC System (all experiments for this language)", "=" * 110,
          " Arrows: KSR ↑ higher is better | top-k hit ↑ higher is better | perplexity ↓ lower is better | latency ↓ lower is better", ""]
    src = {"en": "real English AAC dataset (GPT-generated dialogues)", "hi": "Hindi AAC dataset (per repo notes a translation of the English batches)",
           "mr": "MACHINE-TRANSLATED (NLLB-200) from the English splits - weaker evidence", "gu": "MACHINE-TRANSLATED (NLLB-200) from the English splits - weaker evidence"}[l]
    L += [f" Data: {src}", f" Train sentences {m['n_train']} | dev {m['n_dev']} | test AAC-user {m['n_test_aac']} + caregiver {m['n_test_care']}",
          f" Test OOV rate vs train vocabulary: AAC {f1(m['oov_rate_pct']['aac'])}%, caregiver {f1(m['oov_rate_pct']['care'])}%", ""]
    L += [" 1. NEXT-WORD PREDICTION (full test sets)", ""]
    rows = []
    for n, lab in (("freq_only", "frequency-only (floor)"), ("char12_ngram", "char 12-gram (n-gram reference)"), ("inf_gram_shipped", "OURS: ∞-gram (shipped)"),
                   ("inf_gram_ctx_cap2", "OURS: ∞-gram capped at 2 words")):
        k = m["ksr"][n]; h = k["all"]["hit_at_empty_prefix_pct"]
        rows.append([lab, f1(k["aac"]["ksr_pct"]), f1(k["care"]["ksr_pct"]), f1(k["all"]["ksr_pct"]), f1(h["1"]), f1(h["5"]), f1(h["10"])])
    table(L, ["System", "KSR AAC ↑", "KSR Care ↑", "KSR all ↑", "top-1% ↑", "top-5% ↑", "top-10% ↑"], rows)
    p = m["perplexity"]["all"]
    L += [f" Per-character perplexity ↓ (all test): char 12-gram {f2(p['char12_ngram'])} | ∞-gram open-vocab {f2(p['inf_gram_openvocab'])} (word model; indicative only)",
          f" Latency ↓: ∞-gram {m['latency_ms']['inf_gram_next_word_top10']:.3f} ms per top-10 prediction (CPU); char 12-gram {m['latency_ms']['char12_ngram_per_char']:.3f} ms/char", ""]
    L += [" 2. ABLATION - selected-word exclusion and backoff (KSR ↑, AAC / Care)", ""]
    table(L, ["Variant", "KSR AAC ↑", "KSR Care ↑"], [[n, f2(v["aac"]["ksr_pct"]), f2(v["care"]["ksr_pct"])] for n, v in ab.items()])
    L += [" 3. SENTENCE GENERATION & FIDELITY (131 determinate + 13 ambiguous selections)", ""]
    rows = []
    for s, lab in (("ours_template+gate", "ours: realiser+gate"), ("literal_symbols", "literal word list")):
        d = gen[l][s]; n = d["n"]; pc = lambda k: f"{d.get(k,0)}/{n} ({100*d.get(k,0)/n:.0f}%)"
        rows.append([lab, pc("gate_accept"), pc("act_ok"), pc("entity_ok"), pc("neg_ok"), pc("no_additions"), f"{d.get('abstained_correctly',0)}/{d['n_amb']}"])
    table(L, ["System", "gate accepts ↑", "act correct ↑", "entity kept ↑", "negation kept ↑", "no additions ↑", "ambiguous: asked ↑"], rows)
    c = cc[l]
    L += [" 4. CONCEPT-LEVEL PREDICTOR (board symbols)", f"  words mapped to the 69-concept board: {f1(c['word_to_concept_coverage_pct'])}% | events {c['next_concept_events']} | hit@1 {f1(c['hit_pct']['1'])}% | hit@5 {f1(c['hit_pct']['5'])}% | hit@10 {f1(c['hit_pct']['10'])}%", ""]
    if l == "en":
        L += [" 5. COMPARISON WITH THE BASELINE'S METHODS (same 80+80 test subsample; KSR on 40+40)", ""]
        M = R("llm_en.json")["models"]; rows = []
        for k, lab in (("AAC char 12-gram (our-data analogue of baseline n-gram)", "char 12-gram (baseline-type n-gram)"), ("facebook/opt-125m (pretrained)", "OPT-125m pretrained"), ("facebook/opt-350m (pretrained)", "OPT-350m pretrained"),
                       ("facebook/opt-125m (adapted on our train split)", "OPT-125m adapted on our data  <- BEST accuracy"), ("Ours: infinity-gram (shipped predictor)", "OURS: ∞-gram")):
            d = M[k]; rows.append([lab, f2(d["perplexity"]["all"]), f1((d["ksr"]["aac"]["ksr_pct"] + d["ksr"]["care"]["ksr_pct"]) / 2), f1((d["ksr"]["aac"]["hit_at_empty_prefix_pct"]["5"] + d["ksr"]["care"]["hit_at_empty_prefix_pct"]["5"]) / 2)])
        table(L, ["System", "perplexity ↓", "KSR avg ↑", "top-5 hit % ↑"], rows)
        L += [" Verdict: the adapted OPT-125m is the most accurate; ours is the fastest (CPU, ~0.045 ms) and slightly better than the baseline-type n-gram."]
    L += ["", " See ../../RESULTS_vs_baseline.txt for setup, caveats and the full cross-language comparison."]
    open(f"results_by_language/{NM[l].lower()}_results.txt", "w", encoding="utf-8").write("\n".join(L))
print("written")
