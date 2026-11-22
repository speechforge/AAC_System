# 20 Nov 2026 - change log (running document)

Single log for all work of 2026-11-20. Updated after every step. `Results_10/` (frozen 2026-11-20 snapshot of the earlier results) is **not modified**; everything new goes to `our_experiments_vs_baseline/` and the files named below.
Arrows: KSR ↑ higher is better, top-k hit ↑, perplexity ↓ lower is better, latency ↓.
The shipped app code (`indic-generative-aac/backend/*`) has **not** been changed.

## Index of new files
| File | What |
|---|---|
| `STEP1_DIAGNOSIS.txt` | Step 1 diagnosis report (coverage, oracle ceilings, MT audit) |
| `our_experiments_vs_baseline/exp_step1_diagnose.py` | Step 1 code (cpu / gpu modes) |
| `our_experiments_vs_baseline/results/step1_diagnose_{cpu,gpu}.json` | Step 1 raw results |
| `our_experiments_vs_baseline/exp_fertility.py`, `results/step2_fertility.json` | Step 2a tokenizer fertility |
| `our_experiments_vs_baseline/exp_step2.py`, `results/step2_<lang>.json/.log` | Step 2 LoRA-adapted BLOOM-560m experiments |

## Step 1 - Diagnose the bottleneck (DONE)
Question: why are Marathi/Gujarati weaker, and is ranking or data the limit?
- Perfect-ranker headroom over our candidate pool (KSR points): English 14.3, Hindi 12.3, **Marathi 14.3, Gujarati 12.1** -> ranking quality is the main lever.
- Marathi's ceiling is lower (oracle 63.7 vs Hindi 70.3) because of coverage: test OOV 14.2%/9.7% (AAC/care), type/token 0.19, 58% hapax. OOV is still falling with more data (22.9 -> 16.7 -> 11.7% at 25/50/100% train) -> data-bound.
- ~36-41% of OOV tokens are inflections of known words.
- MT audit (NLLB round trip chrF ↑, median): Marathi 20.6, Gujarati 27.4, Hindi 40.2 (calibration); ~10% of mr/gu sentences were repetition loops (already filtered). First audit run was contaminated by back-translation loops; rerun with loop suppression is the one reported.
- Decision: proceed to Step 2 (headroom > 10 points, so the "stop ranking work" rule did not trigger).

## Step 2 - Adapt a multilingual neural LM on the GPU (DONE for Marathi and Gujarati; Hindi and English in Step 7)
### 2a Base-model choice by measured tokenizer fertility (tokens per word, ↓ lower is better)
| Model | en | hi | mr | gu |
|---|---|---|---|---|
| OPT-125m | 1.11 | 6.61 | 9.07 | 13.26 |
| Qwen2.5-0.5B (our cascade LM) | 1.09 | 4.03 | 5.46 | 7.36 |
| **BLOOM-560m** | 1.11 | **1.14** | **1.45** | **1.37** |
| XGLM-564M | 1.12 | 1.26 | 1.67 | 1.72 |
| mT5-small | 1.40 | 1.82 | 2.30 | 2.36 |
| ByT5-small (bytes) | 5.23 | 11.21 | 15.33 | 13.26 |
-> BLOOM-560m chosen (also pretrained on Marathi and Gujarati). OPT/Qwen waste 5-13 tokens per Indic word.
### 2b Method
LoRA (r=16, alpha=32, all attention + MLP linears, 6.3M trainable params, base frozen fp16), up to 3 epochs, best epoch by dev character-perplexity; ranker = LM log-prob of the candidate word given the context; hybrid weight tuned on 60 dev sentences; KSR on a random 100+100 test-sentence subsample (same for all systems); character-perplexity on the **full** test set. Paired bootstrap 95% CIs vs shipped.
### 2c Results
#### Marathi (done; 100+100 test sentences, KSR ↑ / top-5 ↑ avg of AAC+care; gain CI = paired bootstrap 95%, percentage points vs shipped)
| System | KSR ↑ | top-5 ↑ | gain vs shipped (AAC / care CI) |
|---|---|---|---|
| A shipped ∞-gram | 48.82 | 30.3 | - |
| E improved CPU stack (Results_10 stack, no personalisation) | 49.43 | 31.1 | [-0.77, 0.56] / [0.63, 2.10] |
| BLOOM-560m pretrained, zero-shot | 41.37 | 15.6 | [-9.45, -5.91] / [-9.65, -5.41] (worse) |
| **BLOOM-560m adapted (LoRA)** | **51.33** | **35.2** | [0.76, 3.07] / [1.94, 4.10] |
| **G = CPU stack + adapted BLOOM (weight 0.1 on CPU stack, tuned on dev)** | **51.78** | **35.6** | [1.26, 3.43] / [2.48, 4.59] |

Character-level perplexity ↓ on the **full** Marathi test set: char 12-gram 5.47 | BLOOM pretrained 10.45 | **BLOOM adapted 2.91** (dev by epoch 3.24 -> 3.08 -> 3.03, best = epoch 3).
Reading: zero-shot BLOOM is worse than our CPU stack, so adaptation on our domain is what makes it work (pretrained KSR 41.4 -> adapted 51.3). Adapted BLOOM beats shipped by +2.5 KSR (+3.0 for the hybrid) and +5 top-5 points, CIs above 0 on both sets. It only reaches ~1/4 of the 14-point ranking headroom found in Step 1. Caveats: 200 test sentences, MT data, one split. Cost: ~28 min for 200 sentences on the shared GPU (not a latency number).

#### Gujarati (done; same protocol)
| System | KSR ↑ | top-5 ↑ | gain vs shipped (AAC / care CI) |
|---|---|---|---|
| A shipped ∞-gram | 54.11 | 40.9 | - |
| E improved CPU stack | 55.21 | 43.6 | [-0.11, 1.51] / [0.90, 2.23] |
| BLOOM-560m pretrained, zero-shot | 46.25 | 26.0 | [-10.04, -6.50] / [-9.19, -5.88] (worse) |
| **BLOOM-560m adapted (LoRA)** | **57.21** | **48.1** | [1.70, 4.09] / [2.27, 4.45] |
| **G = CPU stack + adapted BLOOM (weight 0.1)** | **57.45** | **48.6** | [2.00, 4.17] / [2.68, 4.56] |

Character-level perplexity ↓ (full Gujarati test set): char 12-gram 4.99 | BLOOM pretrained 13.85 | **BLOOM adapted 2.95** (dev 3.27 -> 3.11 -> 3.06, best = epoch 3).

### 2d Step 2 verdict
- **Improved in both languages, with CIs above 0 on both test sets.** Marathi KSR 48.8 -> 51.8 (+3.0), top-5 30.3 -> 35.6 (+5.3). Gujarati KSR 54.1 -> 57.5 (+3.3), top-5 40.9 -> 48.6 (+7.7). Against the *improved CPU stack* the gain is about +2.3 (mr) / +2.2 (gu) KSR.
- **Perplexity ↓ roughly halved**: Marathi 5.47 -> 2.91, Gujarati 4.99 -> 2.95 (character-level, full test sets, vs char 12-gram). Same units for all rows; EOS not scored.
- **Adaptation is essential**: zero-shot BLOOM is 6-10 KSR points *worse* than the shipped CPU engine; the in-domain LoRA step is what makes it win (needs only ~2 min of training).
- **Hybrid adds little**: tuned weight on the CPU stack = 0.1; hybrid - adapted LM = +0.45 (mr), +0.24 (gu), inside noise. The LM does the work.
- **Pre-registered target (neural path +7 KSR, Part 6 of IMPROVEMENT_PLAN_INDEPTH.txt) NOT met**: gains are +3.0/+3.3. Only ~1/4 of the Step 1 ranking headroom (12-14 points) was closed. Honest reading: a real, significant improvement, but well short of the ceiling.
- **Cost**: GPU only. Scoring 200 sentences took ~28 min per LM system on the shared GPU (candidate scoring of up to 300 words per query is the bottleneck, not a user-latency number). A per-query latency measurement on an idle GPU and a distilled/CPU variant (Step 7 of the plan) are still needed before this can be offered in the app.
- **Caveats**: 100+100 test sentences, single split, one seed, machine-translated data (indicative); LoRA hyper-parameters not tuned beyond epoch count; hybrid weight tuned on only 60 dev sentences.
- Not run: Hindi and English re-run with BLOOM; Qwen2.5 adapted as a tokenizer-fertility control (hypothesis that fertility matters is supported only by the pretrained/adapted contrast and the fertility table, not by a controlled ablation).

