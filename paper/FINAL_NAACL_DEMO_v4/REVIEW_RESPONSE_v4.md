# Response to the six review points, and what changed in v4 (2026-11-23)

v4 = `latex_source_v4/` (a copy of the proof-read v3 `after_the_proof_reading_final_version/latex_source_final/`, edited).
v3 is left unchanged except for one added file (`qa_scripts/paired_group_bootstrap.py`).
**Not compiled here** (no TeX engine on this machine, and downloading one was not permitted): build on Overleaf with
XeLaTeX and check the page limits (see "Page budget" at the end).

Two builds are named explicitly everywhere in v4, because mixing them caused point 3:
- **Evaluated build** = the frozen 11-12 November system that Sections 4-5 score (commit `fe4e185`; placeholder tone, no speech).
- **Current build** = the system on 23 November 2026 (branch `November_22_2026`, commit `3aacff6`): UI redesign (16 Nov),
  per-language predictor + LoRA re-ranker (20-23 Nov), personal vocabulary + phrase row, switch/dwell access, real IndicF5 speech.

---

## 1. "Template beats the gate" - TRUE, already disclosed; no claim of a quality gain remains

**Check.** Under client input the template alone reaches 118/175 = 67.4 %, the gated system 97/175 = 55.4 %; with explicit
fields 167/175 = 95.4 % vs 132/175 = 75.4 % (`scored.csv`). Paired: the pipeline wins 1 / loses 22 (client) and wins 0 /
loses 35 (explicit). The gaps are -12.0 pp (CI -17.9 to -6.4) and -20.0 pp (-26.4 to -14.0), recomputed by point 4's script.

**Why it happens.** The scorer is lexical: success = every selected label present + negator + act marker + nothing extra.
A template echoes the labels, so it is near the ceiling of this scorer by construction. The measure cannot see which
sentence is more natural, in either direction: for Hindi *Love* (explicit fields) the accepted model sentence is the awkward
"मैं प्यार हूँ, मैं कह रहा हूँ।" while the template is "मुझे प्यार महसूस हो रहा है।"; elsewhere the model may be the more natural one.
Only human ratings can say how often each happens.

**What v4 says.** The abstract already says "the gate is a safeguard, not a quality gain"; v4 keeps this, keeps the template
paragraph, and adds that the comparison "cannot measure what model phrasing adds; a blind native-speaker rating of the
116 accepted model sentences that differ from their templates can, and is prepared but not run". The contribution list
claims the gate as a design (ledger, gate, fallback), not as a quality gain.

**Experiment prepared (needs native raters, cannot be done by the AI).** `qa_scripts/make_ab_rating_sheets.py` ->
`qa_scripts/ab_rating/{en,hi,gu,mr}_sheet.csv` (20 / 42 / 31 / 23 blind pairs, random A/B side) and `KEY_do_not_share.csv`.
Per sentence: meaning correct (yes/no), naturalness (1-5); per pair: preference. Fixed analysis plan in the script header:
paired model-minus-template difference, bootstrap over the 46 scenario groups, two raters per language, agreement reported.
Effort: about 30-45 minutes per rater per language. Only this result can turn "safeguard" into "quality gain" (or not).

## 2. Repaired-build holdout results - CORRECTLY LEFT OUT; stays out

**Check.** `udpated_version_context_of_papers/v2/FINAL_CONTEXT.md` section 7 marks the 120-scenario holdout as DRAFT labels
and "PRELIMINARY: keep out of the paper until the gold annotation is native-checked". The v3 paper prints no holdout score
(Section 5: "awaits native-speaker confirmation ... no score on it is reported"); the 175/175 regression result is labelled
"a regression target and not a test result". Nothing to retract.

**v4 change.** Section 5 now states the requirement exactly: "confirmation of its gold annotation by two native speakers
per language". **Author action:** two native speakers per language fill `v2/fixtures/holdout/native_gold_check_<lang>.csv`;
only then rescore with the frozen repaired build (`v2/run_all.sh`) and report it as a test result.

## 3. Placeholder tone vs MOS claim - REAL INCONSISTENCY between builds; fixed in abstract, Limitations, Conclusion and appendix together

