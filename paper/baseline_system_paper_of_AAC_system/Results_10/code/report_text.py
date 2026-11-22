_h = open("report_head.txt", encoding="utf-8").read(); _i = _h.index(" 0. READ THIS FIRST") - 111
P(_h[:_i])

# ───────── VERDICT BLOCK (inserted right after the header) ─────────
M_ = llm["models"]
cands = [("AAC char 12-gram (baseline-type n-gram)", "AAC char 12-gram (our-data analogue of baseline n-gram)", 0.03, "CPU"),
         ("OPT-125m pretrained (baseline LLM method)", "facebook/opt-125m (pretrained)", 25, "GPU"),
         ("OPT-350m pretrained (baseline LLM method)", "facebook/opt-350m (pretrained)", 140, "GPU"),
         ("OPT-125m adapted on our data (baseline's adaptation)", "facebook/opt-125m (adapted on our train split)", 25, "GPU"),
         ("OURS: infinity-gram", "Ours: infinity-gram (shipped predictor)", 0.045, "CPU")]
def mk(k): d = M_[k]; return dict(ppl=d["perplexity"]["all"], ksr=(d["ksr"]["aac"]["ksr_pct"] + d["ksr"]["care"]["ksr_pct"]) / 2,
        top5=(d["ksr"]["aac"]["hit_at_empty_prefix_pct"]["5"] + d["ksr"]["care"]["hit_at_empty_prefix_pct"]["5"]) / 2)
V = [(n, mk(k), ms, dev) for n, k, ms, dev in cands]
def rank(key, rev):
    o = sorted(range(len(V)), key=lambda i: (V[i][1][key] if key != "ms" else V[i][2]), reverse=rev); r = [0] * len(V)
    for p, i in enumerate(o): r[i] = p + 1
    return r
rp, rk, rt, rs = rank("ppl", False), rank("ksr", True), rank("top5", True), rank("ms", False)
P("""
==============================================================================================================
 A. ENGLISH VERDICT - OUR SYSTEM vs THE BASELINE'S METHODS  (read this first)
==============================================================================================================
 HOW TO READ THE ARROWS
   KSR (keystroke savings, %)      ↑  HIGHER is BETTER   (more keystrokes saved for the user)
   top-5 hit rate (%)              ↑  HIGHER is BETTER   (target word is on the 5-word shelf with nothing typed)
   perplexity (per character)      ↓  LOWER  is BETTER   (model is less 'surprised' by the real text)
   speed (ms per prediction)       ↓  LOWER  is BETTER   (faster / usable without a GPU)
   '#1' = best in that column, '#5' = worst.   Same data, same test sentences, same protocol for every row.
""")
rows = []
for i, (n, m, ms, dev) in enumerate(V):
    rows.append([n, f"{m['ksr']:.1f} ↑ (#{rk[i]})", f"{m['top5']:.1f} ↑ (#{rt[i]})", f"{m['ppl']:.2f} ↓ (#{rp[i]})", f"{ms:g} ms {dev} ↓ (#{rs[i]})"])
table(["System", "KSR % ↑", "top-5 hit % ↑", "perplexity ↓", "speed ↓"], rows)
best_k = max(range(len(V)), key=lambda i: V[i][1]["ksr"]); ours = len(V) - 1
P(f""" BEST ON ACCURACY (KSR, top-5, perplexity)  : {V[best_k][0]}  (KSR {V[best_k][1]['ksr']:.1f}% vs ours {V[ours][1]['ksr']:.1f}%)
 BEST ON SPEED / NO-GPU                           : OURS (infinity-gram), ~0.045 ms on CPU - fastest of all five
 OURS vs THE BASELINE'S n-gram (same kind of model): OURS is slightly BETTER (KSR {V[ours][1]['ksr']:.1f} vs {V[0][1]['ksr']:.1f}; full test set 56.6 vs 56.2) - a small gain, within noise
 OURS vs THE BASELINE'S LLM approach              : OURS is WORSE on accuracy (KSR {V[ours][1]['ksr']:.1f} vs {V[1][1]['ksr']:.1f} / {V[2][1]['ksr']:.1f} / {V[3][1]['ksr']:.1f}),
                                                    but ~500-3000x FASTER and needs no GPU.
 So: our ∞-gram is NOT the best English next-word predictor. The best is the baseline-style LLM adapted on in-domain data.
 Our approach is best on speed/footprint and, beyond prediction, on sentence generation + safety (Section 4), which the
 baseline does not have at all.
 (KSR chance floor, frequency-only, is ~50%, so the useful range is roughly 50-65%.)
""")
P(_h[_i:])