## Step 3 - Speed: CPU stack pre-filters, adapted LM re-scores only the top-K (DONE for Marathi and Gujarati)
Why (plan item "speed" from the Step 2 next-steps): scoring all ~300 pool words per query cost ~28 min per 200 sentences. Method: the improved CPU stack ranks the pool; only its top-K go through the LoRA-adapted BLOOM; final score = w*CPU + (1-w)*LM, both renormalised over the K (other words cannot be suggested). K in {20, 50} and w in {0.1, 0.3, 0.5} chosen on 150 dev sentences. **FULL test sets** this time (not a 100+100 subsample). Code: `our_experiments_vs_baseline/exp_step3.py`, `run_step3.sh`; adapter saved to `results/lora_<lang>.pt`.
Dev grid (Marathi, KSR ↑ on 150 dev sentences): K=20: 47.8-47.9 | K=50: 48.3-48.6 (best K=50, w_cpu=0.1). Larger K is slightly better, so the pre-filter is not free but small.
#### Marathi, full test (351 AAC + 394 caregiver sentences)
| System | KSR ↑ | top-1 ↑ | top-5 ↑ | gain CI vs shipped (AAC / care) |
|---|---|---|---|---|
| A shipped ∞-gram | 48.73 | 16.3 | 28.9 | - |
| E improved CPU stack | 49.38 | 17.0 | 30.0 | [-0.02, 0.74] / [0.56, 1.39] |
| **H top-50 prefilter + adapted BLOOM** | **51.94** | **20.5** | **34.8** | [2.54, 3.74] / [2.77, 3.81] |
- H vs E (the CPU stack alone): CI [2.16, 3.40] / [1.77, 2.92] - the LM adds a real +2.5 over the best CPU system.
- Wall time for the whole full test set 1303 s (vs ~4100 s for 200 sentences in Step 2): about 10x cheaper per sentence.
- LM-call latency (uncached, 50 candidates, shared busy GPU): p50 174 ms, p95 288 ms (n=8325). **Too slow for per-keystroke use as is** (target p95 < 50 ms); needs KV-cache of the context, smaller K, and an idle GPU measurement.

#### Gujarati, full test (346 AAC + 387 caregiver sentences; K=50, w_cpu=0.1)
| System | KSR ↑ | top-1 ↑ | top-5 ↑ | gain CI vs shipped (AAC / care) |
|---|---|---|---|---|
| A shipped ∞-gram | 53.04 | 23.6 | 39.1 | - |
| E improved CPU stack | 54.25 | 25.3 | 41.9 | [0.82, 1.61] / [0.89, 1.51] |
| **H top-50 prefilter + adapted BLOOM** | **56.25** | **28.7** | **46.4** | [2.9, 4.07] / [2.55, 3.33] |
- H vs E: CI [1.81, 2.72] / [1.41, 2.07]. Wall time 2161 s for the whole run. LM-call latency (uncached, 50 candidates, busy shared GPU): p50 188 ms, p95 306 ms.
- **Step 3 verdict**: pre-filtering to the CPU stack's top-50 keeps the whole language-model gain (full-test Marathi +3.2, Gujarati +3.2 KSR over shipped; top-5 +6 / +7 points) at roughly 10x lower cost than scoring all 300 candidates, so FULL-test evaluation is now feasible. Latency is still far above the 50 ms per-keystroke target on this shared GPU (see Step 7 for the one-batch benchmark).


## Step 4 - CPU-only ideas on top of E (DONE, all 4 languages, FULL test sets)
Code `exp_step4.py`, results `results/step4_<lang>.json`. E = improved CPU stack (no personalisation). Two ideas + a learning curve, all knobs picked on dev:
- **ES expected-savings re-ranking** (score = p x (remaining chars+1)^gamma, gamma in {0,.5,1,1.5,2}). **Result: dev picked gamma = 0 in every language, i.e. no gain - hypothesis refuted** (a pre-registered idea from IMPROVEMENT_PLAN_INDEPTH W2-a; reported as a negative result).
- **COV vocabulary-coverage fallback**: besides the 300-word pool, add the 5 most probable char-12-gram completions (beam search, prefix >= 2 chars) that are not in the training vocabulary. Targets the OOV ceiling found in Step 1.

| Language | A shipped KSR ↑ | E KSR ↑ | **E+COV KSR ↑** | COV gain vs E, 95% CI AAC / care (pp) | top-5 (unchanged) |
|---|---|---|---|---|---|
| English | 56.29 | 56.52 | **57.49** | [0.91, 1.48] / [0.59, 1.0] | 34.3 |
| Hindi | 56.74 | 57.80 | **58.28** | [0.43, 0.77] / [0.25, 0.49] | 48.1 |
| Marathi | 48.73 | 49.38 | **51.86** | [2.42, 3.41] / [1.65, 2.42] | 30.0 |
| Gujarati | 53.04 | 54.25 | **55.60** | [1.4, 2.09] / [0.75, 1.22] | 41.9 |

Reading: COV is a **CPU-only** gain that is largest exactly where Step 1 found the biggest OOV problem: Marathi +2.5 KSR over E (+3.1 over shipped, about as much as the GPU language model), Gujarati +1.35, English +1.0, Hindi +0.5. CIs exclude 0 in all languages. Top-5 at an empty prefix does not change (completions need >= 2 typed characters). Cost: a beam search per new prefix (cached); latency not yet measured.

### Learning curve (KSR ↑ on the full test sets; A shipped / E improved, trained on a fraction of the train split)
| Language | 25% | 50% | 75% | 100% |
|---|---|---|---|---|
| English | 47.1 / 46.8 | 51.9 / 51.6 | 54.8 / 54.8 | 56.3 / 56.5 |
| Hindi | 48.0 / 48.6 | 53.0 / 53.8 | 55.5 / 56.5 | 56.7 / 57.8 |
| Marathi | 39.9 / 40.8 | 43.9 / 44.7 | 47.1 / 47.9 | 48.7 / 49.4 |
| Gujarati | 45.8 / 46.6 | 49.6 / 50.6 | 51.9 / 53.0 | 53.0 / 54.2 |

Reading: KSR is **still rising at 100% of the data in all four languages** (Marathi +4.7 from 50% to 100%), confirming the Step 1 conclusion that we are data-bound: collecting more (native) text is likely worth more than further model tuning. The learning-curve gap E - A is small and stable, so Step 1's fix is not data-dependent.


## Step 5 - 5-fold block cross-validation of the CPU improvements (DONE; plan Step 9 / rule R3)
Code `exp_cv.py`, results `results/cv_<lang>.json`. Train+dev+test sentences pooled in original order; 5 contiguous blocks used as test folds (conversation ids are not stored, so leakage is only possible at block borders). Hyper-parameters were tuned once on the original dev split and **not** re-tuned per fold. KSR ↑, mean ± SD over folds; gain = per-fold paired difference vs shipped.

| Language | A shipped | E improved | E+COV | E - A (mean ± SD, folds > 0) | E+COV - A (mean ± SD, folds > 0) |
|---|---|---|---|---|---|
| English | 56.53 ± 2.25 | 56.54 ± 2.25 | 57.43 ± 2.04 | +0.01 ± 0.07 (3/5) | +0.90 ± 0.24 (5/5) |
| Hindi | 54.89 ± 2.42 | 56.13 ± 2.26 | 56.63 ± 2.17 | +1.24 ± 0.26 (5/5) | +1.74 ± 0.32 (5/5) |
| Marathi | 49.20 ± 1.63 | 49.98 ± 1.59 | 52.44 ± 1.32 | +0.78 ± 0.07 (5/5) | +3.24 ± 0.36 (5/5) |
| Gujarati | 53.46 ± 1.83 | 54.50 ± 1.76 | 55.74 ± 1.48 | +1.04 ± 0.15 (5/5) | +2.28 ± 0.37 (5/5) |

Reading (corrects earlier single-split numbers):
- **COV is robust**: E+COV beats shipped in all 5 folds in every language (+0.9 en, +1.7 hi, +3.2 mr, +2.3 gu). This is the most reliable CPU-only improvement we have.
- **E (drop selected-word exclusion + cap + char hybrid) is solid for Hindi/Marathi/Gujarati (+0.8 to +1.2, 5/5 folds) but NOT for English**: +0.01 ± 0.07, only 3/5 folds positive. The +0.3-0.5 English gain seen on the single original split (Results_10, Step 1) does not replicate. English CPU gains should be attributed to COV, not to E.
- Between-fold SD of absolute KSR is 1.3-2.4 points, so differences smaller than that between *systems evaluated on different splits* mean little; paired within-fold differences (SD 0.07-0.4) are the reliable quantity.


