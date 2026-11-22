# Claim–evidence map — ChatGPT Version 3

| Major claim in manuscript | Figure/table and source artifact | Numerical evidence | Scope / status |
|---|---|---|---|
| Archived web policy improves its cascade, below template | Table 2 A; A1_claims_check.csv; A7_paired_ci_recomputed.json | 65/175 → 97/175; template 118/175; +18.29 pp [11.86,25.15]; −12.00 pp [−17.94,−6.40] | Supported — archived lexical scorer, joint gate/retry/fallback effect |
| Retention and polarity alone do not establish scenario success | A1_claims_check.csv; original scored.csv | 215/215 concepts; 0 polarity errors; 54 wrong act; 4 added; 10 off-task (web) | Supported — overlapping lexical diagnostics, 175 scenarios |
| Explicit fields are a diagnostic, not the deployed browser path | Table 2 B; A1 and A7 | 71/175 → 132/175; template 167/175; +34.86 pp [26.70,43.41] | Supported — original gold-field condition |
| Accepted output can fail independent scoring | A1_claims_check.csv; A3_failure_classification.csv | 37/108 accepted model failures; 6/67 fallback failures | Supported — v1 criterion, not native judgments |
| Feeling-selection denominator differs from evaluated family size | A6_feeling_denominator.json | 27/32 selections; 8 symbols × 4 locales; 3/276 false-negation probes | Supported — separate isolated-label diagnostic before exclusions |
| Gujarati eight template failures were scorer lexical gaps | A3_failure_classification.csv; A3_classification_summary.json | 8/8 template-only and 6/6 fallback failures categorized as scorer gaps | Supported — assistant diagnostic, native review pending |
| Revised hybrid equals repaired template on regression | Table 2 C; T1_success_legacy.csv; T2_paired_legacy.csv | 175/175 each; ungated 88/175; joint policy +49.71 pp [42.29,57.14] | Supported — regression only; cases informed repairs; scorer v2 |
| Prediction has 60 held-out source conversations out of 300 per language | archived_prediction.json; predict_eval.py | 240 train / 60 test; 2220 EN, 2437 HI contexts | Supported — context and conversation denominators kept distinct |
| Trie hit@1 exceeds trigram on the evaluated split | Table 3; A8_prediction_counts.csv; A8_prediction_audit.json | EN 381−356=25/2220, +1.126 pp; HI 659−630=29/2437, +1.190 pp | Supported — group-bootstrap uncertainty reported in text |
| Gujarati/Marathi prediction not evaluated | Table 3; evidence handoff GAPS.md | No matched scores | Bounded — dashes and explicit coverage, no invented scores |
| Playback audit is a test-tone audit | B_speech_path.json | 32/32 test tones, 31 warm; median 9949 ms, p95 20769 ms | Supported — audio-element playback event, not audible speech |
| Native-validated holdout/naturalness and target-user outcomes absent | D_ratings_status.json; WHAT_RAN.md; GAPS.md | 0 returned rating files | Bounded — no holdout score or preference claim included |
| Figure 4 and appendix preserve recorded language outputs | figure4_traces.json; appendix_cases.json; assets.source.json | Eight phase traces, 24 family/language examples | Supported — exact recorded strings, grammar not silently repaired |
| Public demo/download and project release licence unverified | D_clean_env_test.json; GAPS.md | No verified public release/video | Bounded — removed release and open-source claims |