M = llm["models"]; mean2 = lambda d: (d["aac"]["ksr_pct"] + d["care"]["ksr_pct"]) / 2
P("""
--------------------------------------------------------------------------------------------------------------
 2. EXPERIMENTAL SETUP (identical for every system)
--------------------------------------------------------------------------------------------------------------
 Data     : english_AAC_Dataset (277 conv.) and hindi_AAC_Dataset (375 conv.). Split BY CONVERSATION (hash of the
            first turn, so original/augmented/transformed copies never straddle splits): 70% train / 10% dev /
            20% test; any train sentence that also occurs verbatim in dev/test is removed. Test set "AAC-user"
            = the AAC user's intended utterances (the paper's 'written/AAC user' analogue); "Caregiver" = the
            conversation partner's turns (the paper's 'spoken' analogue).
            Marathi / Gujarati = NLLB-200 machine translation of the English splits (no native corpus exists);
            degenerate translations (a token repeated >=4 times, or >30 words) were removed.
 Text     : lower-cased, English reduced to a-z ' space (as in the paper); Indic reduced to script letters.
 Training : every system learns ONLY from the train split (tiny: ~2.5-3.9 k sentences vs. the paper's billions of
            characters), so absolute numbers are far from the paper's.
 Models   : ∞-gram            = our shipped AACInfinityGramEngine (suffix trie, backoff alpha=0.4), built on train only
            char 12-gram      = interpolated Witten-Bell character LM, order 12 (the baseline's 'AAC n-gram' analogue,
                                same order as the paper's, but trained on our small data instead of 21 B chars)
            OPT-125m/350m     = pretrained, queried with the paper's subword->character search algorithm (beam 8)
            OPT-125m adapted  = full fine-tune on our train split (the paper's 'in-domain adaptation'; best dev epoch)
            frequency-only    = floor baseline (most frequent matching words)
 Metrics  : per-character perplexity incl. spaces (lower better); keystroke savings (KSR) with 5 word predictions,
            the paper's exact protocol (predict before each word and after each typed prefix; one press selects a
            word + space); next-word hit rate at an empty prefix (what the on-screen "Top Words" shelf shows);
            latency per prediction.
            Candidate pool for KSR is the same for all systems: the 300 most frequent train-vocabulary words that
            match the typed prefix. OOV words must be typed in full.
 ∞-gram perplexity : the shipped engine returns ranked words, not a distribution, so perplexity uses a proper
            open-vocabulary version (backoff mass + unigram floor mu, plus a char-LM OOV term eps; mu/eps tuned on dev).
            Because a word model does not pay for emitting word boundaries, its perplexity is NOT strictly
            comparable with a character model's - treat that row as indicative only. KSR and hit rates ARE comparable.
""")
P("""--------------------------------------------------------------------------------------------------------------
 3. ENGLISH: OUR SYSTEM vs BASELINE-STYLE SYSTEMS   (analogue of paper Tables 1-4)
--------------------------------------------------------------------------------------------------------------
 3a. Same 80+80 test-sentence subsample for ALL systems (needed because the OPT search is slow).
     KSR was computed on 40+40 of those sentences (250 + 354 words). Small samples: differences < ~2 points are noise.
""")
rows = []
order = [("freq", None)]
def row(name, key, params, how):
    d = M[key]; rows.append([name, params, f2(d["perplexity"]["aac"]), f2(d["perplexity"]["care"]), f2(d["perplexity"]["all"]),
        f1(d["ksr"]["aac"]["ksr_pct"]), f1(d["ksr"]["care"]["ksr_pct"]), f1(mean2(d["ksr"])), f1((d["ksr"]["aac"]["hit_at_empty_prefix_pct"]["5"] + d["ksr"]["care"]["hit_at_empty_prefix_pct"]["5"]) / 2), how])