## Step 6 - Learned re-ranker over CPU features (DONE, all 4 languages, FULL test sets)
Code `exp_step6.py`, results `results/step6_<lang>.json`. Pointwise logistic regression (9 features: log CPU/∞-gram/char-12 probability, log frequency, remaining chars, prefix length, OOV flag, CPU rank, word-already-in-sentence) trained on **dev** queries only, C chosen by held-out log-loss, applied to the CPU stack's top-30 of the E+COV candidate set. KSR ↑.

| Language | A shipped | E+COV | **L (E+COV + learned)** | L - E+COV, 95% CI AAC / care (pp) | learned weights (largest) |
|---|---|---|---|---|---|
| English | 56.29 | 57.49 | **57.69** | [0.06, 0.31] / [0.09, 0.34] | log_char +1.07, log_rank -0.72, prefix_len +0.61 |
| Hindi | 56.74 | 58.28 | **58.51** | [0.03, 0.32] / [0.16, 0.43] | log_char +1.19, log_rank -0.84, log_cpu +0.78 |
| Marathi | 48.73 | 51.86 | **52.13** | [0.23, 0.64] / [-0.14, 0.34] | log_char +1.03, log_rank -0.65, prefix_len +0.61 |
| Gujarati | 53.04 | 55.60 | **55.75** | [0.13, 0.45] / [-0.13, 0.17] | log_char +1.58, log_rank -0.71, log_cpu +0.65 |

Reading: the learned ranker adds only about +0.15 to +0.3 KSR on top of E+COV (CIs listed above; where a CI includes 0 the gain is not established). It is cheap (CPU) but not a large lever - the CPU features carry nearly all the signal, which matches Step 3: real new information (a language model) is needed for big gains. Caveat: trained on only ~335 dev sentences per language.


## Step 7 - Combine coverage fallback + adapted LM (DONE, all 4 languages)
Code `exp_step5.py` (file name differs from the step number in this log), `run_step5.sh`, results `results/step5_<lang>.json`. System **I** = candidates from the pool **plus** 5 char-LM completions (COV), ranked by the CPU stack, top-50 re-scored by the LoRA-adapted BLOOM-560m (w_cpu tuned on 150 dev sentences). FULL test sets. A single batch of K candidates per query; latency measured with fresh contexts and CUDA sync on the shared (busy) GPU.
#### Marathi (351 AAC + 394 caregiver)
| System | KSR ↑ | top-5 ↑ | gain CI vs shipped (AAC / care, pp) |
|---|---|---|---|
| A shipped ∞-gram | 48.73 | 28.9 | - |
| E improved CPU stack | 49.38 | 30.0 | [-0.02, 0.74] / [0.56, 1.39] |
| E+COV (CPU only) | 51.86 | 30.0 | [2.64, 3.88] / [2.44, 3.62] |
| **I = E+COV + adapted BLOOM (top-50)** | **54.53** | **34.8** | **[5.30, 7.02] / [4.81, 6.25]** |
- **COV and the LM are complementary** (I - E+COV: CI [2.19, 3.50] / [1.89, 3.11]): +5.8 KSR over shipped in Marathi (48.7 -> 54.5), the largest gain so far and well past the +3 of either idea alone. Top-5 +5.9 points.
- LM latency, one batch of K candidates, uncached, busy shared GPU: **K=10 p50 48 ms / p95 65 ms; K=20 p50 77 / p95 115 ms; K=50 p50 175 / p95 257 ms.** Cost grows about linearly in K (GPU compute-bound while another job uses it at 100%). Only K=10 approaches the 50 ms per-keystroke target; its KSR effect has not been measured yet (K=20/50 only were tuned) - see "Next".
#### Gujarati (346 AAC + 387 caregiver)
| System | KSR ↑ | top-5 ↑ | gain CI vs shipped (AAC / care, pp) |
|---|---|---|---|
| A shipped ∞-gram | 53.04 | 39.1 | - |
| E improved CPU stack | 54.25 | 41.9 | [0.82, 1.61] / [0.89, 1.51] |
| E+COV (CPU only) | 55.60 | 41.9 | [2.43, 3.50] / [1.77, 2.57] |
| **I = E+COV + adapted BLOOM (top-50)** | **57.59** | **46.4** | **[4.49, 5.88] / [3.45, 4.47]** |
- I - E+COV CI [1.75, 2.70] / [1.43, 2.12]. Gujarati KSR 53.0 -> 57.6 (+4.5), top-5 +7.3 points. Latency (busy GPU, one batch, uncached): K=10 p50 42 / p95 64 ms; K=20 p50 72 / p95 136 ms; K=50 p50 162 / p95 278 ms.
#### Hindi (507 AAC + 520 caregiver; adapter trained here, best epoch 3, dev char-ppl 2.50; full-test char-ppl ↓: char 12-gram 4.38 -> adapted BLOOM 2.48)
| System | KSR ↑ | top-5 ↑ | gain CI vs shipped (AAC / care, pp) |
|---|---|---|---|
| A shipped ∞-gram | 56.74 | 45.5 | - |
| E improved CPU stack | 57.80 | 48.1 | [0.63, 1.28] / [0.86, 1.49] |
| E+COV (CPU only) | 58.28 | 48.1 | [1.20, 1.91] / [1.19, 1.87] |
| **I = E+COV + adapted BLOOM (top-50)** | **60.72** | **51.8** | **[3.75, 4.70] / [3.30, 4.13]** |
- I - E+COV CI [2.28, 3.10] / [1.85, 2.56]. Hindi KSR 56.7 -> 60.7 (+4.0), top-5 +6.3 points. Latency (busy GPU): K=10 p50 43 / p95 54 ms; K=20 73 / 114 ms; K=50 153 / 263 ms.
#### English (403 AAC + 402 caregiver; adapter trained here, best epoch 2, dev char-ppl 2.23; full-test char-ppl ↓: char 12-gram 4.70 -> adapted BLOOM 2.13)
| System | KSR ↑ | top-5 ↑ | gain CI vs shipped (AAC / care, pp) |
|---|---|---|---|
| A shipped ∞-gram | 56.29 | 33.4 | - |
| E improved CPU stack | 56.52 | 34.3 | [0.03, 0.57] / [-0.11, 0.40] (not established) |
| E+COV (CPU only) | 57.49 | 34.3 | [1.14, 1.91] / [0.59, 1.26] |
| **I = E+COV + adapted BLOOM (top-50)** | **62.75** | **42.4** | **[6.25, 7.52] / [5.48, 6.60]** |
- I - E+COV CI [4.84, 5.93] / [4.66, 5.55]. English KSR 56.3 -> 62.8 (+6.5), top-5 +9.0 points. This **full-test** result replicates the earlier 100+100-subsample finding with OPT-125m (adapted OPT 61.9-63.0), with a multilingual base model. Latency (busy GPU): K=10 p50 38 / p95 48 ms; K=20 62 / 94 ms; K=50 136 / 218 ms.
- Baseline-paper context (see RESULTS_vs_baseline.txt): the adapted-LM English system is the most accurate of all systems we have evaluated, now with the coverage fallback and full test sets.

## Step 8 - Accuracy vs latency: how many candidates K does the LM need to re-score? (DONE for mr/gu/hi)
Code `exp_step8_k.py`, `run_step8.sh`, results `results/step8_<lang>_K{10,20}.json` (K=50 from Step 7). Same adapter, same weight w_cpu=0.1, full test sets. Latency = one batch of K candidates, uncached, CUDA-synchronised, on the **shared GPU that another job was using at 100%** (so an upper bound, not an idle-GPU figure).

| Language | E+COV (CPU) KSR ↑ | I, K=10 | I, K=20 | I, K=50 | LM latency p50 / p95 ms at K=10 | K=20 | K=50 |
|---|---|---|---|---|---|---|---|
| Marathi (shipped 48.7) | 51.86 | 53.48 | 54.07 | 54.53 | 48 / 65 | 77 / 115 | 175 / 257 |
| Gujarati (shipped 53.0) | 55.60 | 56.82 | 57.37 | 57.59 | 42 / 64 | 72 / 136 | 162 / 278 |
| Hindi (shipped 56.7) | 58.28 | 59.88 | 60.57 | 60.72 | 43 / 54 | 72 / 114 | 153 / 263 |

Reading:
- All K keep a large, CI-significant gain over shipped (K=10: Marathi +4.7, Gujarati +3.8, Hindi +3.1 KSR). Going from K=50 to K=10 costs about 0.7-1.0 KSR but cuts LM latency ~4x (p95 about 50-65 ms on the busy GPU).
- K=20 recovers ~half of that loss (KSR within 0.2-0.5 of K=50) at p95 ~95-135 ms. A sensible setting for a per-keystroke GPU path is K=10-20; K=50 is an accuracy-first mode.
- Not yet established: idle-GPU latency, CPU/int8 latency, and the beam-search cost of the COV fallback. Per-keystroke use is therefore **borderline, not proven**.

