# Indic AAC Studio, NAACL 2027 demo (v2): claim-evidence map and self-review

Editorial file; none of it belongs in the manuscript. "Recomputed" means I recomputed it from raw files on 2026-11-12 independently of the generated number macros; "from v1" means the value comes from the generated macros of the frozen evaluation and I did not recompute it.
Evidence root: `paper/CLAUDE_WRITTEN/naacl2027_demo/eval/` (`results/scored.csv`, `raw_pipeline.jsonl`, `summary.json`, `prediction.json`, `hmm_eval.json`, `refiner_repro.json`, `ui_audit.json`, `reliability_ui.json`, `fixtures/scenarios.jsonl`).

## 1. Claim-evidence matrix

| # | Claim in v2 (where) | Table / figure | Numerical evidence | Status |
|---|---|---|---|---|
| 1 | The gate raises success from 41% to 75% with explicit fields and from 37% to 55% with client-inferred fields (Abstract, Sec. 4 RQ1) | Table 2 | 71/175 to 132/175; 65/175 to 97/175 | **Recomputed**, all cells of Table 2 match `scored.csv` (primary rows, per language and pooled) |
| 2 | The gate keeps all 215 required concepts; the ungated cascade keeps 81-86% (Abstract, RQ1) | Table 2, Kept | 215/215; 175/215 (client) and 185/215 (explicit); unconstrained 199/215 | **Recomputed** from per-scenario retention weighted by concept count. Holds partly by construction because the template echoes the labels (Sec. 4 RQ3 says so) |
| 3 | The cascade makes 36/175 polarity errors with explicit fields (35 dropped negations, 1 spurious); the gate leaves 0/175 (Abstract, Intro, RQ1) | Table 2 | 36 to 0; client 2 to 0 | **Recomputed** (counts); the 35/1 split is from v1 |
| 4 | One unconstrained prompt of the same model succeeds on 8/175 (Abstract, Intro) | Table 2 | 8/175 (5%) | **Recomputed**; one prompt, one 0.5B model, stated |
| 5 | A template alone reaches 167/175 (explicit) and 118/175 (client) and is ahead of the pipeline except Hindi under client payloads (Abstract, RQ3, Conclusion) | Table 2; Sec. 4 | 167/175, 118/175; paired differences -28, -9, -19, -24 pp (explicit) | **Recomputed** counts; CIs from v1 |
| 6 | With explicit fields the gate lets model text through for 108/175; 71/108 accepted outputs are fully correct, 61/67 fallbacks correct (RQ1) | Sec. 4 | 108, 71, 67, 61 (client: 116, 57, 59, 40) | **Recomputed** from the `fallback` and `success` columns |
| 7 | Explicit fields cut wrong-act outputs from 54/175 to 17/175 (Intro, RQ2) | Table 2 | 54 to 17 | **Recomputed** |
| 8 | The client marks 27/32 feelings as requests and 3/276 single-symbol selections as negated (RQ2) | Sec. 4 | 27, 3, 276 | **Recomputed** from `ui_audit.json` summary |
| 9 | Three recorded requests (Fig. 1): "I need food." rejected for a missing concept; the Marathi "I want water" rejected for negation mismatch; the "Tired" sentence accepted although third-person with added content | Fig. 1 (page 2), Appendix Fig. 4 | verdicts: concept match false (score 0.70); negation match false (0.80); all checks pass (1.00) | **Recomputed** by running the deployed validator on the recorded candidates |
| 10 | Suffix trie beats trigram backoff by +1.1 pp (EN) and +1.2 pp (HI) hit@1 (Abstract, RQ4) | Table 3 | 17.2 vs 16.0; 27.0 vs 25.9; CIs [+0.5, +1.8], [+0.5, +1.9] | From v1; the ChatGPT draft's separate pipeline reports 1.13 [0.49, 1.76] and 1.19 [0.47, 1.93] (independent corroboration). Effect is small and stated so |
| 11 | Gutenberg HMM 6.7% and Hindi HMM 24.5% hit@1; no inference about in-domain training (RQ4) | Table 3 | 6.7, 24.5 against trigram 16.0 / 25.9 and trie 17.2 / 27.0 | **Checked** against `hmm_eval.json`; M2 and M3 of the review corrected |
| 12 | Latency medians 6.05 / 9.75 / 7.45 / 6.51 s accepted; 12.04-18.76 s fallbacks; 283 requests; GTX 1650 (RQ4) | Sec. 4 | as listed | From v1 (`summary.json`); speech synthesis excluded, stated |
| 13 | Cold start 10.2 s, first request 13.94 s; only outbound attempt was the optional transliteration service (RQ4) | Sec. 4 | as listed | From v1 (`offline_summary.json`) |
| 14 | Trained components (flan-T5-small 76,961,152 parameters, 960 updates, 378/384, 0 negation errors in 172; HMM sizes; trie 15,505 sentences, depth 181) (Table 5, Appendix C) | Table 5 | as listed | HMM sizes **checked** against `hmm_eval.json`; refiner and trie from v1 (`refiner_repro.json`, `FINAL_CONTEXT.md`) |
| 15 | Interface probes: Enter and Space select a focused card; emulated tap selects; no live region; no explicit labels; blank page without external hosts (Limitations) | Sec. 5 | 0 live regions; 0 label attributes; 0 visible characters with hosts blocked | **Checked** in `reliability_ui.json`. The "focus does not reach symbol cards" flag is a probe artifact (exact text match against emoji-prefixed text) and is **not** claimed |
| 16 | Speech synthesis is integrated but was not evaluated; speech quality not assessed (Abstract, Limitations) | none | evaluation ran in placeholder mode | Supported (`env.json`, `FINAL_CONTEXT.md` section 6) |
| 17 | HMM-1 and HMM-2 are trained components that the evaluated build ran without (Sec. 3, Limitations) | Table 5 | checkpoint objects absent (Git LFS pointers) | Supported; they remain unevaluated |
| 18 | Related-work capabilities, "documented" only (Table 1) | Table 1 | vendor pages and papers read 2026-11-12 | From v1; **not re-read** here; scoped by `n.s.` |
| 19 | India, Census 2011: 26.8 million persons with disabilities, 2.21% (Intro) | none | secondary source (news article) | Supported by a secondary source; the PIB release returned 403 to my fetch; replace with the primary entry |
| 20 | Code released under the stated licence at the stated URL; screencast provided (Abstract, Sec. 5) | none | release statement only | **Needs action**: URL private (404), no licence file, screencast silent |

