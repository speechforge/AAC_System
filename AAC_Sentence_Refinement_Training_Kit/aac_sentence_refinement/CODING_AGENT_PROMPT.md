# Coding-agent prompt: repair AAC sentence realization and run GPU experiments

You are the implementation owner for an existing Indic generative AAC system.
Inspect the repository, implement the repair, run the available experiments on
the user's GPU, and deliver reproducible evidence. Do not stop at a proposal.
Use the accompanying code as an executable English baseline, not as proof that
the production application is already repaired or that a neural model is trained.

## Inputs and known context

Inputs available with this task:

1. The user's current AAC architecture/context document, copied unchanged into
   `docs/USER_SUPPLIED_SYSTEM_CONTEXT.txt` from the attached `Pasted text.txt`.
2. This complete baseline kit, including `aac_refiner.py`, `prepare_data.py`,
   `train.py`, `evaluate.py`, tests and multilingual plan.
3. The actual AAC repository, GPU environment and existing checkpoints, when
   available on the machine where you execute this prompt.

The architecture document describes a Python 3.10 application, Qwen2.5-0.5B-Instruct
realization/refinement/verification stages, a concept ledger, a semantic validator,
HMM symbol suggestions, and IndicF5/Vocos TTS. Names such as `llm.py`, `semantic.py`,
`hmm.py` and `tts.py` are search hints from the document, not verified repository
paths. Treat latency, zero-error and zero-cloud statements in that document as
unverified descriptions until measured. Do not reproduce them as findings.

Read repository instructions and locate the actual UI-to-TTS route. Inspect how
symbol categories, concept IDs, selected words, intent and grammatical features
are passed to the backend. If no repository is mounted, first run and verify
this standalone kit and list the exact repository/checkpoint dependency. Ask
one focused question only if that missing dependency blocks further integration.

## Problem and research questions

The current symptom is an intent-blind prefix:

```json
{"raw_sentence":"I want Angry with Food",
 "selected_concepts":["Angry","with","Food"],
 "user_intent":"expression_of_emotion"}
```

Required output: `I am angry with the food.`

Verify the source of the universal prefix in the real code. Do not assume a
specific failing function based only on the architecture description.

Answer these research questions:

- RQ1: Does conditioning on selected concepts, intent and semantic roles reduce
  meaning errors relative to repairing only the already flawed raw sentence?
- RQ2: Does task-specific lightweight fine-tuning improve grammaticality and
  adequacy beyond deterministic templates and the current prompted Qwen model?
- RQ3: Does optional online-English denoising adaptation improve the same AAC
  model, or does it cause negative transfer relative to AAC-only fine-tuning?
- RQ4: What quality, coverage, fallback and warm/cold latency tradeoffs arise
  from one-pass generation, hybrid rules and the existing three-stage cascade?
- RQ5, later phase: Can language-tagged native supervision extend the verified
  interface to Hindi, Gujarati and Marathi without losing intent or negation?

## Semantic contract

Continue supporting the existing payload keys:

```json
{"raw_sentence":"Water please", "selected_concepts":["Water","please"],
 "user_intent":"request_object", "language":"en"}
```

Expose `AACRefiner.refine(payload) -> str` and an optional diagnostic method.
The public string output must remain compatible with the current TTS caller.

Use explicit user-selected concepts and role metadata as semantic evidence.
Use compatible structured context next. A prefix invented by the previous
renderer must never become authoritative evidence. Detect conflicts instead of
quietly choosing a convenient interpretation.

Build or extend a language-independent frame containing concept IDs, surface
labels, semantic types, actor, action, theme, recipient, modifiers, relation,
polarity with scope, time, location, quantity, intent and selected politeness.
Each nonempty field must identify the selected concept that supports it.
Do not infer a diagnosis, emotional cause, gender, urgency, eating/drinking action,
new person or new location. First-person AAC should speak as `I`, not narrate
`The user`, unless that speaker perspective was explicitly configured.

Distinguish at least:

- `angry, with, food` → `I am angry with the food.`
- `happy, play, outside` → `I am happy to play outside.`
- `water, please` → `I want water, please.`
- `don't, want, medicine` → `I do not want medicine.`
- `not, happy` → `I am not happy.`
- `want, happy` → `I want to be happy.`
- `cold, water` with object-request metadata → `I want cold water.`
- `mother, give, child, book` without role metadata → preserve raw text; no guessed roles.

A bare object has ambiguous speech-act possibilities. Preserve the established
AAC default of requesting it only if that policy is configured. Keep the policy
explicit and test its disabled mode. A single ambiguous selection must not be
treated as a confident new fact.

## Architecture and repository changes

1. Resolve the frame before choosing a surface template. Fix the prefix at its
   source as well as adding refinement; otherwise malformed drafts keep reappearing.
2. Keep the current HMM predictor and symbol-chip sequence available. Sentence
   realization and next-symbol prediction are separate components.