## SUMMARY (2026-11-20/21) - current best vs shipped, full test sets, KSR ↑ / top-5 ↑
| Language | Shipped KSR | CPU-only best (E+COV+learned) | **Best overall (I, K=50)** | gain I vs shipped (CI AAC / care, pp) | top-5 shipped -> I | char-ppl ↓ char12 -> adapted LM |
|---|---|---|---|---|---|---|
| English | 56.29 | 57.69 | **62.75** | [6.25, 7.52] / [5.48, 6.6] | 33.4 -> **42.4** | 4.7 -> **2.13** |
| Hindi | 56.74 | 58.51 | **60.72** | [3.75, 4.7] / [3.3, 4.13] | 45.5 -> **51.8** | 4.38 -> **2.48** |
| Marathi | 48.73 | 52.13 | **54.53** | [5.3, 7.02] / [4.81, 6.25] | 28.9 -> **34.8** | 5.47 -> **2.91** |
| Gujarati | 53.04 | 55.75 | **57.59** | [4.49, 5.88] / [3.45, 4.47] | 39.1 -> **46.4** | 4.99 -> **2.95** |

### What worked / what did not (each tied to its evidence)
- **Worked, CPU-only:** vocabulary-coverage fallback (COV): +0.9 to +3.2 KSR, positive in 5/5 CV folds in every language (Step 4-5). Dropping selected-word exclusion + context cap + char hybrid (E): +0.8 to +1.2 in hi/mr/gu (5/5 folds) but **not** in English (+0.01).
- **Worked, GPU:** LoRA-adapted BLOOM-560m re-scoring the top-K: English +6.5, Hindi +4.0, Marathi +5.8, Gujarati +4.5 KSR over shipped (all CIs well above 0); top-5 +6 to +9 points; character perplexity roughly halved (4.4-5.5 -> 2.1-2.9). Adaptation on our domain is essential (zero-shot BLOOM is 6-10 points worse than shipped, Step 2).
- **Did not work:** expected-savings re-ranking (dev chose gamma=0 everywhere); the learned re-ranker adds only +0.15-0.3 on CPU features; hybrid weight on the CPU stack stays at the smallest tuned value (0.1), i.e. the LM dominates.
- **Diagnosis still true:** KSR still rises with more training data in every language (Step 4 learning curve); machine-translated Marathi/Gujarati data are the weakest part of the evidence.

### Pre-registered targets (IMPROVEMENT_PLAN_INDEPTH.txt Part 6) - status
| Target | Status |
|---|---|
| CPU path KSR >= +2.0 over shipped in each language, CI > 0 | **Partly met**: E+COV vs shipped = en +1.2, hi +1.5, mr +3.1, gu +2.6 (CV mean: +0.9, +1.7, +3.2, +2.3). Met for Marathi and Gujarati, missed for English and Hindi |
| Neural path English full-test KSR >= 61 | **Met**: 62.75 (full test, CI vs shipped [6.25, 7.52] / [5.48, 6.60]) |
| Neural path Indic gain >= +7 | **Not met**: +4.0 to +5.8 |
| Top-5 English >= 38% (CPU) / >= 47% (neural) | **Not met**: 34.3% (CPU) / 42.4% (neural) |
| Perplexity: neural <= 0.8x char 12-gram | **Met** (ratio 0.45-0.53, character level, full test sets; caveat: EOS not scored, units shared by both rows) |
| Latency: CPU p95 < 5 ms; neural p95 < 50 ms | **Neural K=10 borderline** (p95 48-65 ms on a busy GPU); CPU incl. COV beam search **not measured** |
| 5-fold CV with paired CIs | **Done for the CPU systems** (Step 5); not done for the LM path (3 folds planned) |

### NOT done (cannot be done by me alone, or out of scope without your decision)
- Native Marathi/Gujarati text and native test sets; native-speaker rating of the MT data (needs people/data).
- Human studies: user/caregiver trial, TTS MOS listening study (portal reworded, not run), generation-fidelity rating by humans.
- Live Qwen2.5 cascade evaluation, knowledge distillation / int8 CPU variant of the LM, idle-GPU latency, CV for the LM path, Qwen-adapted fertility control.
- **Shipped app code `indic-generative-aac/backend/*` is still UNCHANGED.** Integrating COV (CPU) and, optionally, the adapted-LM path is the natural next engineering step; I did not do it without your go-ahead because it changes the production system.

### Where everything is
- Results/code: `our_experiments_vs_baseline/` (`exp_step1_diagnose.py`, `exp_fertility.py`, `exp_step2.py`, `exp_step3.py`, `exp_step4.py`, `exp_cv.py`, `exp_step6.py`, `exp_step5.py`, `exp_step8_k.py`, run scripts, `results/`); LoRA adapters `results/lora_{en,hi,mr,gu}.pt`.
- Frozen earlier baseline: `Results_10/` (unchanged).  Reports: `STEP1_DIAGNOSIS.txt`, `IMPROVEMENT_PLAN*.txt`, this file.

## STATUS OF THE 9-STEP PLAN (`IMPROVEMENT_PLAN.txt` numbering; appended 2026-11-21)
The log's "Step 1-8" headings above are experiment rounds, NOT the plan's 9 steps. Mapping:

| Plan step | Status | Evidence / note |
|---|---|---|
| 1 Remove selected-word exclusion | DONE as experiment (part of "E"); **not in the app** | +0.3..+1.0 KSR on the single split. In 5-fold CV it does not replicate for English (+0.01); holds for hi/mr/gu (+0.8..+1.2) |
| 2 Hybrid ∞-gram + char 12-gram (CPU) | DONE as experiment (part of "E"); **not in the app** | Small (+0.0..+0.5), inside noise in most languages |
| 3 Adapted LM re-ranker | DONE for all 4 languages (BLOOM-560m + LoRA, top-K re-score) | Log Steps 2, 3, 7, 8. Best system "I": KSR en 62.75, hi 60.72, mr 54.53, gu 57.59. **Not in the app** |
| 4 Per-language ∞-gram engines in the app (mr, gu) | **NOT DONE** | Experiments use per-language models, but `backend/` is unchanged |
| 5 Context cap 2-3 words, unlimited as back-off | DONE as experiment (part of "E") | Evidence in `RESULTS_vs_baseline.txt` Sec. 5; **not in the app** |
| 6a Native Marathi/Gujarati test sets | **NOT DONE** (needs native speakers) | mr/gu numbers are still on machine-translated data |
| 6b More public corpora for the LM | **NOT DONE** | Only a learning curve was run (Step 4) as a proxy for "more data helps" |
| 6c Larger symbol board (>69 concepts) | **NOT DONE** | |
| 7 Personalisation | DONE earlier (Execution Round 2, `IMPROVEMENT_PLAN.txt`): +0.2 en, +0.15 hi, 0 for mr/gu | Not re-run on the new best system "I" |
| 8a Live generation cascade (144 + 10-case suites) | **NOT DONE** | Needs the live Qwen backend |
| 8b Free-form / noisy-typing variants | **NOT DONE** | |
| 8c TTS naturalness (MOS portal) | **NOT DONE** (needs human raters) | Portal wording was updated earlier |
| 8d User study | **NOT DONE** (needs participants) | |
| 9 Statistical rigour (CIs, 5 splits) | **PARTLY DONE** | Paired-bootstrap 95% CIs on every headline number; 5-fold block CV for the CPU systems (Step 5). The adapted-LM system "I" has no CV |

Summary: the prediction-quality steps (1, 2, 3, 5, 7, and 9 for CPU) are done and measured. The steps that change the shipped app (4) or need people, native data or the live backend (6, 8) are not done. Nothing has been integrated into `indic-generative-aac/backend/`.

## COMPARISON TABLE - Results_10 (frozen) vs current system, all improved parameters (appended 2026-11-21)
Generated by `our_experiments_vs_baseline/make_comparison_table.py` straight from `Results_10/results_json/*` and `our_experiments_vs_baseline/results/*` (no hand-typed numbers). Same data splits, same full test sets, same KSR protocol (5 predictions), for every column.

Each cell: **Results_10 (frozen shipped system) → now CPU-only (E+COV, in backend) → now best (I = E+COV + adapted BLOOM-560m, K=50)**  (change best vs Results_10)

