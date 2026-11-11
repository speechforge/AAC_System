# Verified evaluation context

Generated from this evaluation invocation only.

- Input: `/workspace/scratch/5768c4da23ce/aac_sentence_refinement/data/regression.jsonl`
- Input SHA256: `2a87a70fb55035424d7b59e3874a52e033e30ec79ec5d5f80fb75674fb24241a`
- Checkpoint: `None`
- Seed for cluster bootstrap: 42
- Figures: exact_match.png; exact_match.svg
- Observation unit: one AAC payload/draft; paired across methods
- Uncertainty: selection group, including all draft and polarity variants; 2000 resamples

| Method | Rows | Groups | Exact match | Raw fallback | p95 latency (ms) |
|---|---:|---:|---:|---:|---:|
| rules | 8 | 8 | 1.0000 | 0.1250 | 0.304 |

Metric definitions and exact numerators/denominators: `metrics.json` and `metrics.csv`.
Per-payload outputs, rejections and raw model candidates: `predictions.jsonl`.

## Negative findings and gaps

- Template-derived tests share grammar and vocabulary with the implementation.
- Group splitting prevents draft duplication leakage; it does not measure new-user or new-domain generalization.
- Exact match can penalize valid unlisted paraphrases; validator metrics are diagnostics.
- No clinical, conversational-rate, TTS, human-adequacy or real-world safety measurements are produced.
