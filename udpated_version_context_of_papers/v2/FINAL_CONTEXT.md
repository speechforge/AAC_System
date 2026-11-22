# FINAL_CONTEXT: Indic AAC Studio, evaluation and repair (v2 experiments)

Written 2026-11-13 (IST) after the experiments of `AAC_01_Experiments_and_FINAL_CONTEXT.md`.

Written for the paper author. Tables are rendered by `src/render_tables.py` from `results/tables/*.csv` and `results/audit/*`; no table number is typed by hand. Narrative numbers were checked against the same files.

**Labels used throughout.** *Archived* = the system and outputs of the earlier evaluation (commit `fe4e185`, scorer v1). *Revised* = the repaired working tree after the freeze. *Exploratory* = Hinglish and every post-hoc probe. **All holdout fixtures are DRAFT (native-speaker checks pending). Holdout scores below are preliminary and must stay out of the paper until two native speakers per language have confirmed the gold annotation (section 10, gap 1).** 175/175 is an engineering target, not a result; every count below is measured.

## 1. Source revision, environment, dirty state

| Item | Value |
|---|---|
| Repository | `AAC_System_merged`, branch `merged`, HEAD `fe4e185763a181674534656dbf95e30709cf83ff` |
| Dirty state at write time | modified tracked: `backend/app.py`, `llm.py`, `semantic.py`, `tts.py`, `frontend/index.html`; new untracked backend files `aac_lexicon.py`, `templates.py`, `pipeline.py`, `board_concepts.json`; untracked docs `CONTEXT.md`, `NAACL_PAPER_BUNDLE.md`, `paper/`, `udpated_version_context_of_papers/` |
| Patch of the repair | `patches/revised_system_tracked_files.patch` (+ `patches/new_files/`); archived originals in `archived_system/` (hashes `config/archived_system_sha256.txt`) |
| Freeze | `config/freeze_manifest.json` (SHA-256 of every rule, prompt, decoding, scorer and runner file; written 2026-11-13 before the holdout existed, re-written once for Addendum 1 with identical system-file hashes; first manifest `config/freeze_manifest_v1_superseded.json`). `python src/freeze.py --check` returned FREEZE OK locally and on the PC. |
| Model | `Qwen/Qwen2.5-0.5B-Instruct`, revision `7ae557604adf67be50417f59c2c2f167def9a775`, `model.safetensors` SHA-256 prefix `fdf756fa7fcb...` (identical on both machines), fp16 on GPU |
| Local machine | NVIDIA GTX 1650 4 GB (driver 595.99.02), Python 3.13.13, torch 2.11.0+cu130, transformers 5.14.1 |
| PC (alias PC_Nisarg, 10.100.59.86) | NVIDIA TITAN Xp 12 GB (driver 580.178.04), 16 cores, Python 3.12.3, venv `~/aac_v2_env`: torch 2.11.0+cu126 (CUDA 13 wheels do not support Pascal), transformers 5.14.1 |
| SSH | Port 22 was refused until sshd was installed on the PC; the new host key was confirmed by the user, the stale `known_hosts` entry was replaced, then GPU jobs moved to the PC (the user asked to spare the local 4 GB GPU). |

**Where each part ran.** Phase A: local CPU. Browser captures and speech/latency check: local (Chrome; the speech check uses the local GTX 1650 server because that is the demo configuration). Development streams and determinism check: local GTX 1650. Holdout streams, legacy regression streams and one-pass comparator: **PC TITAN Xp** (file names contain `remote`). Local partial holdout rows (GTX 1650) are kept in `results/streams/local_gtx1650/` and compared with the PC rows in section 7.4. Live-path end-to-end run: PC server.

## 2. Paths and conventions

```
udpated_version_context_of_papers/v2/
  FINAL_CONTEXT.md            this file (template: FINAL_CONTEXT.template.md)
  run_all.sh                  evaluation + analysis commands (section 3)
  src/                        all scripts (audit_*, build_fixtures, browser_capture, run_streams, run_onepass, replay, analyze_v2, score_v2, ...)
  config/                     freeze manifests, archived hashes
  fixtures/{legacy,dev,holdout}/scenarios.jsonl   fixture manifests (+ PREREGISTRATION.md, native_gold_check_<lang>.csv, README_DRAFT.md, build_log*.json)
  results/audit/              Phase A evidence (A1..A8) and Phase B/D checks (B_*, D_*)
  results/payloads/           requests captured from the REAL browser client (original and revised)
  results/streams/            candidate streams (trace files); cache_*.jsonl = prompt-level generation cache
  results/scored/             one row per scenario, language, input mode, system, seed, stage (scorer v2)
  results/tables/             T1..T7 paired tables;  results/figures/  figure + source CSV + script copy
  results/checks/             fixture and integrity checks;  results/e2e/ live-path runs
  reviewer_packet/            blind native-rater packet, demo captures
  logs/EXPERIMENT_LOG.md      time-stamped audit trail;  remote/ PC job scripts
```
Scenario schema: `id, group, family, lang, seq, labels, concept_ids, content_concepts, customs, more, gold_act, gold_neg, expected_outcome, template_covered, intended_en, status`. One **group** is one underlying message rendered in four languages; bootstrap resamples groups.

## 3. Exact commands

`run_all.sh` lists the full sequence. Evaluation (GPU, one command per job type, all keyed and resumable): `python src/run_streams.py --split holdout --jobs G0:orig G0:gold G1:rev G1:gold G1:cross --seeds 11 23 47`, `python src/run_onepass.py --split holdout --modes rev gold --seeds 11 23 47`, `python src/run_streams.py --split legacy --jobs G1:rev G1:gold --seeds 11`. Analysis (CPU): `python src/analyze_v2.py --split holdout`, `python src/check_all.py --split holdout --run-commands`, `python src/make_figure.py --split holdout`. Remote execution: `remote/remote_sync_and_run.sh`, `remote/remote_jobs.sh`.

## 4. What ran (and what did not)

| Item | Status | Where / artifact |
|---|---|---|
| A. reproduce and audit the archived run | **done** (CPU) | `results/audit/A1..A8`, section 5 |
| B. repairs (client, protocol, gate, templates, realiser prefix, scorer v2) | **done**, frozen | `patches/`, `config/freeze_manifest.json`, section 6 |
| Dev split, gate probes, tuning | **done** | `fixtures/dev/`, `results/tables/*_dev.csv` (tuned: not evidence) |
| Pre-registered holdout (120 items = 30 groups x 4 languages), overlap checks | **done**, DRAFT labels | `fixtures/holdout/`, `results/checks/fixture_checks_holdout.json` |
| Real-browser payload capture, original and revised client | **done** (dev 84, legacy 184, holdout 120 per client; Hinglish not clickable, uses archived API payloads) | `results/payloads/` |
| Systems on the holdout: archived deployed, matched one-pass, ungated cascade (first and last), repaired template, repaired hybrid, gate-only change, interface cross | **done** | `results/streams/`, `results/scored/holdout_scored.csv`, `results/tables/` |
| Three prespecified seeds (11, 23, 47), English sampling path | **done** (Indic path is greedy: seeds not applicable) | streams |
| Regression of the original 175 on the repaired system | **done** (one seed, 11) | `results/tables/*_legacy.csv` |
| Live HTTP path vs offline replay | **done** (PC server), 180/180 identical | `results/audit/B_replay_vs_live_holdout_pc.json` |
| User-selectable intent control | **implemented and run on the 8 ambiguous items** (16 requests) | `results/e2e/ambiguity_user_choice_pc.jsonl` |
| Determinism of retry; cross-hardware reproducibility | **done** | `B_determinism_check.json`, `B_crosshardware_repro.json` |
| Blind native-rater packet | **built, ratings PENDING** | `reviewer_packet/` |
| Native-speaker check of the gold annotation | **PENDING** | `fixtures/*/native_gold_check_<lang>.csv` |
| Browser-to-speech path on the GTX 1650 (32 UI runs) | **done**; real speech **not** verifiable (no IndicF5 weights, 0 browser voices in headless Chrome) | `results/audit/B_speech_path.json` |
| Demo captures (success, rejection + fallback, clarification, server unreachable) | **done** | `reviewer_packet/demo_captures/*.png` |
| Clean-environment install test | **done on CPU** with the shared Hugging Face cache (see limits) | `results/audit/D_clean_env_test.json` |
| Hosted demo and screencast links | **none exist / not accessible** | section 10 |
| Two-pass GPU work split | all holdout, legacy and one-pass GPU jobs ran on the PC's TITAN Xp; the PC's first freeze check failed only because the client file had not been synced yet and passed after syncing (all frozen files byte-identical); the legacy explicit-gold stream was **not run separately**: on all 184 legacy and 120 holdout selections the repaired client's payload and the explicit-gold payload normalise to **identical contexts**, so the gold rows of the repaired system are the same stream (`legacy_derived_g1gold_from_g1rev`; on the holdout both were run and are identical). | `logs/EXPERIMENT_LOG.md`, `logs/remote/` |


## 5. Phase A: reproduction and audit of the ARCHIVED run (local CPU, no model)

Preserved: archived outputs (`paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results/`), original scorer (`score.py`, v1, unchanged) and original fixture (SHA-256 in `config/archived_artifacts_sha256.txt`). Scripts: `src/audit_archived.py`, `audit_scorer.py`, `audit_classify.py`, `predict_audit.py`. Result: **2304/2304 archived rows, 20/20 published counts, 9/9 exclusions, 32/32 bootstrap CIs and the prediction replay reproduce exactly** (log line 2026-11-13T08:59Z).

**A1 claims recomputed from the raw outputs** (`results/audit/A1_claims_check.csv`, observation label: archived):