| Metric (↑ higher better, ↓ lower better) | English | Hindi | Marathi | Gujarati |
|---|---|---|---|---|
| **KSR % ↑** (mean AAC+caregiver) | 56.29 → 57.49 → **62.75** (**+6.47**) | 56.74 → 58.28 → **60.72** (**+3.98**) | 48.73 → 51.86 → **54.53** (**+5.79**) | 53.04 → 55.60 → **57.59** (**+4.55**) |
| KSR % ↑ AAC-user turns | 53.70 → 55.18 → 60.58 (+6.88) | 55.65 → 57.20 → 59.89 (+4.24) | 46.17 → 49.44 → 52.27 (+6.10) | 50.92 → 53.87 → 56.08 (+5.16) |
| KSR % ↑ caregiver turns | 58.88 → 59.81 → 64.93 (+6.06) | 57.83 → 59.35 → 61.55 (+3.72) | 51.30 → 54.29 → 56.78 (+5.48) | 55.16 → 57.33 → 59.10 (+3.94) |
| top-1 hit % ↑ (nothing typed) | 16.81 → 17.11 → 23.97 (+7.16) | 27.57 → 28.83 → 30.67 (+3.10) | 16.29 → 16.98 → 20.52 (+4.23) | 23.59 → 25.32 → 28.78 (+5.19) |
| top-3 hit % ↑ (nothing typed) | 28.38 → 28.67 → 36.75 (+8.38) | 39.72 → 41.78 → 45.60 (+5.89) | 24.63 → 25.97 → 30.28 (+5.65) | 34.22 → 36.54 → 40.34 (+6.12) |
| top-5 hit % ↑ (nothing typed) | 33.39 → 34.26 → 42.38 (+8.99) | 45.52 → 48.10 → 51.75 (+6.23) | 28.94 → 30.02 → 34.78 (+5.84) | 39.08 → 41.88 → 46.44 (+7.36) |
| top-10 hit % ↑ (nothing typed) | 42.02 → 42.00 → 49.41 (+7.39) | 52.43 → 55.53 → 59.28 (+6.85) | 34.37 → 37.06 → 40.80 (+6.43) | 45.43 → 48.88 → 52.51 (+7.08) |
| char perplexity ↓ (full test) | 3.35 → not measured → **2.13** (-36%) | 3.16 → not measured → **2.48** (-21%) | 4.30 → not measured → **2.91** (-32%) | 3.86 → not measured → **2.95** (-24%) |
| (char 12-gram perplexity, for reference) | 4.70 (unchanged) | 4.38 (unchanged) | 5.47 (unchanged) | 4.99 (unchanged) |
| latency ↓ CPU per next-word call (p50) | 0.04 ms → 5.3 ms → 5.3 ms CPU + LM batch 38 ms p50 / 48 ms p95 (K=10, shared GPU) | 0.05 ms → 5.0 ms → 5.0 ms CPU + LM batch 43 ms p50 / 54 ms p95 (K=10, shared GPU) | 0.09 ms → 6.1 ms → 6.1 ms CPU + LM batch 48 ms p50 / 65 ms p95 (K=10, shared GPU) | 0.07 ms → 5.4 ms → 5.4 ms CPU + LM batch 42 ms p50 / 64 ms p95 (K=10, shared GPU) |
| 95% CI of KSR gain vs Results_10 (pp, AAC / care) | CPU-only [1.14, 1.91] / [0.59, 1.26]; best [6.25, 7.52] / [5.48, 6.6] | CPU-only [1.2, 1.91] / [1.19, 1.87]; best [3.75, 4.7] / [3.3, 4.13] | CPU-only [2.64, 3.88] / [2.44, 3.62]; best [5.3, 7.02] / [4.81, 6.25] | CPU-only [2.43, 3.5] / [1.77, 2.57]; best [4.49, 5.88] / [3.45, 4.47] |
| test OOV rate % (never suggestible by a fixed vocabulary) | 5.4 → reachable once ≥2 letters typed (COV) → same | 3.5 → reachable once ≥2 letters typed (COV) → same | 11.7 → reachable once ≥2 letters typed (COV) → same | 7.8 → reachable once ≥2 letters typed (COV) → same |

Reading notes (so the table is not over-read):
- "Now: CPU-only" is the system that is **now in the backend** (`predictor_v2.py`, see Step 9 below). "Now: best" needs the adapted BLOOM-560m on a GPU and is **not in the backend yet**.
- The "best" KSR/top-k use K=50 candidates re-scored by the LM. At K=10 the KSR is ~0.7-1.0 points lower (mr 53.48, gu 56.82, hi 59.88) and the LM batch takes the latency shown (38-48 ms p50); at K=50 it takes 136-175 ms p50. English K=10 KSR was not run.
- Latency got WORSE, not better: the shipped predictor takes 0.04-0.09 ms on CPU; the new CPU predictor takes 5-6 ms (cold caches, measured by `exp_step9_latency.py`; 11-15 ms for a 2-letter prefix with the fallback on); the LM adds tens of ms on top. All still interactive, but the "latency ↓" goal is not met.
- Perplexity: Results_10's shipped number is the ∞-gram open-vocabulary mix (end-of-sentence not scored); the "best" number is the adapted BLOOM on the same characters. The CPU-only column was not re-measured for perplexity.
- Marathi/Gujarati rows are on machine-translated data (indicative only). The CIs are paired bootstrap over test sentences.

## Step 9 (log numbering) - Plan step 4: integrate the CPU stack into the shipped backend (DONE 2026-11-21; app code now CHANGED)
Files changed / added in `indic-generative-aac/backend/` (nothing else in the app was touched):
- NEW `predictor_v2.py` - self-contained CPU predictor: **one model per language (en, hi, mr, gu)**, no selected-word exclusion, per-language context cap and back-off (tuned on dev), ∞-gram × char 12-gram mix (tuned on dev), and the **coverage fallback** (5 char-12-gram beam-search completions outside the vocabulary when ≥2 letters are typed). Lazy, thread-safe model build (0.6-1.1 s per language).
- NEW `predictor_data/{en,hi,mr,gu}.txt` - normalised training sentences (train+dev+test of the experiments, 3.5-5.5k per language). **Marathi/Gujarati are NLLB machine translations** (same caveat as in all results).
- EDIT `app.py` (+14/-4 lines): `/predict_next` now calls `predictor_v2` first and falls back to the legacy `hmm_engine` if v2 has no data or raises. New optional request field `prefix` (letters typed so far); when given it narrows every source (concept grammar, personal words, statistics). Kill switch: environment variable `AAC_PREDICTOR=legacy` restores the old behaviour exactly. A background thread warms the four models at startup.
- NEW `test_predictor_v2.py` - 7 tests (data present, script matches language, Gujarati uses a Gujarati model, prefix filtering, unseen prefix does not crash, repeated words allowed, unknown language → empty). All pass.

Verification (not just "it runs"):
1. **Parity**: `exp_step9_parity.py` trains `predictor_v2.LangModel` on the train split only and runs the same KSR simulator on the full test sets. It reproduces the experiment numbers to 3 decimals in all 4 languages: E (no fallback) en 56.515 / hi 57.798 / mr 49.378 / gu 54.249; E+COV en 57.495 / hi 58.277 / mr 51.863 / gu 55.602 (`results/step9_parity_*.log`).
2. **Endpoint**: the real `predict_next` function in `app.py` was called with stub requests (the HTTP route needs a login). Before/after, same inputs:
   - Marathi, context "मला": legacy returned the Hindi word "क्या" among its suggestions (Marathi was routed to the Hindi model); v2 returns Marathi only.
   - Marathi, context "मला", prefix "आ": legacy returned **nothing**; v2 returns आनंद, आणखी, आश्चर्य, आवडते, आमच्या.
   - Gujarati, empty context, prefix "હુ": legacy returned one word; v2 returns 5+ (some are character-model guesses, e.g. "હુમલોકો", that are not real words - this is the price of the fallback; the KSR gain above already counts such misses).
3. **Latency** (`exp_step9_latency.py`, CPU, cold caches): shipped 0.08-0.11 ms; v2 5.0-6.1 ms per next-word call, 11-15 ms for a 2-letter prefix with the fallback (hi/mr/gu), English 5.6 ms. Model build 0.6-1.1 s per language. Still interactive, but ~50-70× slower than the shipped predictor.

NOT done in this step (be aware):
- The **web UI does not send `prefix` yet** (`frontend/index.html`, `vnext.jsx` call `/predict_next` with words only), so the live UI gets the per-language models, the context cap and the char mix, but not yet the out-of-vocabulary completion. The API supports it; wiring a letter-typing box to it is a frontend change I did not make because I cannot test the UI visually here.
- In the live UI the board's concept predictor still interleaves with the statistical suggestions (`app.py` merge logic, unchanged), so the +1.2..+3.1 KSR measured in the simulator is an upper bound on what a user sees from the statistical shelf alone.
- The adapted-LM path (best system "I") is NOT in the backend (needs a GPU, 38-175 ms per query on the shared GPU).
- The app's existing de-duplication (`push()` skips words already in the sentence) was kept, so the "no selected-word exclusion" part of E has no effect in the live app.

