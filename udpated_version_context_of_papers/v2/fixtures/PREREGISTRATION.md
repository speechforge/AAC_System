# Pre-registration of the v2 development split and holdout (written before construction)

Written 2026-11-13 (IST), before any holdout scenario existed and before any revised-system output was produced.
Author of the plan, the generator and the system rules: the same assistant session (Claude Code) working for the paper author. **No independent curator was available**, so this document is the substitute: families, counts, sampling rules and the freeze procedure are fixed here and the holdout generator is run only after the system freeze.

## 1. Roles and visibility (who saw what, when)

| Item | Seen by | When |
|---|---|---|
| Legacy 175 scenarios and their archived outputs | assistant, author | before this document; they motivated the repairs (audit Phase A, `results/audit/`). They are **audit and regression cases**, not a clean holdout. |
| Development split (`fixtures/dev/`) | assistant | built first; used to tune the client rules, the gate and the templates; outputs of the archived and revised cascades on it were inspected. |
| System freeze (hash manifest `config/freeze_manifest.json`) | assistant | after tuning, before the holdout generator is executed. |
| Holdout (`fixtures/holdout/`) | assistant (as generator) | generated after the freeze; **no system output on the holdout was inspected before scoring**; no rule was changed afterwards. |
| Native-speaker checks of gold concepts, act, polarity and meaning | nobody yet | pending; fixtures are labelled **DRAFT**; all holdout scores are preliminary and must stay out of the paper until the checks return. |

## 2. Unit of analysis

A *scenario group* is one underlying message defined by concept IDs, communicative act and polarity. Each group is rendered in all four languages (EN, HI, GU, MR) with the board's own localised labels, which gives the per-language item. Translated versions are therefore grouped by construction (bootstrap unit = group).

## 3. Development split (tuning allowed)

21 groups x 4 languages = 84 items. Families: request with two objects (2), request with MORE (2), refusal with new combinations and word order (3), feeling with ME and reordered (2), negated feeling with new positions of the negator (2), action-object or action alone (2), negated action (2), help or call with a person (2), feeling plus request (2), personal vocabulary (1), deliberate ambiguity (1). Dev groups share **no exact concept sequence** with the legacy 175 or with the holdout.
In addition, `fixtures/dev/gate_probes.jsonl` holds hand-written candidate sentences with an accept/reject label per language (right word in the wrong clause, third-person reports, added reasons or times, natural alternate wording, implicit first person, inflected forms). They tune the gate and measure its false acceptances and rejections on synthetic probes only.

## 4. Holdout (frozen system only)

30 groups x 4 languages = 120 items (30 per language). Families and counts fixed here:

| Code | Family | Groups | Template-covered | Note |
|---|---|---|---|---|
| H1 | request with MORE | 2 | yes | new combination |
| H2 | request with two objects | 2 | yes | new combination |
| H3 | refusal (new objects, word order, two objects) | 3 | yes | negation scope, word-order change (negator after the object) |
| H4 | feeling with ME or reordered | 2 | yes | |
| H5 | negated feeling with the negator in a new position | 3 | yes | negation scope, word-order change |
| H6 | action plus object, new combinations | 3 | yes | |
| H7 | negated action | 3 | yes | negation scope |
| H8 | help or call with a person (new persons) | 3 | yes | |
| H9 | feeling plus request (two clauses) | 2 | yes | multi-concept |
| H10 | personal vocabulary (typed word) | 2 | partly | the typed word has no concept ID; frame comes from the other symbol |
| H11 | deliberate ambiguity (clarification target) | 2 | no | gold outcome is clarification; excluded from strict success |
| H12 | template-uncovered frames (go to a place, greeting a person) | 3 | no | no template frame; gold act request or greeting |

Sampling: concept combinations are enumerated by `src/build_fixtures.py` from the board vocabulary under the exclusions of section 5; within each family the generator draws without replacement using `random.Random(20261113)` after sorting the candidate list; where a family has fewer admissible combinations than slots, all are taken. Candidate lists and the draw are logged in `fixtures/holdout/build_log.json`.

## 5. Overlap rules (checked by `src/check_fixtures.py`)

1. No holdout concept sequence equals a legacy or dev concept sequence (exact sequence overlap must be 0).
2. Order-insensitive semantic key (act, polarity, sorted concepts) may coincide with legacy or dev only inside the word-order families (H3, H5) and is then reported item by item.
3. No holdout selection reproduces a few-shot example input string of any prompt (checked per language against the realiser source).
4. Templates are not training references; the one-pass prompt contains no example sentences.

## 6. Systems, inputs, seeds, aggregation (fixed in advance)

* Systems: archived deployed system; matched one-pass Qwen prompt; same cascade with gate and fallback disabled (first candidate and last candidate reported); repaired template alone; repaired hybrid. The archived unconstrained prompt (8/175) is kept as a historical diagnostic only.
* Input modes: browser (real client request captured from the browser for the original and the repaired client); explicit gold fields (diagnostic upper bound for input interpretation); user-selected act (repaired control, ambiguous groups only).
* Seeds: 11, 23, 47 for stochastic paths (English and code-mixed realiser sampling at temperature 0.1). The Indic few-shot path decodes greedily; seeds do not apply and are not counted as repeats.
* Primary metric: strict full-scenario success on determinate scenarios (scorer v2), counted over scenarios; secondary metrics as listed in the task. Missing outputs and timeouts stay in the denominator.
* Paired differences in percentage points; 10,000 bootstrap resamples over scenario groups; bootstrap seed 20261113; all compared systems and seeds travel together inside a resampled group.

## Addendum 1 (2026-11-13, written after the first run of the holdout generator and BEFORE any system output on the holdout was produced or inspected)
The first run of `src/build_fixtures.py holdout` (kept as `fixtures/holdout/scenarios_first_draw_rejected.jsonl`, `build_log_first_draw_rejected.json`) failed the checks of section 5:
(a) three items reproduced a few-shot example input of the revised prompts (gu-H4-02 and mr-H4-02 = ME+HAPPY, hi-H9-02 = SICK+MEDICINE); (b) H4 groups share the order-insensitive semantic key with the legacy single-feeling scenarios
because ME is a speaker marker and not a content concept (every H4 candidate has this property, so rule 2 could not be met by any draw).
Amendments, fixed before any holdout output existed: (1) rule 3 is enforced inside the generator by rejection: candidates whose rendering in any language reproduces a few-shot example input are removed from the candidate list before the seeded draw (the rejected candidates are listed in `build_log.json`);
(2) rule 2 also admits the H4 family (feeling with the ME marker) and lists those items. No system file changed: the freeze manifest was re-written because `build_fixtures.py`, `check_fixtures.py` and this file changed; `config/freeze_manifest_v1_superseded.json` is the first manifest and the hashes of all system files are identical in both.