**Check.** No version in the repository has a "contribution 5" or a MOS claim in the contributions (v3 final has three
contributions; the ChatGPT v3 has three bullet points), so the conflicting sentence is in a draft outside the repo. The
underlying conflict is real: v3 Limitations says "Speech was a placeholder tone" (true for the evaluated build), while the
MOS portal rates speech of the **current** build. Both are true about different builds.

**New evidence (aggregate only, no personal data):** `qa_scripts/mos_pilot_summary.py` reads the portal database read-only
(snapshot 2026-11-23 07:05 UTC): 15 registered, **8 completed** all 20 clips, 0 excluded. MOS (95 % CI, bootstrap over
listeners): English 4.35 (3.75-4.85), Hindi 3.73 (3.10-4.40), Gujarati 4.15 (3.48-4.72), Marathi 4.15 (3.52-4.67).
Native listeners only: Gujarati 4.19 (6 listeners), Hindi 3.92 (3), Marathi 1 listener, English 0.
Listeners rated all four languages, so most Marathi and English ratings are from non-native listeners.

**v4 change (all places at once).**
- Abstract: "The evaluated build produced no speech (a placeholder tone); ... eight listeners rated its [current build's] speech 3.7-4.4 (of 5) in a pilot that is not language-matched."
- Section 3: evaluated-build paragraph keeps the placeholder-tone statement; new "Current build" paragraph says speech uses real IndicF5 weights (F5-TTS for English).
- Limitations: "In the evaluated build speech was a placeholder tone ...; current-build speech has only a pilot listening test that is not language-matched."
- Conclusion: "a pilot rates its speech 3.7-4.4"; next step "a language-matched listening test".
- Appendix: method, numbers, native-only numbers, and the caveat; Table 8 caption points to it.

**Recommendation.** If you want MOS in the abstract as a result (not a pilot), first get >= 5 native listeners per language
(currently 6 / 3 / 1 / 0 for gu / hi / mr / en). Otherwise keep it as the pilot wording above, or delete the abstract clause
(the appendix text can stay).

## 4. Bootstrap script missing - IT EXISTED but was not in the paper package; now added and verified

**Check.** The intervals were produced by `udpated_version_context_of_papers/v2/src/audit_archived.py` (block A7, writes
`v2/results/audit/A7_paired_ci_recomputed.json`), and `qa_scripts/extra_checks.py` gives the +10.1 pp Indic-only interval.
Neither was named in Section 4.

**Done.** `qa_scripts/paired_group_bootstrap.py` (needs only numpy and the frozen `scored.csv`) recomputes all five
intervals printed in Section 4 and checks them against the paper:

| comparison | recomputed | printed | |
|---|---|---|---|
| gate + fallback vs ungated, client input | 18.29 [11.86, 25.15] | 18.3 (11.9-25.2) | OK |
| gate + fallback vs ungated, explicit fields | 34.86 [26.70, 43.41] | 34.9 (26.7-43.4) | OK |
| explicit fields vs client input | 20.00 [12.00, 28.65] | 20.0 (12.0-28.7) | OK |
| template vs deployed, explicit fields | 20.00 [13.95, 26.40] | 20.0 (14.0-26.4) | OK |
| template vs deployed, client input | 12.00 [6.40, 17.94] | 12.0 (6.4-17.9) | OK |

Method, now named in Section 4: paired success difference; resampling unit = the 46 scenario groups (four language versions
of one selection together); 10,000 resamples; seed 20261113; percentile interval of the pooled ratio (summed differences /
scenarios drawn). Section 4 now cites the script.

## 5. Single runs against our own OPT re-implementation - TRUE; re-run with intervals, seeds and repeated timing