row("AAC char 12-gram (baseline-type n-gram)", "AAC char 12-gram (our-data analogue of baseline n-gram)", "n/a", "CPU 0.03 ms/char")
row("OPT-125m pretrained (search alg.)", "facebook/opt-125m (pretrained)", "125", "GPU ~25-80 ms/char*")
row("OPT-350m pretrained (search alg.)", "facebook/opt-350m (pretrained)", "331", "GPU ~140 ms/char*")
row("OPT-125m ADAPTED on our data", "facebook/opt-125m (adapted on our train split)", "125", "GPU ~25-80 ms/char*")
row("OURS: ∞-gram (shipped predictor)", "Ours: infinity-gram (shipped predictor)", "n/a", "CPU 0.045 ms/pred")
table(["System", "Params M", "ppl AAC ↓", "ppl Care ↓", "ppl avg ↓", "KSR AAC ↑", "KSR Care ↑", "KSR avg ↑", "top-5 hit% ↑", "speed"], rows)
P(""" * GPU timings were taken on a TITAN Xp that was shared with three other running jobs (the app server, a vLLM server and
   a translation job), so they are noisy (the paper: 55-120 ms on an A100). The n-gram/∞-gram timings are CPU, single thread.
 Perplexity: lower is better.  KSR (%): higher is better.   KSR chance floor (frequency-only) on this data is ~50%.
""")
r = main["en"]
P(" 3b. FULL English test sets (403 AAC-user + 402 caregiver sentences) for the non-LLM systems\n")
rows = []
for n, lab in (("freq_only", "frequency-only"), ("char12_ngram", "char 12-gram"), ("inf_gram_shipped", "OURS ∞-gram (shipped)")):
    k = r["ksr"][n]; rows.append([lab, f1(k["aac"]["ksr_pct"]), f1(k["care"]["ksr_pct"]), f1(k["all"]["ksr_pct"]), f1(k["all"]["hit_at_empty_prefix_pct"]["1"]), f1(k["all"]["hit_at_empty_prefix_pct"]["5"]), f1(k["all"]["hit_at_empty_prefix_pct"]["10"])])
