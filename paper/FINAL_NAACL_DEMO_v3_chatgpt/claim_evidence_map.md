# Claim-evidence matrix

| Major claim | Supporting artifact | Numerical evidence | Scope limit | Status |
|---|---|---|---|---|
| Archived browser policy improves cascade | Table 2; archived_summary_v1.json; paired_group_intervals_v1.json | 65/175 to 97/175; +18.29 pp, CI 11.86–25.15 | Combined gate, retry, fallback; archived lexical scorer v1 | Supported |
| Template remains stronger | Table 2; paired_group_intervals_v1.json | 118/175 vs 97/175; policy minus template −12.0 pp, CI −17.94 to −6.40 | Closed archived grid; naturalness unmeasured | Supported |
| All required concepts retained; no scored polarity errors | Table 2; archived_claims_check.csv | 215/215 concept instances; 0/175 polarity errors in both conditions | Lexical matching only; not a semantic guarantee | Supported, bounded |
| Gold fields diagnose input interpretation | Table 2; archived_claims_check.csv | 132/175 gold vs 97/175 browser; wrong acts 17 vs 54 | Gold fields are not measured user selections | Supported |
| Accepted outputs can fail the full scorer | Archived audit; archived_failure_classification.csv | 37/108 accepted fail scorer v1; 6/67 fallbacks fail | Two model failures and six fallbacks are scorer gaps; classifications not native-adjudicated | Supported, bounded |
| Eight Gujarati template errors are scorer gaps | Archived audit; archived_failure_classification.csv | 8/175 gold-field template failures; all Gujarati negated feelings | Scorer-v1 feeling-act lexicon misses નથી; not eight established semantic errors | Supported, bounded |
| Feeling diagnostic denominator is 32 | feeling_denominator.json | 8 symbols × 4 locales = 32; 27 sent as requests | Before exclusions; 30 feeling scenarios remain in primary grid | Supported |
| Repaired hybrid and template satisfy regression | regression_v2.csv; regression_paired_v2.csv | 175/175 each; repaired cascade 88/175; policy gain 49.71 pp, CI 42.29–57.14 | Grid informed repair; scorer v2; no generalization claim | Supported, bounded |
| English prediction gain is count-derived | Table 3; prediction_audit.json | (381−356)/2220 × 100 = 1.126 pp; CI 0.505–1.766 | 60 held-out source conversations; repeated utterances disclosed | Supported |
| Hindi prediction gain is count-derived | Table 3; prediction_audit.json | (659−630)/2437 × 100 = 1.190 pp; CI 0.463–1.922 | Translated synthetic dialogues; no Gujarati/Marathi predictor evidence | Supported |
| Speech-path measurements used tones | speech_path.json | 32/32 placeholder tones; median 9.9 s, p95 20.8 s | Click to playback event; no real speech latency or quality claim | Supported, bounded |
| Examples are recorded and preserve errors | trace_samples.json; Figures 3/4; Table 4 | 24 regression trace excerpts across four languages | Illustrative selection; water includes prompt overlaps; not a new performance sample | Supported, bounded |