**Check.** `RESULTS_vs_baseline.txt` (19 Nov) used 40 + 40 test sentences, one run, one adaptation seed, no interval, and
timing from one pass on a shared GPU (and the timing was of the character search, not of word prediction). The baseline's
own models and test sets are not public, so a re-implementation is the only option; the re-implementation was checked only
on one example from the baseline paper ("yeste" -> r: 0.994 vs the paper's 0.9999).

**Experiment run (`exp_step17_baseline_ci.py`, results in `results/step17_baseline_ci.json/.log`):**
- full English test sets (403 + 402 sentences), same simulator as all other KSR numbers, the SAME candidate pool for every system;
- OPT-125m and OPT-350m pretrained; OPT-125m adapted with 3 seeds (mean and range);
- ours: evaluated build's trie, predictor_v2 (CPU), predictor_v2 + adapted BLOOM-560m re-ranker (GPU);
- paired bootstrap 95 % CIs (over sentences) of ours against every row;
- speed: 5 repeated runs of 200 fresh queries per system, median and range of the run medians.

RESULTS: see the table below (filled from the JSON when the run finished).

STEP17_RESULTS_PLACEHOLDER

What stays a limitation (and is now written in Limitations): single training run for our adapters (5-fold CV exists for
the LoRA system from Step 9 in `20_nov_changes.md`), synthetic / machine-translated text, re-implemented baseline.

## 6. Nov 16 UI redesign and Nov 20 LoRA experiments not in the paper - ADDED (System Design + Results + appendix)

- Section 3, new paragraph "Current build": the 16 Nov redesign (draft canvas separate from intended message; explicit
  Speak / Stop / Make sentence; checked-template previews for 1,872 selections, offline too), the per-language predictor,
  the BLOOM-560m + LoRA re-ranker, personal vocabulary + phrase row, Fitzgerald-key colours, 44 px targets, switch
  scanning and dwell, real IndicF5 speech. Contribution (ii) in the Introduction updated.
- Section 4, new Table `tab:ksr` (keystroke savings, four languages, evaluated vs current build, CPU / GPU, new user /
  personal) replaces the old hit@1 table in the main text (moved to the appendix).
- **The +7 target is reported as missed**: the re-ranker gained +6.5 (en), +4.0 (hi), +5.8 (mr), +4.6 (gu) KSR over the
  evaluated trie (5 suggestions, `step5_<lang>.json`), all below the +7 target set in `IMPROVEMENT_PLAN_INDEPTH.txt` (W2).
- Appendix Table `tab:models`: three new rows (current predictor, BLOOM + LoRA with its hyper-parameters and licence
  BigScience RAIL 1.0, personal model). New appendix Table `tab:baseline` (point 5).
- Also measured for the paper (`exp_step17_evaluated_build.py`): the evaluated build's own prediction (shelf ignored typed
  letters; Marathi used the Hindi trie; Gujarati had none) saves en 24.0, hi 33.2, mr 0.2, gu 0.0 % keystrokes, vs the
  current build 64.3 / 64.3 / 57.2 / 60.4.
- Correction found while doing this: the "old app 5-10 %" numbers in `20_nov_changes.md` Step 16 are the **16-22 November**
  build (broken merge rule), not the evaluated build; the paper uses the evaluated-build numbers above.

New citations (verify like the v3 ones, `citation_records/`): gaines2025adapting (from the paper's own header), bigscience2022bloom, hu2022lora, zhang2022opt.

---

## Page budget (check on Overleaf)
v3 had about 2.8 spare lines on page 6 and 2.7 in the appendix. v4 adds about 220 words to the main text and moves the old
prediction table (Table 3) to the appendix, while the new KSR table is smaller. Expected: main text 0-8 lines over;
appendix over by up to half a page. If over, cut in this order:
1. Section 4, first sentence of "Next-word prediction" (the evaluated-build hit@1 sentence; the table is in the appendix).
2. Section 3, the clause about 44 px targets and Fitzgerald colours (keep scanning and dwell).
3. Appendix: drop `tab:pred` (old hit@1) or `tab:mos` (predicted scores), keeping the text sentences.

## What only the authors can do
- Native raters for point 1 (A/B sheets) and point 2 (holdout gold check, two per language).
- More native listeners for the MOS pilot (point 3), at least 5 per language.
- A user study with AAC users (no number here measures communication effectiveness).
- Licences for public release (F5-TTS weights CC-BY-NC-4.0, IndicF5 gated, BLOOM RAIL).