table(["System", "KSR AAC ↑", "KSR Care ↑", "KSR all ↑", "top-1% ↑", "top-5% ↑", "top-10% ↑"], rows)
pp = r["perplexity"]
P(f" Perplexity (full sets): char 12-gram {f2(pp['aac']['char12_ngram'])} / {f2(pp['care']['char12_ngram'])} (AAC / Care);  ∞-gram open-vocab {f2(pp['aac']['inf_gram_openvocab'])} / {f2(pp['care']['inf_gram_openvocab'])}\n")
P(f""" Out-of-vocabulary rate of the test sets w.r.t. train vocabulary: AAC {f1(r['oov_rate_pct']['aac'])}%, Caregiver {f1(r['oov_rate_pct']['care'])}%.
""")
a = llm["adaptation_log_dev_token_loss"]
P(f""" 3c. Domain adaptation (paper Table 2 analogue): OPT-125m dev token loss {a[0][1]:.2f} (pretrained) -> {a[1][1]:.2f} after 1 epoch on
     our train split (best epoch; later epochs over-fit: {a[-1][1]:.2f} at epoch 5). Per-char perplexity 2.65 -> 2.07 and KSR
     {f1(mean2(M['facebook/opt-125m (pretrained)']['ksr']))} -> {f1(mean2(M['facebook/opt-125m (adapted on our train split)']['ksr']))}. In-domain adaptation helps a lot, as in the paper (2.30 -> 2.07).

 3d. READING OF SECTION 3 (honest)
   * Accuracy: the in-domain-adapted OPT-125m is clearly the best predictor here (KSR ~{f1(mean2(M['facebook/opt-125m (adapted on our train split)']['ksr']))}% vs ~{f1(mean2(M['Ours: infinity-gram (shipped predictor)']['ksr']))}% for ours).
     Even pretrained OPT beats our ∞-gram by ~2-3 KSR points. The baseline paper's central finding (LLMs > n-gram) is REPRODUCED
     on our data, and our ∞-gram does NOT beat LLMs on prediction accuracy.
   * ∞-gram vs the n-gram it replaces: on the full test sets the ∞-gram is level with a char 12-gram (KSR 56.6 vs 56.2) and
     better on top-10 hit rate (42.8 vs 41.5). It is a small, consistent but not large gain.
   * Where the ∞-gram does win: cost. 0.045 ms on one CPU thread with no GPU (OPT: tens of ms on a GPU, i.e. roughly 500-3000x slower, noisy),
     builds in <0.5 s from the JSONL data, fully inspectable (it shows the matched depth) and can only suggest words seen in its corpus.
     The baseline paper itself lists GPU-only inference as its main limitation; that is the niche our engine fills.
   * Our system's contribution is NOT better next-word prediction than an LLM. See Experiment 4 below for what it adds.
""")
P("""--------------------------------------------------------------------------------------------------------------
 4. EXPERIMENT 4 - SENTENCE GENERATION & FIDELITY (something the baseline cannot do) - EN / HI / GU / MR
--------------------------------------------------------------------------------------------------------------
 Suite: 144 symbol selections built from the 69-concept board (requests, refusals, feelings, feeling+request, help, actions,
 plus 13 deliberately AMBIGUOUS selections: a person alone, double negation, two feelings). Same concept IDs in all four
 languages. Our realiser+gate is compared with the "literal" output = symbols spoken as a bare word list (what a plain symbol
 board does). The 131 determinate cases are scored; for the 13 ambiguous ones the correct behaviour is to ASK, not invent.
 NOTE: the gate is also the grader for 'gate accept', so that column is partly circular; the 'independent' columns use a
 separate regex check (negator word present iff negation is required; every selected label stem present).
""")
heads = ["Language", "System", "gate accepts", "act correct", "entity kept", "negation kept", "indep. negation", "indep. entity*", "no additions", "native script", "ambig. handled"]
rows = []
nm = {"en": "English", "hi": "Hindi", "mr": "Marathi", "gu": "Gujarati"}
for l in ("en", "hi", "mr", "gu"):
    for s, lab in (("ours_template+gate", "ours: realiser+gate"), ("literal_symbols", "literal word list")):
        d = gen[l][s]; n = d["n"]; pc = lambda k: f"{d.get(k,0)}/{n} ({100*d.get(k,0)/n:.0f}%)"
        rows.append([nm[l] if s.startswith("ours") else "", lab, pc("gate_accept"), pc("act_ok"), pc("entity_ok"), pc("neg_ok"), pc("neg_indep_ok"), pc("entity_indep_ok"), pc("no_additions"), pc("native_script_ok"),
                     f"{d.get('abstained_correctly',0)}/{d['n_amb']} asked" ])
table(heads, rows)
P(""" * 'indep. entity' is a crude 3-character-stem substring test; its misses (7-13 per language) are inflected forms, not dropped
   concepts (the gate, which handles inflection, reports 127-130/131). One case per language is 'unsupported' (the
   selection "I + go + school" has no template) and is counted as a failure above.
 Examples (selection -> output):  English  'No Want Medicine' -> 'I do not want medicine.'   'Pain Medicine' -> 'I am in pain, I want medicine.'
                                  Gujarati 'ના જોઈએ દવા' -> 'મને દવા નથી જોઈતી.'              Gujarati 'દુખાવો દવા' -> 'મને દુખાવો થાય છે, મને દવા જોઈએ છે.'
 Reading: the deterministic route turns telegraphic symbol strings into correct, polarity-preserving, native-script first-person
 sentences in 97-99% of determinate cases in every language, versus 16-41% for speaking the symbols as-is, and it refuses to
 guess on all 13 ambiguous selections (the literal route "invents" an interpretation for all of them). Caveats: these are
 template/lexicon cases authored by the system's developers (a closed 69-concept board), not free user input; the Qwen
 cascade path was NOT run here (needs the live backend), and the repo's own older 10-case run reports 90% validity with
 4/10 falling back to templates.
""")
P("""--------------------------------------------------------------------------------------------------------------
 5. EXPERIMENT 5 - ABLATIONS OF THE ∞-GRAM  (English; KSR %, AAC-user / caregiver test)
--------------------------------------------------------------------------------------------------------------
""")
rows = []
for nme in abl["en"]["en"]:
    d = abl["en"]["en"][nme]; rows.append([nme, f"{d['aac']['ksr_pct']:.2f}", f"{d['care']['ksr_pct']:.2f}"])