| claim | manuscript | recomputed | match |
|---|---|---|---|
| unconstrained Qwen success (single prompt) | 8/175 | 8/175 | True |
| cascade before gate, browser input | 65/175 | 65/175 | True |
| deployed, browser input | 97/175 | 97/175 | True |
| template alone, browser input | 118/175 | 118/175 | True |
| cascade before gate, explicit gold fields | 71/175 | 71/175 | True |
| deployed, explicit gold fields | 132/175 | 132/175 | True |
| template alone, explicit gold fields | 167/175 | 167/175 | True |
| concept retention, deployed (browser) | 215/215 | 215/215 | True |
| concept retention, deployed (explicit) | 215/215 | 215/215 | True |
| concept retention, cascade before gate (browser) | 175/215 | 175/215 | True |
| concept retention, cascade before gate (explicit) | 185/215 | 185/215 | True |
| polarity errors vs gold, cascade (explicit) | 36/175 | 36/175 | True |
| polarity errors vs gold, deployed (explicit) | 0/175 | 0/175 | True |
| wrong-act outputs, deployed (browser) | 54/175 | 54/175 | True |
| wrong-act outputs, deployed (explicit) | 17/175 | 17/175 | True |
| accepted outputs failing full scoring (explicit) | 37/108 | 37/108 | True |
| template fallbacks failing full scoring (explicit) | 6/67 | 6/67 | True |
| template-only failures (explicit) | 8/175 | 8/175 | True |
| primary scenarios by language EN/HI/GU/MR | 46/45/42/42 | 46/45/42/42 | True |
| monolingual scenarios / excluded / Hinglish | 184 / 9 / 8 | 184 / 9 / 8 | True |

**A2 exclusions.** 184 monolingual scenarios, 8 Hinglish (exploratory only), primary 175 (EN 46, HI 45, GU 42, MR 42), 215 concept instances. Nine scenarios are excluded because the query string `llm.py` builds equals a few-shot example input (verified against the archived prompt source by AST parse): `hi-T1-WATER`, `gu-T1-WATER`, `gu-T1-FOOD`, `gu-T2-NO+FOOD`, `gu-T3-HAPPY`, `mr-T1-WATER`, `mr-T1-FOOD`, `mr-T2-NO+FOOD`, `mr-T3-HAPPY` (reason per row in `A2_exclusion_log.csv`). All-184 sensitivity (includes the overlap items; `A2_all184_sensitivity.json`): browser template 125, cascade 72, deployed 104; explicit template 176, cascade 80, deployed 141; unconstrained prompt 8 (unchanged).

**A3 cohorts and the eight template-only failures.** Explicit-field cohorts: accepted model outputs 108 (37 fail scorer v1), template fallbacks 67 (6 fail), template alone 175 (8 fail). The two marginal tables place all eight template-only failures in Gujarati negated feelings (`gu-T4_negated_feeling-NO+{HAPPY,SAD,ANGRY,TIRED,SICK,SCARED,LOVE,EXCITED}`); the join of scenario IDs confirms it. Inspection of every failing output (`A3_failure_classification.csv`, classified by the authoring assistant, **not native-checked**): the eight outputs are the valid negated-feeling form "મને X લાગતું નથી"; the v1 Gujarati feeling-marker list lacked `લાગતું`, so they are **scorer lexical gaps, not realisation errors**. Of the 37 accepted-model failures, 35 are genuine (12 negated want instead of negated feeling, 10 ungrammatical, 9 third-person reports, 4 added content) and 2 are scorer gaps; of the 6 fallback failures all 6 are scorer gaps (14 scorer gaps in total across the fallback and template-only cohorts).

**A4 unconstrained prompt (8/175).** Recovered settings: model revision above, ChatML default chat template, greedy (temperature 0.01 -> `do_sample=False`), `max_new_tokens` 75, stop at EOS, no output parsing, labels only as input, system prompt "You are an assistive communication tool..." (full text in `A4_naive_baseline.json`). Reasons (overlapping flags, n=175): act marker missing 163, wrong act 3, unsupported 7, off-task 16, polarity wrong 2, script wrong 4; concepts fully retained 159/175; **132 of the 167 failures fail only because no request or feeling marker is present** (descriptive outputs such as "Water is a liquid").