## 2. Adversarial self-review (five dimensions)

**Contribution.** *Is this an API wrapper around Qwen and IndicF5?* The paper uses both as released and says so; the contribution is the selection contract (ledger, four-part gate, retry, template floor) behind an interface that carries intent and polarity, trained predictors, a four-language demo, and a frozen paired protocol that also reports where the design fails. Residual risk: the gate is lexical and modest; v2 does not claim fluency gains.

**Writing clarity.** *Can a reader restate the paper after page 2?* Fig. 1 shows the whole story on three real requests (two caught, one missed); terms (ledger, gate, template floor, client versus explicit) are defined once. Coding vocabulary is gone from text and figures.

**Experimental strength.** *Are baselines fair?* Literal join, unconstrained prompt, pre-gate cascade (the same response as the deployed output), deployed, template-only, one frozen set, paired bootstrap. The template's lead is reported in the abstract, RQ3 and the Conclusion. Residual risks: one small model, one unconstrained prompt, single samples for English and code-mixed output, a lexical scorer written by the authoring assistant and not native-reviewed.

**Evaluation completeness.** *Does it answer the demo-track questions?* Faithfulness, error origin, template comparison, prediction, latency, offline operation, probes. Missing and stated: user study, native-speaker ratings, speech quality, HMM-1/HMM-2, screen readers.

**Method soundness.** *Does the gate guarantee correctness?* No; it checks concepts, polarity and limited intent cues. The paper reports a miss (Fig. 1 row 3), the unvalidated fallback, English-only intent test, and the client's intent defects.

## 3. Rebuttal readiness (short answers)
- *Closest prior work and delta?* Compansion and recent LLM-based AAC systems expand text or abbreviations; none of the sources read documents a deterministic concept-and-polarity check for Indian-language symbol boards (scoped claim).
- *Why is the template not the contribution?* It is the floor the gate falls back to; the gate decides when model text may replace it. Whether model text is better than the template is not measured; the paper says that.
- *Which result supports the central claim?* Table 2, rows "Cascade before gate" against "deployed".
- *Failure case?* Fig. 1 row 3; RQ2 defects.
- *Real but non-invalidating limitation?* Lexical scorer; no user study.