table(["Variant", "KSR AAC ↑", "KSR Care ↑"], rows)
cap = r["ksr"]
P(f""" Context-depth cap (full test, KSR avg): 1 word {f1(cap['inf_gram_ctx_cap1']['all']['ksr_pct'])} | 2 words {f1(cap['inf_gram_ctx_cap2']['all']['ksr_pct'])} | 3 words {f1(cap['inf_gram_ctx_cap3']['all']['ksr_pct'])} | unlimited (shipped) {f1(cap['inf_gram_shipped']['all']['ksr_pct'])}
 Findings: (1) ARBITRARY CONTEXT DEPTH DOES NOT HELP on this corpus - a 2-word cap is as good or slightly better in all four languages; the
 sentences are short (7 words on average), so there is little long context to exploit. The "∞" advantage is not demonstrated here.
 (2) The shipped rule "never re-suggest an already selected word" COSTS a little accuracy: removing it gains (AAC / Care KSR points)
 +0.4 / +0.3 (EN), +0.9 / +1.1 (HI), +0.3 / +0.6 (MR), +0.6 / +0.8 (GU). Backoff alpha (0.1-0.7) makes no difference.
 Small but consistent in all four languages - a cheap, safe improvement (single run, so not significance-tested).
""")
P("""--------------------------------------------------------------------------------------------------------------
 6. HINDI, MARATHI, GUJARATI - EFFECTIVENESS OF OUR SYSTEM  (NOT compared with the baseline)
--------------------------------------------------------------------------------------------------------------
 The baseline is English-only, so there is nothing to compare against. For context, each row also shows the character 12-gram
 trained on the same data and the frequency-only floor (internal references, not the baseline paper).
 Hindi = the repo's Hindi dataset (per the repo notes it mirrors the English batches, produced with opus-mt translation).
 Marathi, Gujarati = NLLB machine translation of the English splits; they inherit translation errors and English-derived
 phrasing, and the Marathi OOV rate is higher, so treat them as weaker evidence than English/Hindi.
 6a. Next-word prediction, full test sets.  KSR with 5 predictions (%), top-k = next-word hit rate with nothing typed yet.
""")
rows = []
for l in ("en", "hi", "mr", "gu"):
    m = main[l]
    for n, lab in (("freq_only", "frequency-only"), ("char12_ngram", "char 12-gram"), ("inf_gram_shipped", "OURS ∞-gram")):
        k = m["ksr"][n]; h = k["all"]["hit_at_empty_prefix_pct"]
        rows.append([nm[l] if n == "freq_only" else "", f"{m['n_train']}/{m['n_test_aac']+m['n_test_care']}" if n == "freq_only" else "", lab, f1(k["aac"]["ksr_pct"]), f1(k["care"]["ksr_pct"]), f1(k["all"]["ksr_pct"]), f1(h["1"]), f1(h["5"]), f1(h["10"]),
                     (f2(m["perplexity"]["all"]["char12_ngram"]) if n == "char12_ngram" else f2(m["perplexity"]["all"]["inf_gram_openvocab"]) if n == "inf_gram_shipped" else "")])
table(["Lang", "train/test sents", "System", "KSR AAC ↑", "KSR Care ↑", "KSR all ↑", "top-1% ↑", "top-5% ↑", "top-10% ↑", "ppl/char ↓"], rows)
P(" ppl/char: Devanagari/Gujarati characters are Unicode code points (a consonant+matra = 2 keystrokes), so KSR/ppl are not directly comparable across scripts.\n")
P(" 6b. Same ∞-gram with the 'exclude selected words' rule removed (suggested fix), KSR avg of AAC/Care test:\n")
rows = []
for l in ("en", "hi", "mr", "gu"):
    d = abl[l][l]; s = [v for k, v in d.items() if k.startswith("shipped")][0]; n = d["no exclusion, alpha=0.4"]
    rows.append([nm[l], f1((s["aac"]["ksr_pct"] + s["care"]["ksr_pct"]) / 2), f1((n["aac"]["ksr_pct"] + n["care"]["ksr_pct"]) / 2), f1(main[l]["ksr"]["char12_ngram"]["all"]["ksr_pct"])])