3. Add a small deterministic fast path for supported unambiguous frames.
4. Add a single-pass local seq2seq realization route with short greedy decoding.
   Reuse `SYSTEM_PROMPT` for a properly chat-templated Qwen prompt-only baseline.
   The T5 route uses the shared `seq2seq_source` prefix during both training and
   inference; do not accidentally train one serialization and serve another.
5. Keep the concept ledger/validator after generation. Validate selected content,
   unsupported content, first-person/role mapping, negation and scope, quantities,
   names, time, location, script and language. Boundary-aware lexical checks alone
   do not prove role preservation; use frame-aware realization and a conservative
   rejection policy. Report both pre-validation model errors and final outputs.
6. On exception, rejection, invalid metadata or timeout, return the original
   `raw_sentence` exactly. Never return an empty explanation or a diagnostic
   string to TTS. On an originally empty raw sentence, retain the existing UI's
   no-utterance handling rather than inventing text.
7. Load once at service startup; cache only validated results, keyed by the
   semantic frame, language, perspective and model version. Do not cache failures.
8. Use a persistent bounded worker or equivalent server cancellation mechanism.
   A Python thread timeout does not stop an in-flight CUDA generation. Limit queue
   wait, token count and total call budget; discard obsolete UI selection revisions.
   Recover a crashed worker outside the interactive request path.
9. Preserve the present API, UI chips, display text and TTS playback. Add concise
   route/rejection/latency diagnostics to existing telemetry, avoiding unnecessary
   raw-user-text logging. Do not change hosting or deployment without task context.

## GPU and model preparation

Detect actual GPU model, compute capability, VRAM, driver, CUDA runtime, PyTorch
version and compatible installed wheel. Run `preflight.py` before downloading or
starting a long job. Use a separate training environment.

Start with pretrained `google/flan-t5-small` for the English experiment; measure
its actual parameter count and memory. Do not train a new language model from
scratch. Compare the existing Qwen checkpoint before replacing it. If the existing
model is already adequate with corrected intent prompting, report that result.

Use FP32 first, batch size 2 and gradient accumulation 4; on 4 GB hardware try
batch size 1 and accumulation 8. Reduce sequence limits only after checking that
no selected concept or reference is truncated. On TITAN Xp/Pascal do not assume
BF16, FlashAttention, current CUDA-wheel support or bitsandbytes compatibility.
If memory fails, record the failure and use smaller batches/checkpointing rather
than deleting examples or silently falling back to CPU.

## Training data and supervision

Build two explicitly separate tasks:

**A. AAC realization supervision.** Input is the selected concepts, intent,
structured roles and a possibly defective raw draft; target is a minimal natural
sentence that expresses those same selections. Include emotion vs object,
request vs statement/question, attributes vs states (`cold water` vs `I feel cold`),
actions vs objects, count/mass nouns, negation, polite requests, urgency only when
selected, actor/recipient distinctions, body locations, names and quantities.
Include conservative copy-raw examples for unresolved ambiguity.

Start with the bundled synthetic pairs for pipeline debugging. Expand with the
actual application's concept inventory and independently human-authored pairs.
Do not train only on outputs from the current failing model. Do not treat
synthetic labels or self-generated verifier verdicts as human ground truth.

**B. Optional general-English fluency adaptation.** Fetch public WikiText using
the exact online dataset/configuration in `prepare_data.py`. Resolve and record
the immutable revision, source rows, filtering, deduplication, article groups and
hashes. Corrupt only grammatical function words in this pilot; preserve polarity,
entities, actions, roles and content order. Give this task its own instruction
and validation data. News/encyclopedic prose is not an AAC intent dataset.

Never randomly shuffle all content words and assume their roles survive. Do not
remove `not`, negative auxiliaries or negation-bearing symbols while making noisy
input. Keep numeric quantities and selected proper names. Do not convert an
unselected contextual detail from a reference sentence into a supposed user fact.

## Splits, observation units and exclusions

Freeze a data split before tuning. Retain the bundled split seed 42 for initial
comparisons. Group all raw-draft corruptions, paraphrases, positive/negative
contrast members and metadata variants of one semantic selection together.
Group online examples by source article. Deduplicate normalized inputs and
targets before splitting. Check cross-split IDs, hashes, targets and group IDs.

Observation unit: one AAC payload, with selection group/user/source document as
the correlation unit where applicable. Evaluate every system on identical payloads
with the same reference set. Report sample and group counts per split, language,
intent and negation condition. Never count repeated drafts as independent users.

Exclude malformed records, unresolved labels and over-length examples only with
an explicit reason and count. For semantic truncation, prefer a hard failure and
repaired input limits. Keep deployment ambiguity/failure cases in evaluation and
count their fallbacks rather than dropping them. Track mixed-language and
out-of-vocabulary examples as separate strata, not hidden exclusions.