## Step 10 (log numbering) - native Marathi/Gujarati text: access check and plan (started 2026-11-21; LOG, appended as work proceeds)
User request: use the Hugging Face native corpora (pasted list) to train on native text instead of only machine-translated text; use the GPU (12 GB, shared) and parallel workers; start when the GPU is free.
- **Login**: no Hugging Face token exists on this machine (`whoami` -> LocalTokenNotFoundError, no `HF_TOKEN`, no `~/.cache/huggingface/token`). I did not receive one in the chat, so I could not log in.
- **Anonymous access probe (streaming, first row)**:
  | Dataset | Result |
  |---|---|
  | `ai4bharat/IndicCorpV2` `indiccorp_v2` split `mar_Deva` | OK (Marathi news sentences) |
  | `ai4bharat/sangraha` `verified/mar`, `verified/guj` | OK (documents, `type: web`) |
  | `ai4bharat/indic-align` `Anudesh` | OK, but the first row is English prompts (not Marathi/Gujarati) - not used |
  | `Cossale/gujarati-speech-corpus` | **FAILS: gated** - needs `huggingface-cli login` + accepting terms (run `! huggingface-cli login` in this prompt if you want it) |
  | `cc100` / `statmt/cc100` | **FAILS**: dataset script no longer supported by `datasets` 5.0.1 (would need the parquet mirror) |
- **What native text can and cannot do here (stated up front)**: Sangraha/IndicCorpV2 are web/news text, not AAC conversation. They can add vocabulary/morphology coverage to the language model. They **cannot** replace the missing native AAC test set: any evaluation on them is out-of-domain. The KSR numbers will still be measured on the same machine-translated AAC test sets (so they stay comparable with every earlier result), plus a separate held-out native-text perplexity.
- **Plan**: (a) CPU, parallel: stream + filter native sentences (script purity, 3-15 words, de-duplicated, held-out shard) -> `our_experiments_vs_baseline/data_native/`; (b) GPU (when free): LoRA stage 1 on native sentences, stage 2 on the AAC train split, compared with the existing AAC-only adapter on dev/test char-ppl and system-I KSR at K=10; (c) log every number here.
- **Also running**: Step 9 cross-validation of system I (`results/cv_lm_<lang>.log`). Progress so far (K=10, ~190-273 test sentences per fold): English fold 0: A 52.33 / E+COV 53.54 / I 56.52; fold 1: 54.59 / 55.72 / 58.68. Hindi fold 0: 51.46 / 53.58 / 55.45. I beats A by 3.9, 4.1, 4.0 in these three folds. Final table when all 20 folds finish.
- **Step 9 incident (logged honestly)**: the Hindi cross-validation run crashed with `torch.OutOfMemoryError` (the shared GPU was full: another job holds ~6 GB, plus my English and Hindi processes). Only fold 0 was written (A 51.46 / E+COV 53.58 / I 55.45); files kept as `results/cv_lm_hi_run1_oom.log` / `cv_lm_hi_run1_partial.json`. Hindi is **re-queued to rerun in full** after the Gujarati run finishes (English -> Marathi and Gujarati continue). Lesson: run at most 2 GPU jobs at a time on this card.
- **Step 10 set-up done (2026-11-21)**: written and syntax-checked, not yet run on the GPU:
  - `our_experiments_vs_baseline/prep_native.py` - CPU, 2 languages in parallel, each with a 4-worker pool: streams Sangraha-verified (30k documents) + IndicCorpV2 (400k lines), sentence-splits, keeps 3-12-word script-pure sentences, de-duplicates, removes anything identical to our AAC dev/test sentences, splits by sentence hash into native train / dev / test. Output `data_native/<lang>_native_{train,dev,test}.txt` + `<lang>_native_info.json`. Running now.
  - `exp_native_lm.py` - GPU: BLOOM-560m LoRA stage 1 (native text, 1 epoch, best checkpoint by native-dev perplexity) then stage 2 (our AAC train split, 3 epochs, best by AAC dev). Four models compared: pretrained, AAC-only (existing adapter), native-only, native→AAC, on AAC full-test char-ppl, native held-out char-ppl and system-I KSR (K=10, full AAC test, paired-bootstrap CI vs the AAC-only adapter). Output `results/native_<lang>.json`.
  - `run_native.sh` - launcher: waits until the GPU has ≥4.5 GB free, then starts Marathi, then Gujarati (overlap only if memory allows; at most 2 of my jobs at once because the card is shared). The GPU is at 12.0/12.3 GB right now (cross-validation running), so nothing has started yet.
- **Hugging Face login (2026-11-21)**: logged in on this machine with the token the user supplied (stored only in the local Hugging Face cache; not written to any project file or to this log). `whoami` works; the token is a *fine-grained* token. `Cossale/gujarati-speech-corpus` is still **not accessible**: "gated dataset ... ask for access". The terms must be accepted on the dataset page by the user's own account (https://huggingface.co/datasets/Cossale/gujarati-speech-corpus), and a fine-grained token also needs the permission to read public gated repos. Until then the Gujarati native data is Sangraha + IndicCorpV2 only.
- **Step 10 data prep finished** (`data_native/*_native_info.json`): Marathi 759,849 unique native sentences (Sangraha-verified 396,773 + IndicCorpV2 379,178 before de-duplication); Gujarati 579,146 (352,463 + 236,534). Sentences identical to our AAC dev/test were removed (counts in the info files). Native held-out: ~2% test, ~2% dev by sentence hash; the rest is train.
- **Step 10 run 1 (Marathi, first 30k lines) - superseded, kept for the record** (`results/native_mr_run1_first30k*.{json,log}`): I noticed that taking the first 30,000 lines of the prepared file samples only the first Sangraha documents (the file is Sangraha first, then IndicCorpV2), i.e. a biased sample. Its numbers (char-ppl ↓, full test): AAC test: pretrained 10.44, AAC-only adapter 2.91, native-only 4.15, **native→AAC 2.81**; native held-out: pretrained 7.81, AAC-only 5.42, native-only 3.75, native→AAC 4.75. Native-dev perplexity was still falling at the end of the epoch (3.82 → 3.62), so more native data should help. Run killed before its KSR evaluation.
- **Step 10 run 2 (current)**: `exp_native_lm.py` now takes a RANDOM sample of 120,000 native sentences over both sources (seed 1). Same evaluation. Relaunched via `run_native.sh` (Marathi then Gujarati).

## Step 9 RESULT so far - 5-fold cross-validation of the language-model system "I" (English and Marathi DONE; Hindi and Gujarati re-queued) (2026-11-21)
Protocol (fixed before running): contiguous 5-fold blocks over train+dev+test; a NEW LoRA adapter trained per fold on that fold's training part only; epochs and CPU weight from the original dev run; K=10; evaluation on every 4th sentence of each test block (same sentences for all systems). KSR % ↑ (mean over folds ± sd). Code `exp_cv_lm.py`, results `results/cv_lm_<lang>.json`.

| Language | A shipped | E+COV (CPU) | I (K=10, adapted LM) | I − A: mean (sd), folds positive, pooled 95% CI | E+COV − A | I − E+COV |
|---|---|---|---|---|---|---|
| English (190 sent/fold) | 56.35 ± 3.08 | 57.19 ± 2.73 | **59.84 ± 2.38** | **+3.49** (0.73), 5/5, [3.16, 3.76] | +0.84, 5/5, [0.58, 1.07] | +2.65, 5/5, [2.41, 2.83] |
| Marathi (181 sent/fold) | 48.78 ± 1.46 | 52.34 ± 1.15 | **54.09 ± 0.95** | **+5.31** (0.70), 5/5, [4.92, 5.73] | +3.56, 5/5, [3.18, 3.98] | +1.75, 5/5, [1.45, 2.01] |

