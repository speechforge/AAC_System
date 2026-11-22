# Claim-evidence map (v3)

| Claim in the paper | Where | Evidence | Status |
|---|---|---|---|
| Client input: success 37% to 55% (65/175 to 97/175); explicit 41% to 75% (71/175 to 132/175) | abstract, Effect of the gate, Table 2 | `eval/results/scored.csv` (recount by `numbers_check.py`) | verified |
| 215/215 concepts kept; no scored polarity error; ungated cascade 175/215 and 185/215 | abstract, Effect of the gate | `scored.csv`; scorer tests presence of a negator, not scope | verified, scoped |
| Gain +18.3 pp (CI 11.9 to 25.2), +34.9 (26.7 to 43.4), +20.0 (12.0 to 28.7); template gaps 20.0 (14.0 to 26.4) and 12.0 (6.4 to 17.9) | Evaluation | `v2/results/audit/A7_paired_ci_recomputed.json` (46 groups, 10,000 resamples) | verified; grouped bootstrap, run after the audit |
| Hindi, Gujarati, Marathi alone +10.1 pp (5.2 to 16.0); English supplies 20 of 33 flips | Effect of the gate | `qa_scripts/extra_checks.py` | verified (own bootstrap) |
| 116 accepted, 57 correct; 40/59 fallbacks; 59 of 110 failing admitted; explicit 71/108 and 61/67 | abstract, Effect of the gate, Conclusion | `scored.csv`; FINAL_CONTEXT section 5 | verified |
| All 33 (client) and 61 (explicit) flips are template sentences | Effect of the gate | `extra_checks.py` | verified |
| Paired against the template: wins 1/loses 22 (client), wins 0/loses 35 (explicit) | Template baseline | `extra_checks.py` | verified |
| First cascade stage alone 63/175 and 67/175 vs 65/175 and 71/175 | Effect of the gate | `scored.csv` (stage `llm1`) | verified |
| Verifier never changed Indic first-stage text (129/129); median 4.63 s | Appendix B | `scored.csv`; `numbers.tex` | verified |
| Client inputs identical to real-page captures (184/184) | Protocol | `v2/results/payloads/original_legacy.jsonl` vs `eval/fixtures/scenarios.jsonl` | verified |
| 27 of 32 feeling selections sent as request; 3 of 272 non-negated selections marked negated | Remaining errors | `v2/results/audit/A6_feeling_denominator.json` | verified |
| Eight template failures are all Gujarati negated feelings (scorer gaps, not native-checked) | Template baseline | `v2/results/audit/A3_*` | verified; classification AI-assisted |
| Failure audit 12/10/9/4 + 2 of 37; 6 and 8 gaps | Appendix B | `A3_failure_classification.csv` | verified; AI-assisted |
| Scorer v2: 97 to 95 (5 gained, 7 lost), 132 to 138, 65 to 63, 71 to 72, 167 to 175; gaps 13.1 and 21.1 pp | Section 5 | `v2/results/audit/B_scorer_effect*.csv`; FINAL_CONTEXT section 5 | verified |
| Repaired pipeline and template 175/175 (regression only); 88/175 cascade without gate; +49.7 pp (42.3 to 57.1); one-pass prompt 8/175 | Section 5 | FINAL_CONTEXT section 7.7 | verified; not a test result |
| Original client sent a wrong act for 59 of 184 scenarios; repaired client 0 | Section 5 | `v2/results/payloads/` captures | verified |
| Table 3: +1.1 pp (381/356 of 2,220), +1.2 pp (659/630 of 2,437); Hindi bigram 24.0 | Table 3, Next-word prediction | `prediction.json`, `v2/results/audit/A8_prediction_counts.csv` | verified |
| Default voice is a Punjabi clip for every language; browser voices only when no server audio; model card lists no English | Section 3, Appendix B | archived `index.html`, `tts.py`; Hugging Face model card (read 2026-11-13) | verified |
| Gate act cues and word lists are English only | Section 3, Limitations | archived `semantic.py` (agents 2, 4, 5) | verified by three agents |
| Vertanen (2026) has none of Hindi, Gujarati, Marathi | Table 3 caption | paper's Table 1 (34 languages; Bengali only) | verified |
| Runtime medians 6.05, 9.75, 7.45, 6.51 s; 12.04 to 18.76 s; 9.9 s median click to playback (31 warm runs; the 95th percentile, 20.8 s, was dropped from the text for space); 44 s CPU; 0.4 ms template | Appendix B | `raw_pipeline.jsonl`; `B_speech_path.json`; `D_clean_env_test.json`; FINAL_CONTEXT 7.6 | verified |
| Code released under Apache-2.0; package and video at the URL | Availability | URL public but stale, no LICENSE | **not yet true** (author action) |
| Placeholder tone scores UTMOS22 1.54 and NISQA 1.12; 8 human prompt clips 2.66 to 4.27 (UTMOS22); default Punjabi prompt 3.83 / 4.74 | Appendix B, Table 8 | `mos_eval/mos_scores.csv` (`score_mos.py`; recount `check_mos.py`); tone regenerated as in `backend/tts.py` (every recorded `audio_b64_len` = 76,860 = 1.2 s at 24 kHz) | verified (computed 2026-11-14) |
| Open MMS-TTS stand-in voices reading the 175 deployed sentences: UTMOS22 4.01 / 3.66 / 3.88 / 3.31 and NISQA 4.39 / 3.52 / 4.91 / 3.95 (EN / HI / GU / MR; n = 46, 45, 42, 42) | Appendix B, Table 8 | `mos_eval/mos_scores.csv`; text identical to `scored.csv` (system `deployed`, cond `ui`) | verified; **describes the stand-in voices, not IndicF5**; English-trained predictors, indicative only; no listening test |
| IndicF5 speech was not scored | Appendix B, Table 8, Limitations, abstract | weights gated; `mos_eval/synth_indicf5.py` refuses to write a clip unless the engine reports real synthesis | verified (author action: accept the terms, run the script) |