Primary English benchmark target: collect 200 independently authored AAC payloads
covering all intent families and at least 50 contrast pairs, subject to available
reviewed data. These are proposed collection targets, not existing samples.
Keep it separate from template-generated debugging data and from prompt tuning.
Use multiple acceptable references and human adequacy judgments when phrasing
varies. If independent labels are unavailable, produce synthetic results with
that limitation and leave human claims pending.

## Minimal experiments and metrics

Run these systems on the same frozen test data:

1. Current flawed renderer/raw output.
2. Corrected deterministic intent templates.
3. Existing Qwen with one-pass intent-aware prompting, if checkpoint is present.
4. FLAN-T5-small fine-tuned on AAC pairs only.
5. The same base model with short online-English denoising, then AAC fine-tuning.
6. Hybrid fast rules + best supported model + validation.

Use seeds 17, 42 and 73 for neural optimization when practical, preserving the data
split. First complete one pilot seed before launching the remaining seeds.
Use identical task-specific update budgets and data for the two FLAN arms; record
the extra adaptation compute. Select checkpoints/hyperparameters on validation,
not by maximizing the final test score. Test general-fluency adaptation as an
ablation; do not assume it is beneficial.

For each system report:

- Reference exact match with numerator and denominator; supplemental only because
  several outputs may be adequate.
- Human grammaticality and semantic adequacy on independently reviewed data, if
  available, with a stated scale and rater/sample counts.
- Intent, actor/recipient, action/theme, relation, entity/attribute, quantity and
  time/location preservation. Define each denominator as the number of test items
  with that selected feature. Separate lexical diagnostic proxies from reviewed
  semantic correctness.
- Negation omission, insertion, inversion and scope errors separately. Omission
  denominator: negated inputs; insertion denominator: nonnegated inputs; scope
  denominator: applicable scope-annotated inputs. The kit's `negation_error` metric
  is only an omission diagnostic and must not be renamed a complete semantic score.
- Unsupported-addition and concept-omission rates per output and per eligible
  selected concept; document the inventory/annotation method.
- Raw fallback and accepted-model coverage over all attempted payloads, with
  timeout/rejection/ambiguity causes. Report failures even when the returned raw
  string happens to equal a reference.
- Warm end-to-end text-module latency in milliseconds: p50, p95, p99, mean and
  maximum. Record cold load/warm-up separately, plus peak allocated GPU VRAM and
  token lengths. Synchronize CUDA for device timing; include queue/IPC/validation
  in user-visible wall time. Do not mix text latency with TTS latency.

For paired method comparisons use cluster bootstrap resampling of whole semantic
selection groups or users, preserving method pairing and contrast pairs. Use
2,000 resamples and seed 42, and report 95% intervals and paired absolute changes.
Report individual optimization seeds and their mean/SD separately; do not treat
training seeds as extra test utterances. When a subgroup has no eligible items,
report its metric as not estimable, not zero. Retain negative and null findings.

## Required validation

Run the provided regression tests and expand them for production input schemas.
Test the four required examples, explicit desire for an emotion, attribute/state
ambiguity, negation scope, emergency words, roles, plural/count/mass nouns, names,
numbers, language/script mismatch, prompt-like text inside concepts, empty inputs,
network/download errors, model-load failure, actual timeout termination, unavailable
GPU, OOM, cache invalidation and concurrent/stale UI requests. Add meaningful tests
for the paths you change; do not replace neural evaluation with mocked success.

Smoke-test a few GPU training updates, finite loss and gradients, checkpoint save,
reload, generation, validation and epoch-level resume before long runs. Compare
training and inference tokenization and serialized source strings. Verify no
cross-split leakage and no silent target/input truncation. Check that displayed
text equals the text sent to TTS for a finalized selection revision.

## Deliverables and execution report

Deliver complete runnable scripts with imports, installation instructions,
configuration, model/dataset revisions, reproducible seeds, checkpoints or their
exact paths, tests and logs. Provide CSV/JSON metric tables, per-example outputs
with rejected candidates, and clear figures for quality vs latency, error types
and fallback coverage. Preserve all negative results.

Write one consolidated `FINAL_CONTEXT.md` containing verified findings only:

- Repository commit, changed modules and actual root cause.
- Research questions answered and unresolved dependencies.
- Data paths, immutable source revisions, output paths and hashes.
- Observation/correlation units, pairing, split/group counts, exclusions and
  denominators by condition/language.
- Model/tokenizer identities, parameter counts, hardware, precision, hyperparameters,
  stopping/checkpoint rules, seeds and executed commands.
- Every reported metric with definition, units, numerator/denominator and uncertainty.
- Pre-validation model errors and final fallback behavior, plus negative findings.
- Human evaluation status and exact limits of synthetic/model-generated data.
- Integration and acceptance-test evidence; remaining gaps and next action.

Do not invent unavailable GPU measurements or independently reviewed samples.
Do not claim that a string validator guarantees zero semantic errors. Complete
the English repair and a measured pilot before optional model-size sweeps or
multilingual expansion. Then follow `docs/MULTILINGUAL_PLAN.md` for staged Indic work.