Reading: the language-model gain is positive in every fold and the pooled CIs exclude 0, so the full-test finding (system I > CPU-only > shipped) is **not a one-split artefact** for English and Marathi. With K=10 the English gain (+3.5) is smaller than the full-test K=50 figure (+6.5): K=10 costs accuracy (see Step 8), and the cross-validated sentences are a different subsample. Marathi (+5.3) matches its full-test number (+5.8 at K=50). Marathi is on machine-translated data. Hindi and Gujarati: both runs died with CUDA OOM on the shared GPU (Hindi fold 0 only: A 51.46 / E+COV 53.58 / I 55.45); logs kept as `results/cv_lm_hi_run{1,2}_*`, `cv_lm_gu_run1_oom.log`. `run_cv_rest.sh` reruns them one at a time after the native-text jobs finish.
- **Step 10 run 2 first launch failed (my bug, fixed)**: the edit that introduced the random sample left a `#` comment in the middle of a line and commented out the native dev/test loading (`NameError: nat_dev`). Fixed, syntax-checked, relaunched 10:24 (`results/native_launcher.log`). Run order now: native-text Marathi → native-text Gujarati → cross-validation Hindi → cross-validation Gujarati (`run_native.sh`, then `run_cv_rest.sh`; one GPU job at a time because the card is shared with other users' jobs). Estimated ~65 min per native-text language and ~35 min per cross-validation language.
- **Cossale/gujarati-speech-corpus access (2026-11-21)**: the user submitted the access request on the dataset page; it is **awaiting review by the dataset authors**. Until approved, the Gujarati native data stays Sangraha + IndicCorpV2. When approved: re-run the access probe, extract the `text` column, apply the same filter as `prep_native.py`, add to `data_native/gu_native_*`, and rerun Gujarati stage 1 with it. (Speech transcripts are the most conversational native Gujarati text on the list, so it is the one most worth waiting for.)

## Step 10 RESULT - does native Marathi/Gujarati text help the adapted LM? (DONE 2026-11-21; GPU, BLOOM-560m LoRA, 120,000 random native sentences + AAC train split)
Code `exp_native_lm.py`, data `data_native/`, results `results/native_<lang>.json`, logs `results/native_<lang>.log`. Stage 1 = native text only (1 epoch, 7,500 steps, ~33 min); stage 2 = our AAC train split (epoch picked on AAC dev: epoch 2 for both). KSR = system I (E+COV top-10 + adapted LM, w_cpu 0.1) on the FULL AAC test sets (machine-translated), paired-bootstrap 95% CI of the KSR change vs the AAC-only adapter (pp, AAC / care).

Char perplexity ↓ (full test; "native" = held-out Sangraha/IndicCorpV2 sentences, out-of-domain for AAC):

| Model | Marathi AAC test | Marathi native | Gujarati AAC test | Gujarati native |
|---|---|---|---|---|
| pretrained BLOOM-560m | 10.44 | 7.81 | 13.84 | 16.09 |
| AAC-only adapter (existing) | 2.91 | 5.42 | 2.95 | 8.49 |
| native-only (stage 1) | 3.90 | **3.61** | 3.99 | **5.14** |
| native → AAC (stage 2) | **2.76** | 4.28 | **2.78** | 6.35 |

KSR % ↑ / top-5 % ↑ (K=10, full AAC test):

| Model | Marathi | Gujarati |
|---|---|---|
| AAC-only adapter | 53.48 / 32.7 | 56.82 / 44.2 |
| native-only | 52.29 / 30.5 (CI [-1.21,-0.42] / [-1.97,-1.15]: **worse**) | 55.51 / 41.0 (CI [-1.61,-0.99] / [-1.60,-1.00]: **worse**) |
| native → AAC | 53.80 / 32.9 (CI [-0.18, 0.43] / [0.21, 0.82]: ≈ +0.3) | 56.77 / 43.7 (CI [-0.34, 0.07] / [-0.14, 0.25]: **tie**) |

Verdict (honest): native text improves the language model's *perplexity* a little on our AAC test (-5%: 2.91 → 2.76 Marathi, 2.95 → 2.78 Gujarati) and a lot on native text, but it does **not** improve keystroke savings: Marathi +0.3 KSR (small, borderline), Gujarati no change, and native-only training hurts KSR by ~1.2-1.3 points. Reason (hypothesis, not tested): web/news sentences teach formal vocabulary the AAC test set rarely uses; the AAC-domain stage restores most of what matters. Since the test set is machine-translated AAC text, this experiment cannot say whether native text helps *real* native AAC conversation - that needs the native test set. Cossale (conversational) access is still pending. Not worth switching the shipped adapter on this evidence.
- **Bug found (mine)**: `run_cv_rest.sh` (the queued Hindi/Gujarati cross-validation) never started: its wait loop `pgrep -f "run_native.sh|exp_native_lm.py"` matched the shell wrappers that contained those words, so it waited ~2.5 h for nothing. Fixed (no wait loop) and started 12:55 (Hindi, then Gujarati, ~35 min each).

## ALL SCORES - English and Hindi, proposed systems vs the baseline-style English systems (added 2026-11-21)
Built by `our_experiments_vs_baseline/make_full_table.py` from the JSON result files (no hand-typed numbers); the block between the markers is regenerated by `update_md_table.py` when the pending cells (marked "pending") are filled. Arrows: KSR ↑, top-k ↑, perplexity ↓, latency ↓. KSR (mean) = mean of the AAC-user and caregiver test sets, 5 word predictions. "top-k" = target word is among the k suggestions with nothing typed yet.
How the rows relate (read before comparing):
- **Full-test rows** (first English table, Hindi table): every system on the same 805 (English) / 1,027 (Hindi) test sentences. The baseline LLM rows (OPT) are NOT in these tables because the OPT character search is too slow to run on the full set.
- **Same-sample rows** (second English table): the OPT-125m / OPT-350m rows of Results_10 were measured only on 80+80 sentences (perplexity) and 40+40 (KSR). I re-evaluated our systems on exactly that sample so they can sit in the same table. Small sample: differences under ~2 KSR points are noise.
- E+COV has the same top-k as E because the coverage fallback only acts once ≥2 letters are typed (top-k is measured with nothing typed). With K=10, top-10 equals the CPU top-10 by construction (the language model only reorders the 10).
- The baseline paper's own numbers (last table) are on its private test sets and are shown for reference only.
<!-- FULLTABLE-START -->
**ENGLISH - full test set (403 AAC-user + 402 caregiver sentences)**

| System | KSR % ↑ (mean) | KSR AAC | KSR care | top-1 % ↑ | top-3 % ↑ | top-5 % ↑ | top-10 % ↑ | char perplexity ↓ | latency ↓ |
|---|---|---|---|---|---|---|---|---|---|
| frequency-only (no context) | 49.35 | 47.64 | 51.07 | | | | | - | - |
| AAC char 12-gram (baseline-type n-gram, our data) | **55.82** | 53.22 | 58.42 | 16.7 | 27.3 | 32.7 | 40.7 | 4.70 | 0.028 ms/char CPU |
| **Results_10 shipped ∞-gram** (reference) | **56.29** | 53.70 | 58.88 | 16.8 | 28.4 | 33.4 | 42.0 | 3.35 | 0.04 ms CPU |
| proposed: improved CPU stack E | **56.52** | 54.01 | 59.02 | 17.1 | 28.7 | 34.3 | 42.0 | not measured | ~5 ms CPU |
| proposed: E + coverage fallback (CPU only; **in backend**) | **57.49** | 55.18 | 59.81 | 17.1 | 28.7 | 34.3 | 42.0 | not measured | 5.3 ms CPU (next word), 5.6 ms with 2-letter prefix |
| proposed: I with K=10 | not run for English | | | | | | | | |
| proposed: **I = E+COV top-50 + adapted BLOOM-560m (GPU, best)** | **62.75** | 60.58 | 64.93 | 24.0 | 36.8 | 42.4 | 49.4 | 2.13 | CPU + LM batch 136 ms p50 / 218 ms p95 (shared GPU) |

**ENGLISH - the baseline-style systems (OPT-125m / OPT-350m, run by us with the baseline paper's character-search method) and ours on the SAME small sample** (80+80 sentences for perplexity, the first 40+40 of them for KSR; differences below ~2 KSR points are noise at this size)

| System | KSR % ↑ (mean) | KSR AAC | KSR care | top-1 % ↑ | top-3 % ↑ | top-5 % ↑ | top-10 % ↑ | char perplexity ↓ | latency ↓ |
|---|---|---|---|---|---|---|---|---|---|
| baseline-type: AAC char 12-gram | **55.08** | 53.08 | 57.09 | 13.7 | 23.8 | 29.8 | 37.5 | 4.93 | 0.03 ms/char CPU |
| baseline LLM: OPT-125m pretrained | **58.01** | 56.05 | 59.98 | 18.1 | 30.2 | 36.4 | 41.3 | 2.65 | 82 ms/char GPU (search) |
| baseline LLM: OPT-350m pretrained | **58.91** | 57.13 | 60.69 | 20.0 | 31.2 | 36.9 | 42.5 | 2.52 | 141 ms/char GPU (search) |
| baseline LLM: OPT-125m adapted on our data (the baseline's adaptation) | **62.64** | 60.39 | 64.89 | 23.5 | 38.7 | 44.9 | 55.6 | 2.07 | 24 ms/char GPU (search) |
| **Results_10 shipped ∞-gram** (reference) | **55.86** | 53.87 | 57.85 | 13.9 | 25.3 | 30.5 | 39.8 | 3.57 | 0.05 ms CPU |
| proposed: improved CPU stack E | **55.79** | 53.87 | 57.70 | 14.5 | 25.1 | 31.3 | 39.8 | not measured | ~5 ms CPU |
| proposed: E + coverage fallback (CPU only; in backend) | **56.76** | 54.45 | 59.07 | 14.5 | 25.1 | 31.3 | 39.8 | not measured | ~5-6 ms CPU |
| proposed: I top-10 (adapted BLOOM-560m, GPU) | **59.53** | 57.20 | 61.85 | 19.0 | 31.7 | 34.9 | 39.8 | 2.12 | CPU + ~38 ms LM batch |
| proposed: **I top-50 (adapted BLOOM-560m, GPU)** | **62.65** | 60.10 | 65.20 | 21.9 | 36.9 | 41.2 | 46.8 | 2.12 | CPU + ~136 ms LM batch |

(our shipped ∞-gram re-run on this sample reproduces Results_10 exactly: KSR AAC 53.87, care 57.85 - see `results/same_sample_en_cpu.json`; the perplexity column of the ∞-gram row is the open-vocabulary mix, as in Results_10.)

**HINDI - full test set (507 AAC-user + 520 caregiver sentences)**

| System | KSR % ↑ (mean) | KSR AAC | KSR care | top-1 % ↑ | top-3 % ↑ | top-5 % ↑ | top-10 % ↑ | char perplexity ↓ | latency ↓ |
|---|---|---|---|---|---|---|---|---|---|
| AAC char 12-gram (baseline-type n-gram, our data) | **57.33** | 56.21 | 58.45 | 27.5 | 40.7 | 47.0 | 54.9 | 4.38 | 0.050 ms/char CPU |
| **Results_10 shipped ∞-gram** (reference) | **56.74** | 55.65 | 57.83 | 27.6 | 39.7 | 45.5 | 52.4 | 3.16 | 0.05 ms CPU |
| proposed: improved CPU stack E | **57.80** | 56.61 | 58.99 | 28.8 | 41.8 | 48.1 | 55.5 | not measured | ~5 ms CPU |
| proposed: E + coverage fallback (CPU only; **in backend**) | **58.28** | 57.20 | 59.35 | 28.8 | 41.8 | 48.1 | 55.5 | not measured | 5.0 ms CPU (next word), 11.2 ms with 2-letter prefix |
| proposed: I = E+COV top-10 + adapted BLOOM-560m (GPU) | **59.88** | 59.09 | 60.67 | 30.5 | 44.6 | 50.4 | 55.5 | 2.48 | CPU + LM batch 43 ms p50 / 54 ms p95 (shared GPU) |
| proposed: **I = E+COV top-50 + adapted BLOOM-560m (GPU, best)** | **60.72** | 59.89 | 61.55 | 30.7 | 45.6 | 51.8 | 59.3 | 2.48 | CPU + LM batch 153 ms p50 / 263 ms p95 (shared GPU) |

(Hindi has no OPT/baseline-LLM rows: the baseline's OPT models are English-only and were not run for Hindi.)

**Reference only - the baseline paper's own published numbers (Gaines & Vertanen, `paper1.tex` Tables 3-4), on THEIR private test sets, 5 words predicted - NOT comparable in absolute value with the rows above:**

| Baseline-paper system | KSR % ↑ average over its 5 test sets | KSR % ↑ on its AAC-user set | perplexity ↓ average | time per prediction |
|---|---|---|---|---|
| AAC n-gram (KenLM) | 59.7 | 55.3 | 2.54 | 0.1 ms |
| C4+Sub n-gram | 59.6 | 56.4 | 2.58 | 0.1 ms |
| C4+Sub n-gram (full) | 60.5 | 57.4 | 2.53 | 0.1 ms |
| OPT-350m (no adaptation), search | 63.2 | 63.1 | 2.28 | 79.1 ms |
| OPT-350m adapted C4→Sub→BOLT→Daily | 65.0 | 62.5 | 2.12 | 78.9 ms |
| OPT-350m adapted C4→Sub→BOLT+Daily | 65.0 | 62.3 | 2.12 | 78.2 ms |
| OPT-350m adapted BOLT+Daily (best) | **65.2** | 62.7 | **2.11** | 78.0 ms |
| ByGPT5 (byte LLM) | 64.5 | 61.6 | 2.21 | 11.6 ms |

<!-- FULLTABLE-END -->

## Step 9 RESULT, COMPLETE - 5-fold cross-validation of the language-model system "I", all 4 languages (2026-11-21)
Hindi and Gujarati reruns finished (all 5 folds each; the earlier OOM logs are kept as `results/cv_lm_*_oom.log`). Same protocol as the English/Marathi table above (new adapter per fold, K=10, every 4th sentence of each test block, knobs fixed from the original dev run). KSR % ↑, mean ± sd over 5 folds:

| Language | A shipped | E+COV (CPU) | I (K=10) | I − A: mean (sd), folds positive, pooled 95% CI | E+COV − A | I − E+COV |
|---|---|---|---|---|---|---|
| English (190/fold) | 56.35 ± 3.08 | 57.19 ± 2.73 | **59.84 ± 2.38** | **+3.49** (0.73), 5/5, [3.16, 3.76] | +0.84, 5/5, [0.58, 1.07] | +2.65, 5/5, [2.41, 2.83] |
| Hindi (273/fold) | 54.69 ± 2.38 | 56.43 ± 2.25 | **58.08 ± 2.03** | **+3.39** (0.49), 5/5, [3.12, 3.64] | +1.74, 5/5, [1.53, 1.96] | +1.65, 5/5, [1.47, 1.83] |
| Marathi (181/fold) | 48.78 ± 1.46 | 52.34 ± 1.15 | **54.09 ± 0.95** | **+5.31** (0.70), 5/5, [4.92, 5.73] | +3.56, 5/5, [3.18, 3.98] | +1.75, 5/5, [1.45, 2.01] |
| Gujarati (177/fold) | 53.38 ± 1.46 | 55.61 ± 1.07 | **56.70 ± 1.26** | **+3.31** (0.48), 5/5, [2.98, 3.64] | +2.23, 5/5, [1.94, 2.52] | +1.08, 5/5, [0.89, 1.31] |

Conclusion: in **all 4 languages and all 20 folds** the adapted-LM system beats the shipped predictor (every fold positive, pooled CIs exclude 0) and beats the CPU-only system. The cross-validated gains at K=10 (+3.3 to +5.3) are smaller than the full-test K=50 gains (+4.0 to +6.5) because K=10 gives up ~0.7-1.0 KSR (Step 8) and the folds are a subsample; they are the more conservative figures. Marathi/Gujarati use machine-translated data. This closes plan step 9 for the LM system.

### Verdict from the filled-in same-sample table (2026-11-21)
On the baseline's own sample (40+40 sentences for KSR, 80+80 for perplexity; noise ≈ ±2 KSR points):
- KSR: our best system I (K=50) **62.65** vs the baseline's method with in-domain adaptation (OPT-125m adapted, character search) **62.64** → a **tie**. I at K=10 (the faster setting): 59.53, between the baseline's pretrained OPT-350m (58.91) and the adapted OPT-125m.
- top-5 / top-10 hit (nothing typed): adapted OPT-125m 44.9 / 55.6 vs I(K=50) 41.2 / 46.8 → **the baseline's adapted LLM is better on top-k**. Reason in part: I only re-ranks the CPU stack's top-50, so words outside that shortlist can never reach the top-10.
- Perplexity: adapted OPT-125m 2.07 vs adapted BLOOM 2.12 → the baseline's adapted LLM is slightly better.
- So the honest English claim is: our best system **matches** the baseline's adapted-LLM method on KSR and does not beat it; our additional value is the CPU-only path (no GPU, ~5 ms, +1.0 KSR over the shipped system), multilingual support, sentence generation and safety checks - not a better English next-word predictor. The BLOOM/OPT difference is within noise at this sample size and was not tested on the full test set (the OPT search is too slow to run there).
- All 9 plan steps: prediction-quality steps (1, 2, 3, 5, 7, 9) done and cross-validated; step 4 (per-language engines in the app) done for the CPU stack; steps 6 and 8 (native AAC test sets, live generation cascade, MOS, user study) remain NOT done - they need people/native data/the live backend.
