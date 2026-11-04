# Verified evaluation context

Generated from this evaluation invocation only.

- Input: `/home/linux/Documents/AACsystem/AAC_System-jaydeep/AAC_Sentence_Refinement_Training_Kit/aac_sentence_refinement/data/regression.jsonl`
- Input SHA256: `2a87a70fb55035424d7b59e3874a52e033e30ec79ec5d5f80fb75674fb24241a`
- Checkpoint: `runs/seed_42_gpu_max/fluency_then_aac/best`
- Seed for cluster bootstrap: 42
- Figures: exact_match.png; exact_match.svg
- Observation unit: one AAC payload/draft; paired across methods
- Uncertainty: selection group, including all draft and polarity variants; 2000 resamples

| Method | Rows | Groups | Exact match | Raw fallback | p95 latency (ms) |
|---|---:|---:|---:|---:|---:|
| raw | 8 | 8 | 0.1250 | 0.0000 | 0.000 |
| rules | 8 | 8 | 1.0000 | 0.1250 | 0.096 |
| model | 8 | 8 | 0.8750 | 0.2500 | 33.722 |
| hybrid | 8 | 8 | 1.0000 | 0.1250 | 0.087 |

Metric definitions and exact numerators/denominators: `metrics.json` and `metrics.csv`.
Per-payload outputs, rejections and raw model candidates: `predictions.jsonl`.

## Negative findings and gaps

- Template-derived tests share grammar and vocabulary with the implementation.
- Group splitting prevents draft duplication leakage; it does not measure new-user or new-domain generalization.
- Exact match can penalize valid unlisted paraphrases; validator metrics are diagnostics.
- No clinical, conversational-rate, TTS, human-adequacy or real-world safety measurements are produced.