**A5 scorer audit** (`A5_scorer_probes.csv`, `A5_offtask_causes.json`). The v1 "off-task" flag is not a test of a user's refusal: it bundles model refusals (`sorry`), the English pattern "the user" (23 outputs in the cascade stages), empty or over-long text and Latin leakage; the pattern `can't` would also flag a legitimate negated request. Negation is **not** clause-scoped in v1 (any negator anywhere counts). Third person is caught only by the English pattern "the user". Valid Gujarati, Hindi and Marathi desire constructions and "would love" fail the v1 marker lists. On 20 hand-written probes v1 agrees with the expected verdict 9/20.

**A6 the "27 of 32 feeling selections".** Denominator: single-symbol selections, 8 feeling symbols x 4 locales = 32 (not scenarios, not the 175). 27 were sent as REQUEST, 5 as STATEMENT. The same audit over all 276 single selections finds 3 false negations by substring (`Bathe` Gujarati `નાહવું`, `Nose` English and Gujarati) (`A6_feeling_denominator.json`).

**A7 paired CIs** recomputed with the archived seed (20261111) reproduce the archived intervals; a pooled group-level bootstrap with the new seed (20261113) is in `A7_paired_ci_recomputed.json`.

**A8 prediction table.** Unrounded counts: English infinity-gram 381/2220 = 17.162 % hit@1, trigram 356/2220 = 16.036 %, so the gain is **+1.126 pp from counts** (+1.2 pp from the printed rounded values). Hindi 659/2437 = 27.041 % vs 630/2437 = 25.851 %: **+1.190 pp from counts** (the printed rounded values give +1.1). Denominators: 60 source conversations per language; English 392 distinct test utterances (18 seen verbatim in training), 167 OOV target items (7.5 %, kept in the denominator); Hindi 384 distinct (28 seen verbatim), 133 OOV items (5.5 %). Repeat-filtered test on the same train split (OOV kept): English n=2170, trie minus trigram **+0.968 pp, 95 % CI [0.374, 1.544]** (cluster bootstrap over the 60 conversations); Hindi +1.02 pp [0.206, 1.818]. Table: `A8_prediction_counts.csv`.


## 6. Phase B: targeted repairs (REVISED system) and how they were tuned and frozen

**What changed** (files in `patches/`; all active before the freeze):

| Area | Repair | File |
|---|---|---|
| Act and polarity | Separate fields: `act` in {REQUEST, FEELING, FEELING_REQUEST, QUESTION, GREETING, UNKNOWN} and `negation`. A refusal is REQUEST + negation; a negated feeling is FEELING + negation. Explicit user choice (`act_source: user`) is never overridden. Legacy payloads (`intent` REQUEST/WANT/STATEMENT/FEEL/QUESTION/NEGATION, no `act`) are still accepted; for them only an unspecified REQUEST act is reconciled when every selected symbol is a feeling. | `pipeline.py`, `app.py` |
| Browser client | Board tokens carry stable concept IDs; typed, predicted and "My Words" entries carry none and are matched only as whole tokens (so `Nose` and `નાહવું` are no longer negations). The NO symbol sets polarity wherever it appears. Feelings, negated feelings and refusals are analysed by concept ID in all four languages. A **Message type** control (Auto / Request / Feeling / Question) lets the user override. Ambiguous selections show a localized clarification card (two buttons) instead of guessing; literal previews are labelled and not spoken automatically; a server error shows the literal words only; placeholder audio is labelled "Placeholder tone" instead of "IndicF5 Voice". Verified by driving the real UI in Chrome and capturing the POST body (`src/browser_capture.py`): on the 184 legacy and 120 holdout selections the revised client sent the gold polarity and act every time (0 mismatches), while the original client sent a wrong act for 59 of 184 legacy selections. | `frontend/index.html` |
| Realiser prompt | The negated-feeling case no longer uses the negated-want prefix: prefix "I am saying + NOT + feeling" plus one few-shot example per language built on a non-board word (so no scenario can reproduce it); English ledger names the act FEELING. Everything else in the prompts, the model and decoding is unchanged, so generator differences between archived and revised are small and separable. | `llm.py` |
| Gate (V1, `gate-v2`) | Locale-aware, documented rules: script/language (no Latin leakage), off-task and meta text, **speaker perspective** (third-person reports rejected, implicit first person accepted), **concept presence** by board ID with locale forms and inflections, **substitutions and additions** (any unselected board concept or distractor), unrequested reason/time words, **polarity and negation scope** (the negator must sit in the clause of the selected concept; right word in the wrong clause is rejected), **communicative act** (request marker / state marker / both; a feeling under a request marker is rejected), Hindi `khana` homograph rule (food and eat), length. Reason codes are logged per attempt. It is a heuristic: its false acceptances and rejections are tracked (sections 7.3 and `T4_gate_confusion`). | `semantic.py`, `aac_lexicon.py` |
| Template (T1) | Compositional, locale-specific frames: request, refusal, feeling, negated feeling, action (+ object, + negation), call or help a person, feeling + request, MORE, two objects. Noun gender (Gujarati, Marathi), case forms and gender-neutral constructions where the speaker's gender would otherwise be marked. **Not covered by design**: movement to a place, greetings, body parts, places alone, two feelings, negation over a feeling-plus-request. The fallback is checked by the gate; if no safe sentence exists the result is a **clarification** (no determinate act) or a labelled **literal preview**; a technical failure is a third, distinct outcome. Linguistic status: written by the authoring assistant, **not native-reviewed**. | `templates.py` |
| Outcomes | `sentence_model`, `sentence_template`, `clarification`, `literal_preview`, `failure` (and `sentence_ungated` for the evaluation switch). Only a sentence is spoken; the decision to speak a clarification or literal preview is the user's. | `app.py` |
| Retry policy | Unchanged (2 attempts). The code carries an optional `skip_deterministic_retry` switch that is **off**; it is justified by the determinism check (section 7.5) but was not used for any reported number. | `pipeline.py` |
| Scorer v2 | Corrections for every gap found in Phase A (section 5 A5, A3): marker lists for valid Gujarati/Hindi/Marathi/English constructions, scoped negation, off-task split into refusal / meta / third person / long / empty / Latin leak (user's own `can't` no longer flagged), reason and time words, "feeling under a request marker", Hindi `khana` homograph, inflected short forms. The archived report is kept; **both scorers were run on the same saved archived outputs** (`results/audit/B_scorer_effect.csv`). On 20 hand-written probes v2 agrees 19/20 (v1 9/20; the remaining disagreement is `I can't have pizza.` whose expected verdict is arguable). | `src/score_v2.py` |

**Effect of the scorer change on the archived outputs (primary 175; archived system, observation label: archived):**

| system | cond | n | success_v1 | success_v2 | n_changed |
|---|---|---|---|---|---|
| deployed | st | 175 | 132 | 138 | 12 |
| deployed | ui | 175 | 97 | 95 | 12 |
| literal_join | any | 175 | 0 | 0 | 0 |
| llm1 | st | 175 | 67 | 68 | 7 |
| llm1 | ui | 175 | 63 | 61 | 12 |
| llm2 | st | 175 | 67 | 68 | 7 |
| llm2 | ui | 175 | 64 | 62 | 12 |
| llm3_pre | st | 175 | 71 | 72 | 7 |
| llm3_pre | ui | 175 | 65 | 63 | 12 |
| naive_qwen | ui | 175 | 8 | 8 | 4 |
| template_only | st | 175 | 167 | 175 | 8 |
| template_only | ui | 175 | 118 | 118 | 0 |

All eight Gujarati template-only failures flip to success under v2 (167 to 175), confirming that they were lexical gaps. The browser-condition deployed count moves 97 to 95 and the explicit-condition deployed count 132 to 138 (cases and flags: `B_scorer_effect_cases.csv`).

**Development split and tuning.** `fixtures/dev/` (84 items = 21 groups x 4 languages, families in `fixtures/PREREGISTRATION.md`) and 92 hand-written gate probes (`fixtures/dev/gate_probes.jsonl`, `src/make_gate_probes.py`) were used for tuning. Gate on the probes: archived gate 30/52 false acceptances and 10/40 false rejections; revised gate 0/52 and 0/40 (synthetic probes written by the same author: not independent evidence). Changes made while tuning on dev: quantity symbol MORE carried into the template; Gujarati verb forms; Hindi food/eat rule; feeling-under-request rule (gate and scorer). Changes made after inspecting the **legacy** regression set (which Phase A had already shown to the author, so it is an audit/regression set and not a clean test): Marathi `आई` case forms in the gate, short-form inflection matching in the scorer, Hindi/Marathi EAT forms in the scorer. Dev numbers after tuning (revised hybrid and repaired template 80/80 on determinate dev items) are **tuned results and are not evidence**.

**Freeze and holdout.** After tuning, `src/freeze.py` wrote `config/freeze_manifest.json`; only then was `src/build_fixtures.py holdout` executed (guarded: it refuses to run without the manifest). The first run failed the pre-registered overlap rules (three items reproduced few-shot inputs; H4 shares a semantic key with legacy single feelings because ME is a function symbol). **Addendum 1** to the pre-registration (written before any holdout output existed) enforces rule 3 by rejection inside the generator and admits H4 in rule 2; the first draw is kept (`fixtures/holdout/*first_draw_rejected*`). No system file changed (identical hashes in both manifests). **Who saw what:** one assistant session wrote the plan, the generator, the rules and the scorer; no independent curator existed; no holdout output was inspected before scoring, but the holdout items were visible to the author when the PC runs were started and when the repaired template's literal-preview behaviour on uncovered families was glimpsed on partial streams (no rule was changed afterwards).


## 7. Phase C: matched systems on fresh scenarios (holdout = DRAFT; PRELIMINARY: keep out of the paper until the gold annotation is native-checked)

### 7.1 Design as run
* **Scenarios.** 120 items = 30 groups x 4 languages. 112 items (28 groups) are *determinate*; 8 items (2 groups: `BAD`, `HEART` alone) are deliberately ambiguous with the clarification as target and are excluded from strict success. Template-covered: 100 determinate items; template-uncovered by design (go to a place, greeting a person): 12 items. Families, counts and the overlap rules: `fixtures/PREREGISTRATION.md` (+ Addendum 1). Overlap check: 0 exact-sequence overlaps with legacy or dev, 0 few-shot overlaps, semantic-key overlaps only inside the word-order families and H4 (listed in `results/checks/fixture_checks_holdout.json`).
* **Systems and what each receives.** *Archived deployed system*: archived `llm.py` cascade + archived gate + archived template; receives the original client's payload (labels with "No", substring-inferred intent) or the explicit-gold legacy fields. *Matched one-pass Qwen*: same model revision, ChatML chat template, target language, **same fields as the repaired hybrid** (act, polarity, concepts), decoding as the realiser path of that language (English temperature 0.1, 3 seeds, 60 tokens; Indic greedy, 75 tokens), asks for one first-person sentence, no examples, no gate. *Same cascade, gate and fallback disabled*: first candidate, and last candidate after an earlier rejection (reported separately). *Repaired template alone*: no model. *Repaired hybrid*: realiser + refiner + verifier + gate V1 + retry (2 attempts) + template T1 + clarification / literal outcomes. *Gate-only change*: identical archived candidates, retry policy and archived template, only the gate replaced (V0 -> V1).
* **Inputs.** (i) repaired browser (payload captured from the real client); (ii) explicit gold fields (diagnostic upper bound for input interpretation); (iii) original browser; (iv) "cross": original-client payload sent to the repaired realiser (interface effect). **On all 120 holdout selections the repaired client sent the gold act and polarity (0 mismatches); the original client sent the gold polarity too (0 mismatches) but is handled by the legacy contract.** After normalisation the repaired-browser and explicit-gold contexts are identical, so those two columns coincide by construction (their difference is exactly 0.0 pp). This is a property of one author's rules, not an independent finding.
* **Seeds.** 11, 23, 47 for the English sampling path of every applicable system; the same seeds across systems (seeds set per attempt: seed + 1000 x attempt). Indic: single greedy run. Per-scenario value = mean over seeds; draws are never counted as new scenarios.
* **Metric definitions (units, denominators).** *Strict full-scenario success* (scorer v2): every selected concept present, polarity correct with scoped negation, gold act expressed, no added concept / reason / time word, no third-person report, correct script, not off-task; **a literal preview, clarification or failure is not a sentence and therefore counts as not successful on a determinate item**. Denominator 112 items (pooled) or 28 items (one language). *Concept retention*, *missed concepts*: concept instances (270 instance-draws). *Error flags* overlap; denominators are determinate scenario-draws: 168 = 28 English items x 3 seeds + 84 Indic items x 1. *Model coverage*: share of determinate draws whose final text is a model output accepted by the gate. *Accepted-output error rate*: accepted model outputs that fail the scorer / accepted model outputs. *Fallback rate / success*: template outputs after rejection / those passing the scorer. Missing outputs and timeouts stay in the denominator: **0 occurred** (0 generation errors in 1032 stream rows, 0 in 360 one-pass calls, 0 HTTP errors in 180 live requests).
* **Aggregation and uncertainty.** Paired difference in percentage points, A minus B, on the 112 determinate items; 95 % percentile bootstrap, 10,000 resamples of the **28 scenario groups** (the four language versions of one message share a group), seed 20261113; all systems, modes and seeds of a group travel together. Per-language intervals resample the same groups (n = 28 items, 28 groups: wide). Sparse strata (family cells of 8 to 12 items) are flagged in `T6_by_family_holdout.csv`.

### 7.2 Strict success (all counts are k/n over 112 determinate items; English values are means over 3 seeds)

| System | Input | EN | HI | GU | MR | Pooled k/n (rate) | 95% CI (group bootstrap) |
|---|---|---|---|---|---|---|---|
| archived system (deployed) | explicit gold fields | 20.3/28 (72.6%) | 21.0/28 (75.0%) | 20.0/28 (71.4%) | 17.0/28 (60.7%) | 78.3/112 (69.9%) | [58.9,80.4] |
| archived system (deployed) | original browser | 16.7/28 (59.5%) | 13.0/28 (46.4%) | 17.0/28 (60.7%) | 15.0/28 (53.6%) | 61.7/112 (55.1%) | [41.1,68.2] |
| archived few-shot realiser alone (LLM-1 stage) | explicit gold fields | 0.7/28 (2.4%) | 9.0/28 (32.1%) | 9.0/28 (32.1%) | 13.0/28 (46.4%) | 31.7/112 (28.3%) | [19.3,37.2] |
| archived few-shot realiser alone (LLM-1 stage) | original browser | 0.7/28 (2.4%) | 6.0/28 (21.4%) | 13.0/28 (46.4%) | 11.0/28 (39.3%) | 30.7/112 (27.4%) | [19.3,35.7] |
| repaired few-shot realiser alone (LLM-1 stage) | original-browser payload into repaired realiser | 0.0/28 (0.0%) | 11.0/28 (39.3%) | 14.0/28 (50.0%) | 13.0/28 (46.4%) | 38.0/112 (33.9%) | [24.1,43.8] |
| repaired few-shot realiser alone (LLM-1 stage) | explicit gold fields | 0.0/28 (0.0%) | 10.0/28 (35.7%) | 14.0/28 (50.0%) | 13.0/28 (46.4%) | 37.0/112 (33.0%) | [24.1,42.9] |
| repaired few-shot realiser alone (LLM-1 stage) | repaired browser | 0.0/28 (0.0%) | 10.0/28 (35.7%) | 14.0/28 (50.0%) | 13.0/28 (46.4%) | 37.0/112 (33.0%) | [24.1,42.9] |
| archived cascade, no gate (first candidate) | explicit gold fields | 1.0/28 (3.6%) | 9.0/28 (32.1%) | 9.0/28 (32.1%) | 13.0/28 (46.4%) | 32.0/112 (28.6%) | [19.6,37.5] |
| archived cascade, no gate (first candidate) | original browser | 0.0/28 (0.0%) | 6.0/28 (21.4%) | 13.0/28 (46.4%) | 11.0/28 (39.3%) | 30.0/112 (26.8%) | [18.8,34.8] |
| archived cascade, no gate (last candidate) | explicit gold fields | 1.0/28 (3.6%) | 9.0/28 (32.1%) | 9.0/28 (32.1%) | 13.0/28 (46.4%) | 32.0/112 (28.6%) | [19.6,37.5] |
| archived cascade, no gate (last candidate) | original browser | 0.0/28 (0.0%) | 6.0/28 (21.4%) | 13.0/28 (46.4%) | 11.0/28 (39.3%) | 30.0/112 (26.8%) | [18.8,34.8] |
| archived candidates, revised gate, archived template | explicit gold fields | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 104.0/112 (92.9%) | [82.1,100.0] |
| archived candidates, revised gate, archived template | original browser | 21.0/28 (75.0%) | 21.0/28 (75.0%) | 21.0/28 (75.0%) | 22.0/28 (78.6%) | 85.0/112 (75.9%) | [58.9,90.2] |
| revised cascade, no gate (first candidate) | original-browser payload into repaired realiser | 0.0/28 (0.0%) | 11.0/28 (39.3%) | 14.0/28 (50.0%) | 13.0/28 (46.4%) | 38.0/112 (33.9%) | [24.1,43.8] |
| revised cascade, no gate (first candidate) | explicit gold fields | 0.0/28 (0.0%) | 10.0/28 (35.7%) | 14.0/28 (50.0%) | 13.0/28 (46.4%) | 37.0/112 (33.0%) | [24.1,42.9] |
| revised cascade, no gate (first candidate) | repaired browser | 0.0/28 (0.0%) | 10.0/28 (35.7%) | 14.0/28 (50.0%) | 13.0/28 (46.4%) | 37.0/112 (33.0%) | [24.1,42.9] |
| revised cascade, no gate (last candidate) | original-browser payload into repaired realiser | 0.0/28 (0.0%) | 11.0/28 (39.3%) | 14.0/28 (50.0%) | 13.0/28 (46.4%) | 38.0/112 (33.9%) | [24.1,43.8] |
| revised cascade, no gate (last candidate) | explicit gold fields | 0.0/28 (0.0%) | 10.0/28 (35.7%) | 14.0/28 (50.0%) | 13.0/28 (46.4%) | 37.0/112 (33.0%) | [24.1,42.9] |
| revised cascade, no gate (last candidate) | repaired browser | 0.0/28 (0.0%) | 10.0/28 (35.7%) | 14.0/28 (50.0%) | 13.0/28 (46.4%) | 37.0/112 (33.0%) | [24.1,42.9] |
| revised hybrid | original-browser payload into repaired realiser | 24.0/28 (85.7%) | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 25.0/28 (89.3%) | 101.0/112 (90.2%) | [80.4,98.2] |
| revised hybrid | explicit gold fields | 25.0/28 (89.3%) | 27.0/28 (96.4%) | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 104.0/112 (92.9%) | [83.9,100.0] |
| revised hybrid | repaired browser | 25.0/28 (89.3%) | 27.0/28 (96.4%) | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 104.0/112 (92.9%) | [83.9,100.0] |
| archived template alone | explicit gold fields | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 104.0/112 (92.9%) | [82.1,100.0] |
| archived template alone | original browser | 21.0/28 (75.0%) | 21.0/28 (75.0%) | 21.0/28 (75.0%) | 21.0/28 (75.0%) | 84.0/112 (75.0%) | [57.1,89.3] |
| archived template alone | repaired browser | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 26.0/28 (92.9%) | 104.0/112 (92.9%) | [82.1,100.0] |
| repaired template alone | explicit gold fields | 25.0/28 (89.3%) | 25.0/28 (89.3%) | 24.0/28 (85.7%) | 25.0/28 (89.3%) | 99.0/112 (88.4%) | [75.0,99.1] |
| repaired template alone | repaired browser | 25.0/28 (89.3%) | 25.0/28 (89.3%) | 24.0/28 (85.7%) | 25.0/28 (89.3%) | 99.0/112 (88.4%) | [75.0,99.1] |
| matched one-pass Qwen prompt | explicit gold fields | 4.0/28 (14.3%) | 0.0/28 (0.0%) | 0.0/28 (0.0%) | 0.0/28 (0.0%) | 4.0/112 (3.6%) | [0.9,6.8] |
| matched one-pass Qwen prompt | repaired browser | 4.0/28 (14.3%) | 0.0/28 (0.0%) | 0.0/28 (0.0%) | 0.0/28 (0.0%) | 4.0/112 (3.6%) | [0.9,6.8] |

### 7.3 Paired differences (A minus B, percentage points, 95 % group bootstrap)

| Comparison (A vs B) | Lang | Items | Groups | A-B (pp) | 95% CI | A-only / B-only wins |
|---|---|---|---|---|---|---|
| end-to-end: revised hybrid (browser) vs archived system (browser) | ALL | 112 | 28 | 37.8 | [21.73, 53.87] | 49/5 |
| end-to-end, explicit gold fields: revised hybrid vs archived system | ALL | 112 | 28 | 22.92 | [10.12, 35.71] | 31/5 |
| gate effect: revised hybrid vs same generator without gate/fallback (first candidate) | ALL | 112 | 28 | 59.82 | [47.32, 71.43] | 67/0 |
| gate effect, gold fields | ALL | 112 | 28 | 59.82 | [47.32, 71.43] | 67/0 |
| gate effect, archived system (browser): deployed vs ungated first candidate | ALL | 112 | 28 | 28.27 | [19.05, 37.2] | 34/1 |
| gate effect, archived system (gold): deployed vs ungated first candidate | ALL | 112 | 28 | 41.37 | [30.65, 52.68] | 47/0 |
| pure gate change V0 -> V1 on identical archived candidates (gold fields) | ALL | 112 | 28 | 22.92 | [14.88, 31.55] | 26/0 |
| pure gate change V0 -> V1 on identical archived candidates (browser) | ALL | 112 | 28 | 20.83 | [13.1, 28.87] | 25/0 |
| revised hybrid vs matched one-pass prompt (browser fields) | ALL | 112 | 28 | 89.29 | [80.65, 96.43] | 101/0 |
| revised hybrid vs matched one-pass prompt (gold fields) | ALL | 112 | 28 | 89.29 | [80.65, 96.43] | 101/0 |
| revised hybrid vs the few-shot realiser alone (LLM-1 stage, no refiner / verifier / gate) | ALL | 112 | 28 | 59.82 | [47.32, 71.43] | 67/0 |
| revised hybrid vs repaired template alone (browser) | ALL | 112 | 28 | 4.46 | [0.89, 9.82] | 5/0 |
| revised hybrid vs repaired template alone (gold) | ALL | 112 | 28 | 4.46 | [0.89, 9.82] | 5/0 |
| repaired template (revised client) vs archived template (original client) | ALL | 112 | 28 | 13.39 | [-8.04, 34.82] | 28/13 |
| repaired template vs archived template (gold fields) | ALL | 112 | 28 | -4.46 | [-20.54, 10.71] | 8/13 |
| interface effect: revised-browser vs explicit gold fields (hybrid) | ALL | 112 | 28 | 0.0 | [0.0, 0.0] | 0/0 |
| interface effect: same realiser, original-client payload vs revised-client payload | ALL | 112 | 28 | -2.68 | [-7.14, 0.0] | 0/3 |
| interface effect on the template | ALL | 112 | 28 | 0.0 | [0.0, 0.0] | 0/0 |

**Verified observations (preliminary, DRAFT fixtures, scorer v2, one author for rules, gold and scorer):**
1. **Gate effect.** With generator and inputs fixed, the repaired hybrid beats the same repaired cascade without gate and fallback by **+59.8 pp (95 % CI 47.3 to 71.4; 67 items only the hybrid solves, 0 only the cascade)**; the archived system's own gate adds +28.3 pp (19.1 to 37.2) on browser input and +41.4 pp (30.7 to 52.7) on explicit fields over its ungated first candidate. The ungated cascades score 26.8 to 33.9 % (English 0 to 3.6 %, because the model answers in third person: "The user requested ...").
2. **Pure gate change** (identical archived candidates, same retry policy and archived template): V0 -> V1 **+22.9 pp (14.9 to 31.6)** on explicit fields and **+20.8 pp (13.1 to 28.9)** on browser input; 26 and 25 items improve, 0 worsen.
3. **End to end.** Repaired hybrid (repaired browser) vs archived system (original browser): **+37.8 pp (21.7 to 53.9)**, 49 items only the repaired system solves, 5 only the archived one; on explicit fields +22.9 pp (10.1 to 35.7).
4. **Template alone vs hybrid.** Hybrid minus repaired template **+4.5 pp (0.9 to 9.8)**, five items, all of them where the template deliberately returns a literal preview (the four go-to-place/greeting items the model realised acceptably and one gate false rejection, section 7.4). The hybrid does **not** beat the template on any template-covered item (100/100 vs 99/100): **the gate is a safeguard, the template carries 119 of 154 hybrid sentences**.
5. **Repaired template vs archived template (both given correct fields).** On the 100 template-covered items the repaired template succeeds on 99 and the archived template on 92: the archived template fails the feeling-plus-request group (two groups x four languages, e.g. "I want Happy Play.", "I want Tired Sleep.": a feeling put under a request marker). On the 12 template-uncovered items it is 0 against 12: the archived template emits a sentence for everything and the lexical scorer accepts it ("I want Go Hospital.", "I want Go School.", "I want Hello Friend."), while the repaired template returns a literal preview. The pooled difference, repaired minus archived, is -4.5 pp (95 % CI -20.5 to 10.7), inconclusive: +7 items on covered frames and -12 items on uncovered frames that follow from the literal-preview policy. With the original client's payload the repaired template is +13.4 pp (-8.0 to 34.8; 28 items better, 13 worse). The scorer cannot see ungrammatical phrasing, so **the phrasing question is open and is the reason the human rating packet exists.**
6. **Matched one-pass prompt.** 3.6 % (4/112; English 14.3 %, Indic 0 %): hybrid minus one-pass **+89.3 pp (80.7 to 96.4)**. The comparison is dominated by prompting: the pre-registered one-pass prompt has no examples and Qwen2.5-0.5B answers in Latin script, gibberish or third-person narration; the few-shot realiser alone (LLM-1 stage, no refiner/verifier/gate) reaches 33.0 %. A few-shot one-pass comparator was not pre-registered and was not run.
7. **Interface effect.** Same repaired realiser, original-client payload vs repaired-client payload: -2.7 pp (-7.1 to 0.0); the three losing items are the feeling-plus-request selection `Happy + Play` (English, Hindi), which the original client labels a feeling and the backend honours under the legacy contract, and one greeting. The small gap is because the repaired backend reconciles the act of legacy payloads that say REQUEST for a feeling and drops the "No" symbol; the original client's wrong acts cost the archived system 14.8 pp between explicit fields and browser input (69.9 % vs 55.1 %).
8. **Retries.** First and last candidates give identical success (cascade 26.8 / 33.0 %), the Indic retry reproduced the first candidate in 354/354 stream rows and in 40/40 uncached repeats (`B_determinism_check.json`), the English retry (new seed) changed the text in 109/415 rows without changing any reported rate. The retry is therefore a pure latency cost for Indic output; the optional skip switch was not used.

### 7.4 Gate correctness and coverage (first candidates of the saved streams, determinate items, draws, scorer v2 as reference)

| gate | generator | lang | n | accept_correct | accept_wrong | reject_wrong | reject_correct | coverage_accept_rate | accepted_error_rate | false_reject_of_correct | false_accept_of_wrong |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V0_archived | G0 | ALL | 336 | 60 | 83 | 189 | 4 | 0.426 | 0.58 | 0.062 | 0.305 |
| V0_archived | G0 | en | 168 | 3 | 28 | 137 | 0 | 0.185 | 0.903 | 0.0 | 0.17 |
| V0_archived | G0 | gu | 56 | 21 | 15 | 19 | 1 | 0.643 | 0.417 | 0.045 | 0.441 |
| V0_archived | G0 | hi | 56 | 15 | 21 | 20 | 0 | 0.643 | 0.583 | 0.0 | 0.512 |
| V0_archived | G0 | mr | 56 | 21 | 19 | 13 | 3 | 0.714 | 0.475 | 0.125 | 0.594 |
| V0_archived | G1 | ALL | 448 | 104 | 94 | 242 | 8 | 0.442 | 0.475 | 0.071 | 0.28 |
| V0_archived | G1 | en | 196 | 0 | 31 | 165 | 0 | 0.158 | 1.0 |  | 0.158 |
| V0_archived | G1 | gu | 84 | 37 | 9 | 33 | 5 | 0.548 | 0.196 | 0.119 | 0.214 |
| V0_archived | G1 | hi | 84 | 31 | 21 | 32 | 0 | 0.619 | 0.404 | 0.0 | 0.396 |
| V0_archived | G1 | mr | 84 | 36 | 33 | 12 | 3 | 0.821 | 0.478 | 0.077 | 0.733 |
| V1_revised | G0 | ALL | 336 | 62 | 2 | 270 | 2 | 0.19 | 0.031 | 0.031 | 0.007 |
| V1_revised | G0 | en | 168 | 3 | 0 | 165 | 0 | 0.018 | 0.0 | 0.0 | 0.0 |
| V1_revised | G0 | gu | 56 | 22 | 0 | 34 | 0 | 0.393 | 0.0 | 0.0 | 0.0 |
| V1_revised | G0 | hi | 56 | 15 | 1 | 40 | 0 | 0.286 | 0.062 | 0.0 | 0.024 |
| V1_revised | G0 | mr | 56 | 22 | 1 | 31 | 2 | 0.411 | 0.043 | 0.083 | 0.031 |
| V1_revised | G1 | ALL | 448 | 104 | 1 | 335 | 8 | 0.234 | 0.01 | 0.071 | 0.003 |
| V1_revised | G1 | en | 196 | 0 | 0 | 196 | 0 | 0.0 |  |  | 0.0 |
| V1_revised | G1 | gu | 84 | 36 | 0 | 42 | 6 | 0.429 | 0.0 | 0.143 | 0.0 |
| V1_revised | G1 | hi | 84 | 30 | 1 | 52 | 1 | 0.369 | 0.032 | 0.032 | 0.019 |
| V1_revised | G1 | mr | 84 | 38 | 0 | 45 | 1 | 0.452 | 0.0 | 0.026 | 0.0 |

The archived gate V0 accepts 43 to 44 % of first candidates and **47.5 to 58.0 % of what it accepts is wrong** (83 accepted-wrong of 143 accepted on the archived stream, 94 of 198 on the repaired stream; draws); the revised gate V1 accepts 19 to 23 % and its accepted-output error rate is **3.1 % (2 of 64) and 1.0 % (1 of 105)**; false rejections (correct candidates rejected) are 2 of 64 and 8 of 112. Figure: `results/figures/fig_gate_holdout.{png,pdf}` (panel A: gate verdict against scorer; panel B: error categories of the final output), data `fig_gate_source_holdout.csv`, script `src/make_figure.py`.
The seven distinct V1 disagreements with the scorer (all listed with texts by `src/dev_inspect.py`-style replay): (a) **false rejection of a valid Gujarati desire construction** "ફોન કરવો છે" (gate lacks the construction the scorer has), two items; (b) false rejection of greeting items judged under a legacy REQUEST act (cross and archived-gold payloads), three draws of two items; (c) **false acceptance** "मला रागात नाही." because the gate counts a bare first-person pronoun as a state marker, one item; (d) **false acceptance** of "मैं खेलना हूँ, मैं खुश हूँ।" under a legacy payload that labelled a feeling-plus-request selection as a feeling, one item. One further **false rejection of a valid template** was found in the frozen gate: Gujarati "મને જવાનું મન નથી." fails because the gate's form for GO (`જવ`) is a two-letter exact-token form (`gu-H7-03`); the hybrid still answered with an accepted model sentence, the template alone returned a literal preview. These are failures of the frozen heuristic and were **not repaired** after the freeze.

### 7.5 Outcomes, routes, families, determinism, hardware, live path

| system | mode | n_determinate | n_sentence_model | n_sentence_template | model_accepted | accepted_error | fallback | fallback_success | first_attempt_accepted | n_ambiguous | ambiguous_clarified | ambiguous_literal | ambiguous_confident_sentence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| archived_deployed | gold | 168 | 75 | 93 | 75 | 41 | 93 | 85 | 72 | 12 | 0 | 0 | 12 |
| archived_deployed | orig | 168 | 75 | 93 | 75 | 49 | 93 | 69 | 71 | 12 | 0 | 0 | 12 |
| archived_llm1_stage | gold | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 12 |
| archived_llm1_stage | orig | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 12 |
| revised_llm1_stage | cross | 112 |  |  | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 8 |
| revised_llm1_stage | gold | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| revised_llm1_stage | rev | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| cascade_ungated_first | gold | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 12 |
| cascade_ungated_first | orig | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 12 |
| cascade_ungated_last | gold | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 12 |
| cascade_ungated_last | orig | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 12 |
| gate_only_v1 | gold | 168 | 34 | 134 | 34 | 0 | 134 | 122 | 34 | 12 | 0 | 0 | 12 |
| gate_only_v1 | orig | 168 | 31 | 137 | 31 | 2 | 137 | 98 | 31 | 12 | 0 | 0 | 12 |
| revised_cascade_first | cross | 112 |  |  | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 8 |
| revised_cascade_first | gold | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| revised_cascade_first | rev | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| revised_cascade_last | cross | 112 |  |  | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 8 |
| revised_cascade_last | gold | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| revised_cascade_last | rev | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| revised_hybrid | cross | 112 | 35 | 67 | 35 | 1 | 67 | 67 | 35 | 8 | 0 | 2 | 6 |
| revised_hybrid | gold | 168 | 35 | 119 | 35 | 0 | 119 | 119 | 35 | 12 | 12 | 0 | 0 |
| revised_hybrid | rev | 168 | 35 | 119 | 35 | 0 | 119 | 119 | 35 | 12 | 12 | 0 | 0 |
| template_archived | gold | 112 |  | 112 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 8 |
| template_archived | orig | 112 |  | 112 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 8 |
| template_archived | rev | 112 |  | 112 | 0 | 0 | 0 | 0 | 0 | 8 | 0 | 0 | 8 |
| template_revised | gold | 112 |  | 99 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 |
| template_revised | rev | 112 |  | 99 | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 |
| onepass | gold | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 12 |
| onepass | rev | 168 |  |  | 0 | 0 | 0 | 0 | 0 | 12 | 0 | 0 | 12 |

Outcomes of the repaired hybrid (repaired browser, determinate draws, n = 168): model output accepted 35 (**0 wrong**), checked template after rejection 119 (**119 correct**), literal preview 14 (all on the three template-uncovered groups), clarification 0, failure 0. Archived system (original browser): model accepted 75 (**49 wrong**), template 93 (69 correct); on the 12 ambiguous draws it produced a confident sentence 12 times and never asked, the repaired hybrid asked 12/12 (target met by design, not by luck). By family (`T6_by_family_holdout.csv`): every template-covered family 100 % (cells of 8 to 12 items), template-uncovered family 4/12 (the remaining eight items end as literal previews, the intended safe behaviour, but they count as strict failures).

* **Live path equals replay.** 180 requests (120 payloads, English x 3 seeds) through the web backend on the PC with the captured browser payloads: 180/180 identical text and outcome to the offline replay of the saved streams (`B_replay_vs_live_holdout_pc.json`).
* **Cross-hardware reproducibility.** The 304 holdout candidates first generated on the GTX 1650 were regenerated on the TITAN Xp (same weights, prompts, decoding, seeds, transformers 5.14.1, torch 2.11.0 with cu130 vs cu126): final candidate identical in **278/304 (91.4 %)**: English (seeded sampling) 120/140, Hindi 52/55, Marathi 51/54, Gujarati 55/55 (`B_crosshardware_repro.json`). Results are not bit-reproducible across GPUs; every paired comparison above uses one machine.
* **User-selected act** (the repaired Message-type control, 8 ambiguous items x 2 choices, live PC pipeline, exploratory n = 16, `ambiguity_user_choice_pc.jsonl`): the explicit choice is always respected and reaches the endpoint (`act_source: user`). Feeling on `Bad`: English and Marathi template sentences ("I feel bad.", "मला वाईट वाटते."), Gujarati model sentence "હું ખરાબ છું." accepted by the gate although it means "I am bad", Hindi template rejected by the gate (label `खराब` vs template word `बुरा`) so a literal preview. Request on `Bad`: model sentences such as "मुझे खराब चाहिए।" are accepted (the user's choice is followed even when semantically odd). `Heart`: five of eight requests end as literal previews, the Gujarati feeling answer "હૃદય હું કહું." was accepted by the gate. The gate checks concepts and act markers, not sense.

### 7.6 Latency cost (seconds; method differences)

| method | hardware | lang | route | n | median_s | p95_s | note |
|---|---|---|---|---|---|---|---|
| revised hybrid, live HTTP /generate | PC TITAN Xp | en | all | 90 | 2.944 | 3.631 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | en | template_after_rejection | 75 | 2.957 | 3.633 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | en | clarification | 6 | 0.001 | 0.001 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | hi | all | 30 | 3.883 | 4.362 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | hi | model_first | 10 | 2.002 | 2.25 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | hi | template_after_rejection | 17 | 4.021 | 4.393 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | hi | clarification | 2 | 0.001 | 0.001 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | gu | all | 30 | 3.423 | 3.833 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | gu | model_first | 12 | 1.842 | 1.951 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | gu | template_after_rejection | 14 | 3.697 | 3.9 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | gu | clarification | 2 | 0.001 | 0.001 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | mr | all | 30 | 2.21 | 3.544 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | mr | model_first | 13 | 1.699 | 1.747 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | mr | template_after_rejection | 13 | 3.449 | 3.544 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | mr | clarification | 2 | 0.001 | 0.001 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | ALL | all | 180 | 2.966 | 4.085 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | ALL | model_first | 35 | 1.812 | 2.146 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | ALL | template_after_rejection | 119 | 3.261 | 4.117 |  |
| revised hybrid, live HTTP /generate | PC TITAN Xp | ALL | clarification | 12 | 0.001 | 0.001 |  |
| revised hybrid, click to first playback (browser) | local GTX 1650 | en | all | 7 | 12.357 | 12.43 |  |
| revised hybrid, click to first playback (browser) | local GTX 1650 | hi | all | 8 | 15.263 | 21.54 |  |
| revised hybrid, click to first playback (browser) | local GTX 1650 | gu | all | 8 | 7.899 | 8.482 |  |
| revised hybrid, click to first playback (browser) | local GTX 1650 | mr | all | 8 | 10.701 | 15.198 |  |
| revised hybrid, click to first playback (browser) | local GTX 1650 | ALL | all | 31 | 9.949 | 20.769 |  |
| revised cascade, first attempt (LLM-1+2+3, no gate) (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | en | stage sum | 172 | 0.984 | 7.097 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| revised cascade, first attempt (LLM-1+2+3, no gate) (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | hi | stage sum | 61 | 7.271 | 8.82 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| revised cascade, first attempt (LLM-1+2+3, no gate) (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | gu | stage sum | 59 | 6.938 | 8.487 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| revised cascade, first attempt (LLM-1+2+3, no gate) (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | mr | stage sum | 59 | 6.362 | 7.548 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| revised cascade, first attempt (LLM-1+2+3, no gate) (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | ALL | stage sum | 351 | 6.142 | 8.36 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| archived cascade, first attempt (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | en | stage sum | 180 | 0.956 | 6.971 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| archived cascade, first attempt (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | hi | stage sum | 60 | 7.222 | 8.628 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| archived cascade, first attempt (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | gu | stage sum | 60 | 6.761 | 8.893 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| archived cascade, first attempt (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | mr | stage sum | 60 | 6.194 | 7.802 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| archived cascade, first attempt (original uncached GPU calls only: cached repeats excluded where latency is 0) | PC TITAN Xp | ALL | stage sum | 360 | 5.913 | 8.318 | measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost |
| matched one-pass prompt (single call) | PC TITAN Xp | en | single call | 90 | 0.968 | 1.527 |  |
| matched one-pass prompt (single call) | PC TITAN Xp | hi | single call | 30 | 0.713 | 2.447 |  |
| matched one-pass prompt (single call) | PC TITAN Xp | gu | single call | 30 | 3.037 | 3.552 |  |
| matched one-pass prompt (single call) | PC TITAN Xp | mr | single call | 30 | 0.73 | 1.714 |  |
| matched one-pass prompt (single call) | PC TITAN Xp | ALL | single call | 360 | 0.927 | 3.449 |  |
| repaired template alone (normalise + compose + gate) | CPU (local) | ALL | no model | 120 | 0.401 | 0.508 | median_s / p95_s columns hold MILLISECONDS for this row |

Live path on the PC (no speech synthesis, placeholder tone): repaired hybrid median **2.97 s, p95 4.09 s** (accepted first attempt 1.8 s; template after two rejected attempts 3.3 s; clarification 0.001 s). Browser click to first playback on the GTX 1650 (32 runs, 31 warm): **median 9.9 s, p95 20.8 s** (accepted model output about 7.9 s, template after rejection about 14.2 s). The one-pass call is the cheapest model path (median 0.9 s on the PC); the template alone costs about 0.4 ms on a CPU. The stage-sum rows of the cascade were measured while five jobs shared the PC's GPU and are inflated: use the live rows.

### 7.7 Regression of the original 175 (archived = scorer v2 on the saved archived outputs, one sample per payload; revised = one seed for English)

The legacy set informed the repairs (section 6): this is a **regression result, not a test result**. 175/175 is an engineering target and is stated here because it was measured.

| System | Input | EN | HI | GU | MR | Pooled k/n (rate) | 95% CI (group bootstrap) |
|---|---|---|---|---|---|---|---|
| archived system (deployed) | explicit gold fields | 33.0/46 (71.7%) | 40.0/45 (88.9%) | 33.0/42 (78.6%) | 32.0/42 (76.2%) | 138.0/175 (78.9%) | [72.8,84.8] |
| archived system (deployed) | original browser | 22.0/46 (47.8%) | 24.0/45 (53.3%) | 26.0/42 (61.9%) | 23.0/42 (54.8%) | 95.0/175 (54.3%) | [42.6,65.7] |
| archived few-shot realiser alone (LLM-1 stage) | explicit gold fields | 1.0/46 (2.2%) | 26.0/45 (57.8%) | 17.0/42 (40.5%) | 24.0/42 (57.1%) | 68.0/175 (38.9%) | [30.7,46.9] |
| archived few-shot realiser alone (LLM-1 stage) | original browser | 1.0/46 (2.2%) | 17.0/45 (37.8%) | 25.0/42 (59.5%) | 18.0/42 (42.9%) | 61.0/175 (34.9%) | [26.7,43.3] |
| repaired few-shot realiser alone (LLM-1 stage) | explicit gold fields | 3.0/46 (6.5%) | 29.0/45 (64.4%) | 27.0/42 (64.3%) | 26.0/42 (61.9%) | 85.0/175 (48.6%) | [41.2,55.8] |
| repaired few-shot realiser alone (LLM-1 stage) | repaired browser | 3.0/46 (6.5%) | 29.0/45 (64.4%) | 27.0/42 (64.3%) | 26.0/42 (61.9%) | 85.0/175 (48.6%) | [41.2,55.8] |
| archived cascade, no gate (first candidate) | explicit gold fields | 5.0/46 (10.9%) | 26.0/45 (57.8%) | 17.0/42 (40.5%) | 24.0/42 (57.1%) | 72.0/175 (41.1%) | [33.1,49.1] |
| archived cascade, no gate (first candidate) | original browser | 3.0/46 (6.5%) | 17.0/45 (37.8%) | 25.0/42 (59.5%) | 18.0/42 (42.9%) | 63.0/175 (36.0%) | [27.6,44.4] |
| revised cascade, no gate (first candidate) | explicit gold fields | 6.0/46 (13.0%) | 29.0/45 (64.4%) | 27.0/42 (64.3%) | 26.0/42 (61.9%) | 88.0/175 (50.3%) | [42.9,57.7] |
| revised cascade, no gate (first candidate) | repaired browser | 6.0/46 (13.0%) | 29.0/45 (64.4%) | 27.0/42 (64.3%) | 26.0/42 (61.9%) | 88.0/175 (50.3%) | [42.9,57.7] |
| revised cascade, no gate (last candidate) | explicit gold fields | 6.0/46 (13.0%) | 29.0/45 (64.4%) | 27.0/42 (64.3%) | 26.0/42 (61.9%) | 88.0/175 (50.3%) | [42.9,57.7] |
| revised cascade, no gate (last candidate) | repaired browser | 6.0/46 (13.0%) | 29.0/45 (64.4%) | 27.0/42 (64.3%) | 26.0/42 (61.9%) | 88.0/175 (50.3%) | [42.9,57.7] |
| revised hybrid | explicit gold fields | 46.0/46 (100.0%) | 45.0/45 (100.0%) | 42.0/42 (100.0%) | 42.0/42 (100.0%) | 175.0/175 (100.0%) | [100.0,100.0] |
| revised hybrid | repaired browser | 46.0/46 (100.0%) | 45.0/45 (100.0%) | 42.0/42 (100.0%) | 42.0/42 (100.0%) | 175.0/175 (100.0%) | [100.0,100.0] |
| archived template alone | explicit gold fields | 46.0/46 (100.0%) | 45.0/45 (100.0%) | 42.0/42 (100.0%) | 42.0/42 (100.0%) | 175.0/175 (100.0%) | [100.0,100.0] |
| archived template alone | original browser | 33.0/46 (71.7%) | 31.0/45 (68.9%) | 27.0/42 (64.3%) | 27.0/42 (64.3%) | 118.0/175 (67.4%) | [53.7,80.8] |
| archived template alone | repaired browser | 46.0/46 (100.0%) | 45.0/45 (100.0%) | 42.0/42 (100.0%) | 42.0/42 (100.0%) | 175.0/175 (100.0%) | [100.0,100.0] |
| repaired template alone | explicit gold fields | 46.0/46 (100.0%) | 45.0/45 (100.0%) | 42.0/42 (100.0%) | 42.0/42 (100.0%) | 175.0/175 (100.0%) | [100.0,100.0] |
| repaired template alone | repaired browser | 46.0/46 (100.0%) | 45.0/45 (100.0%) | 42.0/42 (100.0%) | 42.0/42 (100.0%) | 175.0/175 (100.0%) | [100.0,100.0] |
| matched one-pass Qwen prompt | explicit gold fields | 5.0/46 (10.9%) | 0.0/45 (0.0%) | 3.0/42 (7.1%) | 0.0/42 (0.0%) | 8.0/175 (4.6%) | [1.7,8.1] |
| matched one-pass Qwen prompt | repaired browser | 5.0/46 (10.9%) | 0.0/45 (0.0%) | 3.0/42 (7.1%) | 0.0/42 (0.0%) | 8.0/175 (4.6%) | [1.7,8.1] |
| archived unconstrained prompt (historical diagnostic) | original browser | 2.0/46 (4.3%) | 1.0/45 (2.2%) | 3.0/42 (7.1%) | 2.0/42 (4.8%) | 8.0/175 (4.6%) | [1.8,7.6] |

| Comparison (A vs B) | Lang | Items | Groups | A-B (pp) | 95% CI | A-only / B-only wins |
|---|---|---|---|---|---|---|
| end-to-end: revised hybrid (browser) vs archived system (browser) | ALL | 175 | 46 | 45.71 | [34.27, 57.39] | 80/0 |
| end-to-end, explicit gold fields: revised hybrid vs archived system | ALL | 175 | 46 | 21.14 | [15.24, 27.17] | 37/0 |
| gate effect: revised hybrid vs same generator without gate/fallback (first candidate) | ALL | 175 | 46 | 49.71 | [42.29, 57.14] | 87/0 |
| gate effect, gold fields | ALL | 175 | 46 | 49.71 | [42.29, 57.14] | 87/0 |
| gate effect, archived system (browser): deployed vs ungated first candidate | ALL | 175 | 46 | 18.29 | [11.86, 25.15] | 33/1 |
| gate effect, archived system (gold): deployed vs ungated first candidate | ALL | 175 | 46 | 37.71 | [29.14, 46.59] | 66/0 |
| revised hybrid vs matched one-pass prompt (browser fields) | ALL | 175 | 46 | 95.43 | [91.91, 98.31] | 167/0 |
| revised hybrid vs matched one-pass prompt (gold fields) | ALL | 175 | 46 | 95.43 | [91.91, 98.31] | 167/0 |
| revised hybrid vs the few-shot realiser alone (LLM-1 stage, no refiner / verifier / gate) | ALL | 175 | 46 | 51.43 | [44.17, 58.76] | 90/0 |
| revised hybrid vs repaired template alone (browser) | ALL | 175 | 46 | 0.0 | [0.0, 0.0] | 0/0 |
| revised hybrid vs repaired template alone (gold) | ALL | 175 | 46 | 0.0 | [0.0, 0.0] | 0/0 |
| repaired template (revised client) vs archived template (original client) | ALL | 175 | 46 | 32.57 | [19.19, 46.29] | 57/0 |
| repaired template vs archived template (gold fields) | ALL | 175 | 46 | 0.0 | [0.0, 0.0] | 0/0 |
| interface effect: revised-browser vs explicit gold fields (hybrid) | ALL | 175 | 46 | 0.0 | [0.0, 0.0] | 0/0 |
| interface effect on the template | ALL | 175 | 46 | 0.0 | [0.0, 0.0] | 0/0 |

Under scorer v2 the repaired hybrid scores 175/175 (browser and explicit fields); the archived system scores 95/175 (browser) and 138/175 (explicit); the archived template given correct fields also scores 175/175 on these simple single-act scenarios, i.e. there the lexical scorer separates systems only through input interpretation, the gate, and the act, not through phrasing. Gate effect on the original 175: repaired hybrid minus the same cascade without gate **+49.7 pp (42.3 to 57.1)**; archived system minus its ungated first candidate +18.3 pp (11.9 to 25.2, browser) and +37.7 pp (29.1 to 46.6, explicit). Hinglish (n = 8, **exploratory**, API payloads because the UI has no code-mix control): repaired hybrid 8/8, archived deployed 4/8 (browser payload) and 5/8 (explicit), unconstrained prompt 0/8 (`T8_codemix_exploratory_legacy.csv`).


## 8. Phase D: human judgments and demonstration checks

**Native-rater packet (blind, randomised): built, human outcomes PENDING.** `reviewer_packet/`: for each of EN, HI, GU, MR two independent rater files (`packet_<lang>_R1/R2.csv`, 30 items each) with neutral output IDs, per-rater item order, exactly half of the items with swapped sides, the selected symbols and the intended message, a meaning rubric asked **before** naturalness (content added, content omitted, polarity and negation scope, act, first-person speaker) and a paired preference with a tie option; `RATER_INSTRUCTIONS.md`, `ADJUDICATION.md`, and the analysis-only key `KEY_DO_NOT_SHARE_WITH_RATERS.csv`. The same 120 holdout scenarios are used for the repaired template and the repaired hybrid; in 88 of them both outputs are the same string (blind controls) and in 32 they differ. `src/analyze_ratings.py` (copy in the packet) reports assigned and rated counts, missing ratings, pre-adjudication agreement, adjudicated outcomes on all pairs and on the prespecified both-preserve-meaning subset, and the agreement of scorer v2 and the gate with adjudicated meaning; with no returned file it writes `results/audit/D_ratings_status.json` = PENDING and invents nothing. A human language review tests meaning and phrasing; it is **not** evidence of AAC usability, which needs a separate target-user study.

**Browser-to-speech path (GTX 1650, 32 UI runs: 1 cold, 31 warm; 4 languages x 4 selections x 2 repeats; `results/audit/B_speech_path.json`).**
* Locale-to-engine mapping (code): backend `IndicF5Engine.generate_speech`: English (not code-mixed) uses the `english_female` reference prompt, hi/gu/mr the `indic_female` prompt; browser fallback `speak()`: en `en-US/en-IN/en-GB`, hi `hi-IN`, gu `gu-IN` then `hi-IN` then `en-IN`, mr `mr-IN` then `hi-IN` then `en-IN`.
* **No IndicF5 checkpoint exists on either machine (gated model), so every locale returned a 440 Hz placeholder tone (32/32 runs); the UI now labels it "Placeholder tone" instead of "IndicF5 Voice". Headless Chrome exposed 0 SpeechSynthesis voices. Speech production in each locale with the real checkpoint or a browser voice is therefore NOT verified.**
* Click to first playback event (audio element `playing`, placeholder tone): median **9.9 s**, p95 **20.8 s** (EN 12.4 s, HI 15.3 s, GU 7.9 s, MR 10.7 s medians; accepted model output 7.9 s, template after rejection 14.2 s); text time dominates, synthesis time about 0 s (placeholder); 0 sentence outcomes without a playback event; system-wide peak GPU memory sampled 1858 MiB (about 1.6 GB for the server). Hardware and software: section 1. The compared path (live HTTP on the PC) is in section 7.6.
* Demo states captured from the real UI (`reviewer_packet/demo_captures/`): `1_successful_render.png`, `2_rejection_and_fallback.png` ("No + Pizza": model rejected, checked template shown with its chip), `3_clarification.png` and `3b_clarification_resolved.png` ("What do you want to say?" with two buttons; no speech), `4_server_unreachable_literal_preview.png` (literal words only, nothing guessed or spoken).

**Reviewer package in a clean environment.** Fresh virtualenv (unpinned `pip install torch transformers fastapi uvicorn scipy pydantic safetensors vocos numpy python-multipart`: torch 2.15.0, transformers 5.22.2, fastapi 0.162.5; newer than the paper's), package = working-tree copy, CPU only: `/api/health` ok; the README's example request and a new-protocol request answered (44 s and 60 s on CPU), a clarification request in 0.01 s, an invalid body returned HTTP 422 (`D_clean_env_test.json`). **Not tested:** first-time download of the Qwen weights (the shared Hugging Face cache was reused), the GPU path in the clean environment, IndicF5 synthesis, the hosted demo. **Links:** no installable download or hosted demo link and no screencast link exists that could be verified (the original repository returned 404 without credentials; the earlier screencast is silent).


## 9. Negative and null results, and material limitations (each stated once)

**Negative or null results (measured).**
1. **The gate does not make the model good; it hides it.** Only 35 of 154 hybrid sentences on the holdout are model outputs (model coverage 21 %); the template supplies 119. The hybrid does not beat the template on any template-covered item (100/100 vs 99/100). With the model alone behind the gate V1 the pipeline's quality is the template's quality.
2. **English model output is unusable as realised** (ungated English 0 to 3.6 %): third-person narration ("The user requested ..."), which the gate now rejects but the archived gate accepted.
3. **The matched one-pass prompt scores 3.6 %** (and 4.6 % on the original 175, equal to the archived unconstrained prompt): this is a statement about zero-shot Qwen2.5-0.5B in these languages, not about one-pass generation in general; a few-shot one-pass comparator was not pre-registered or run (the few-shot realiser alone: 33.0 %).
4. **Repaired template vs archived template: no clear pooled gain under the lexical scorer.** Holdout pooled -4.5 pp (CI -20.5 to 10.7): +7 items on template-covered frames (feeling plus request), -12 on uncovered frames (literal preview against a lexically accepted ungrammatical sentence); legacy 0.0 pp (both 175/175). The gain in phrasing is untested until native raters answer.
5. **Frozen-gate defects** (section 7.4): a Gujarati desire construction rejected, a two-letter form that rejects a valid Gujarati template, bare pronouns counted as state markers; the gate checks concepts, act markers and polarity, not sense ("હું ખરાબ છું." and "હૃદય હું કહું." were accepted under a user-chosen Feeling act).
6. **Template-uncovered frames** end as literal previews by design, so strict success is 4/12 there; one could instead score "safe response" (sentence, clarification or literal preview) which is 112/112 for the hybrid, but that is a different metric and is not used for the headline.
7. **Browser and gold inputs coincide** for the repaired client on all 304 selections (contexts identical): the "interface effect" of the repaired client is 0 by construction, so only the original-client contrast (section 7.3 point 7) is informative.
8. **Not bit-reproducible across GPUs**: 91.4 % of candidates identical (section 7.5).

**Material limitations.**
* **Authorship and circularity.** One assistant session wrote the plan, the fixtures' gold annotation, the client rules, the gate, the templates and the scorer (separate code and tables, same author). No independent curator or annotator exists; the holdout is "fresh" only in the sense that it was generated after the freeze under pre-registered families. Gate-probe results (0 false accepts, 0 false rejects) are synthetic and were used for tuning.
* **Scorer.** Lexical; no grammaticality or sense judgement; lexicon not native-reviewed; scorer v2 was corrected using Phase A findings and regression gaps (it is therefore not independent of the legacy set). The archived and repaired outputs are always scored with the same scorer version in the paired tables; v1 numbers are kept only in the archived report and `B_scorer_effect.csv`.
* **Templates** are not native-reviewed; Gujarati and Marathi constructions (e.g. `મન છે`, `इच्छा आहे`, case forms) are the author's best forms and may be stilted; gender-neutral constructions were preferred.
* **Sample size.** 28 determinate groups; per-language intervals are wide (one language = 28 items); family cells hold 8 to 12 items (flagged sparse); two ambiguous groups only; Hinglish n = 8 (exploratory, no UI path).
* **Hardware and software.** Holdout GPU jobs ran on a TITAN Xp with torch 2.11.0+cu126; the paper's earlier numbers came from a GTX 1650 with cu130; dev streams and the speech check ran on the GTX 1650.
* **Speech.** No IndicF5 weights, no real voices: speech quality, intelligibility and per-locale audibility are unevaluated; click-to-first-playback refers to a placeholder tone.
* **No target-user data.** Nothing here speaks to AAC usability.


## 10. Unresolved gaps, precise dependencies, manuscript sections affected

| # | Gap | Dependency (what exactly is needed) | Manuscript sections affected |
|---|---|---|---|
| 1 | **Native-speaker confirmation of the holdout and dev gold** (concepts, act, polarity, intended meaning, ambiguity target) | Two native speakers per language fill `fixtures/holdout/native_gold_check_<lang>.csv` (and dev); items that change are re-scored with `src/analyze_v2.py`. Until then **no holdout score may appear in the paper** | Evaluation setup and results tables, Abstract numbers, Limitations |
| 2 | **Human ratings, template vs hybrid** (meaning, then naturalness and preference with tie) | Two independent raters per language return `reviewer_packet/packet_<lang>_R1/R2.csv`; adjudication; `src/analyze_ratings.py` | Human evaluation, claim that the hybrid is more natural or clearer (currently untested), Conclusion |
| 3 | **Independent curation** (or at least independent review of rules and gold) | An annotator who did not write the rules; ideally a fresh holdout built by them and scored once with the frozen system | Evaluation setup, Limitations (circularity) |
| 4 | **Fresh holdout for any gate/template repair** | The frozen-gate defects (section 7.4) can be fixed (add the Gujarati desire pattern, drop bare-pronoun state markers, widen two-letter forms) but then the present holdout is spent; a new pre-registered holdout is needed before reporting | System description (gate), Evaluation, Limitations |
| 5 | **Real speech in each locale** | IndicF5 weights (accept the gated-model terms; `x_transformers`), or a browser with Hindi, Gujarati and Marathi voices; rerun `src/speech_and_demo_check.py`; audible screencast | Demo, System description (TTS), screencast, Ethics (voice cloning), the claim "speaks in four languages" |
| 6 | **Installable link, hosted demo, screencast link** | A public location for the package (the original repository is private), a licence file, a re-recorded audible screencast <= 2:30; then a clean GPU install test including the first-time Qwen download | Availability, Demo requirements, Reproducibility checklist |
| 7 | **Few-shot one-pass comparator** | Pre-register and run a one-pass prompt with the realiser's examples on the same inputs | Evaluation (baselines), claim wording about one-pass generation |
| 8 | **Hardware-matched rerun** | Rerun dev and speech/latency on the TITAN Xp, or the holdout on the GTX 1650 (about 3 h), if one machine must appear in the paper | Evaluation setup, Latency statement |
| 9 | **Gujarati / Marathi next-word prediction, HMM-1/2 checkpoints** | LFS objects of the private repository; new predictors; `paper/CLAUDE_WRITTEN/naacl2027_demo/eval/hmm_eval.py` | Prediction table and its claims, System description (prediction) |
| 10 | **Target-user study** | Ethics approval and AAC users or proxies | Claims about AAC usability, Limitations, Ethics |
| 11 | **Code-mixed (Hinglish) client path** | A code-mix control in the UI, otherwise the exploratory rows stay API-only | Evaluation (exploratory), Limitations |

Manuscript edits that follow from verified findings **now** (counts in sections 5 to 7; use only after gap 1): replace "97/175, 132/175, 118/175, 167/175" by the scorer-v2 values and say which scorer; state that the eight Gujarati template-only failures were scorer lexical gaps; report the unrounded prediction gains (+1.126 and +1.190 pp) or the repeat-filtered ones; state the denominator of "27 of 32" (8 feeling symbols x 4 locales); present the gate as a safeguard with its measured false acceptance and false rejection; do not claim that the hybrid improves quality over the template.

## 11. Index of source artifacts

`results/audit/` A1 to A8 (Phase A), `B_scorer_effect*.csv`, `B_scorer_probes_v2.csv`, `B_determinism_check.json`, `B_crosshardware_repro.json`, `B_replay_vs_live_holdout_pc.json`, `B_speech_path.json`, `D_clean_env_test.json`, `D_ratings_status.json`; `results/tables/T1..T8`; `results/scored/*_scored.csv` (one row per scenario, language, input mode, system, seed, stage, with gate reasons and per-criterion flags); `results/streams/` (traces); `results/checks/` (fixture and integrity checks, exit codes); `results/figures/fig_gate_holdout.*` + `fig_gate_source_holdout.csv` + `src/make_figure.py`; `fixtures/` (manifests, pre-registration, overlap logs, native check sheets); `reviewer_packet/`; `patches/`; `config/`; `logs/EXPERIMENT_LOG.md`.

