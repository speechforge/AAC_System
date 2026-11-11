# Verified evaluation context

Generated from this evaluation invocation only.

- Input: `/home/linux/Documents/AACsystem/AAC_System-jaydeep/AAC_Sentence_Refinement_Training_Kit/aac_sentence_refinement/data/aac_test.jsonl`
- Input SHA256: `08f4c60ad288a48cd026577b539cb87c0032221e1af29fd12e45ba71409f14b2`
- Checkpoint: `runs/seed_42_gpu_max/fluency_then_aac/best`
- Seed for cluster bootstrap: 42
- Figures: exact_match.png; exact_match.svg
- Observation unit: one AAC payload/draft; paired across methods
- Uncertainty: selection group, including all draft and polarity variants; 2000 resamples

| Method | Rows | Groups | Exact match | Raw fallback | p95 latency (ms) |
|---|---:|---:|---:|---:|---:|
| raw | 384 | 40 | 0.0000 | 0.0000 | 0.000 |
| rules | 384 | 40 | 1.0000 | 0.0000 | 0.079 |
| model | 384 | 40 | 0.9870 | 0.0130 | 38.008 |
| hybrid | 384 | 40 | 1.0000 | 0.0000 | 0.079 |

Metric definitions and exact numerators/denominators: `metrics.json` and `metrics.csv`.
Per-payload outputs, rejections and raw model candidates: `predictions.jsonl`.

## Negative findings and gaps

- Template-derived tests share grammar and vocabulary with the implementation.
- Group splitting prevents draft duplication leakage; it does not measure new-user or new-domain generalization.
- Exact match can penalize valid unlisted paraphrases; validator metrics are diagnostics.
- No clinical, conversational-rate, TTS, human-adequacy or real-world safety measurements are produced.