table(["Lang", "shipped KSR ↑", "without exclusion KSR ↑", "char 12-gram KSR ↑"], rows)
P(" 6c. Concept-level predictor (the one the UI uses for Gujarati/Marathi). Hit rate of the next board concept in held-out sentences:\n")
cc = {**R("concept_en_hi.json"), **R("concept_mr.json"), **R("concept_gu.json")}
rows = [[nm[l], f1(cc[l]["word_to_concept_coverage_pct"]), cc[l]["next_concept_events"], f1(cc[l]["hit_pct"]["1"]), f1(cc[l]["hit_pct"]["5"]), f1(cc[l]["hit_pct"]["10"])] for l in ("en", "hi", "mr", "gu")]
table(["Lang", "words mapped to board %", "events", "top-1% ↑", "top-5% ↑", "top-10% ↑"], rows)
P(""" Only ~6-14% of dataset words are one of the 69 board concepts, so this predictor is evaluated on very few events (44-272);
 hit@10 of 29-45% is a rough indication, not a robust measure. It is language-independent by construction, which is why
 Gujarati and Marathi (for which, per the concept_predict.py docstring, the app relies on it) still get context-aware suggestions.
 IMPORTANT (a finding, not an experiment): the shipped ∞-gram routes Devanagari to its Hindi trie and everything else to
 the English trie. Marathi therefore shares the Hindi trie, and Gujarati has no model of its own in the app - the
 per-language ∞-gram numbers above were obtained by building a separate engine per language, which the app does not do today.
 6d. Latency (CPU, ms per top-10 prediction): """ + ", ".join(f"{nm[l]} {main[l]['latency_ms']['inf_gram_next_word_top10']:.3f}" for l in ("en", "hi", "mr", "gu")) + """
 Build time of the full ∞-gram from the shipped corpora: ~0.45 s.
""")
P("""--------------------------------------------------------------------------------------------------------------
 7. SUMMARY - WHAT THESE RESULTS SHOW ABOUT THE PROPOSED APPROACH
--------------------------------------------------------------------------------------------------------------
 SUPPORTED by the experiments
  1. Sentence generation with a deterministic gate (Exp 4): in all four languages the system produces a correct, polarity- and
     entity-preserving, native-script sentence for 97-99% of determinate selections (literal symbol output: 16-41%) and abstains
     on 13/13 ambiguous selections. The baseline paper offers nothing at this layer.
  2. Efficiency: the ∞-gram predicts in ~0.05 ms on a CPU with no GPU, roughly 500-3000x faster than OPT character search,
     with keystroke savings within ~1 point of a 12-gram char LM in all four languages (slightly ahead in English, slightly
     behind as shipped in Hindi/Marathi/Gujarati; level or ahead once the selected-word exclusion is removed, except Gujarati).
  3. Multilingual coverage: the same pipeline works in Hindi, Marathi and Gujarati with prediction accuracy (KSR 49-57%)
     in the same range as English (56%), measured on translated text for mr/gu.
 NOT supported / negative findings
  4. Prediction accuracy vs LLMs: an in-domain-adapted OPT-125m beats our ∞-gram by ~7 KSR points and ~1.5 perplexity;
     even pretrained OPT-125m/350m win by ~2-3 points. The paper's "LLMs > n-gram" conclusion holds on our data.
  5. The "infinite" context depth gives no measurable benefit on this short-sentence corpus (2-word cap is as good).
  6. The 'exclude already-selected words' rule costs 0.3-1.1 KSR points; removing it is a free improvement.
 LIMITATIONS
  * Small synthetic corpus (no real AAC users); small test sets (few hundred sentences); LLM comparison on an 80+80 sentence
    subsample (KSR on 40+40); single run, single split, no confidence intervals - differences < ~2 points should be read as ties.
  * The baseline's own models, private data and adaptation corpora were unavailable; absolute values are not comparable with the paper.
  * mr/gu text is machine translated (after removing 4-11% degenerate outputs); the Hindi data are, per the repo notes, themselves a translation of the English batches.
  * Not run: Qwen cascade end-to-end validity/latency, TTS intelligibility/naturalness (MOS portal is separate), user study.
 SUGGESTED NEXT STEPS (cheap -> costly):  drop the selected-word exclusion; add a small adapted LM (e.g. OPT-125m-class, 25 ms on a
 GPU) as an optional re-ranker on top of the ∞-gram candidates; build per-language ∞-gram engines for mr/gu; collect a small native
 Marathi/Gujarati test set; run the live-backend LLM-cascade evaluation and the MOS study.
""")
