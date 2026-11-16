# Automated paired metrics

Software replays only; no AAC-user study, task-cue timing or measured audible onset. All attempted scenarios remain in each denominator. Timeouts/invalid text/missing audio count as failures.

## Visible tile feedback

| Locale | Before successes / attempts | After successes / attempts | Before p95 ms | After p95 ms | Paired mean change ms (95% bootstrap interval) |
|---|---:|---:|---:|---:|---|
| en | 10/10 | 10/10 | 34.0 | 32.2 | -0.0 [-1.3, 1.1] |
| hi | 10/10 | 10/10 | 34.0 | 33.0 | -0.6 [-3.1, 1.3] |
| gu | 10/10 | 10/10 | 34.0 | 32.4 | -0.4 [-4.6, 2.5] |
| mr | 10/10 | 10/10 | 33.1 | 32.4 | 0.6 [-1.5, 2.4] |

Click receipt to second animation frame, warm headless Chromium; same YES tile and viewport, paired by locale/run. 100 ms p95 initial target. This is a rendering-feedback proxy, not time from a human task cue. Bootstrap is over 10 paired automated runs per locale, not participants.

## Exact-word composition tasks

| Locale | Condition | Correct / attempted | Median completed ms | Intentional actions / completed message | Clarifications | Corrections | Timeouts |
|---|---|---:|---:|---:|---:|---:|---:|
| en | before | 4/5 | 136 | 3.2 | 0 | 0 | 1 |
| en | after | 5/5 | 150 | 4.0 | 0 | 0 | 0 |
| hi | before | 5/5 | 102 | 3.0 | 0 | 0 | 0 |
| hi | after | 5/5 | 141 | 4.0 | 0 | 0 | 0 |
| gu | before | 5/5 | 108 | 3.0 | 0 | 0 | 0 |
| gu | after | 5/5 | 128 | 4.0 | 0 | 0 | 0 |
| mr | before | 5/5 | 95 | 3.0 | 0 | 0 | 0 |
| mr | after | 5/5 | 129 | 4.0 | 0 | 0 | 0 |

Five tasks per locale/condition: request, refusal, feeling, question and authored name. Exact selected words or typed text are sent to TTS; TTS response and Audio are fixtures in this comparison. Time is scripted task start to TTS request, not spoken completion. Language/category clicks and explicit commits are counted; typing a whole supplied string is one intentional fill action. This measured reviewed-text workflow deliberately uses a commit action; the repaired direct Speak workflow no longer requires that extra action. See `direct-speak-stop.json` for its real-audio checks; its task latency was not pooled into this earlier reviewed-text comparison. Task times are not evidence of improved user performance. The final captured comparison retains one baseline English-name timeout (Speak stayed disabled) as a failure; the redesigned condition completed all 20 attempts. See the all-attempt timeout sensitivity table below.

## Offline real-audio onset

| Condition | Playback starts / attempted | p95 ms | Max ms | 500 ms p95 target |
|---|---:|---:|---:|---|
| offline-cold-browser | 16/16 | 35.6 | 35.6 | met on this test machine |
| offline-warm | 20/20 | 5.4 | 5.7 | met on this test machine |

“Cold-browser” means one cold browser reopen, then first activation of each of the 16 locale/phrase pairs. Only the first English Help activation is the first utterance after process restart; it is not 16 independent cold browser launches. Warm condition is 20 English Water activations. Browser networking was disabled. The original stopped-backend run remains in `evidence/offline-backend-stopped-metrics.json`. The final repair verification kept the backend running while blocking browser networking; each final raw row records `backend_stopped`. Real WAV decoding, `HTMLMediaElement.playing` event; no audible-output measurement. The separate missing-audio negative test is 0/1 audio success, with correct same-locale readable fallback, and is retained as an audio failure rather than included among the 36 available-pack trials. No paired before-offline estimate exists because the captured build had no equivalent installed public pack; do not infer a causal onset improvement.

## Frozen deterministic realization

| Input mode | Locale | Condition | Overall success / attempted | All concepts | Correct act | Correct polarity | Added-concept failures | Median completed ms |
|---|---|---|---:|---:|---:|---:|---:|---:|
| explicit | en | before | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.308 |
| explicit | en | after | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.309 |
| explicit | hi | before | 54/54 | 54/54 | 54/54 | 54/54 | 0 | 0.278 |
| explicit | hi | after | 54/54 | 54/54 | 54/54 | 54/54 | 0 | 0.281 |
| explicit | gu | before | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.263 |
| explicit | gu | after | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.258 |
| explicit | mr | before | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.272 |
| explicit | mr | after | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.272 |
| explicit | pooled | before | 192/192 | 192/192 | 192/192 | 192/192 | 0 | 0.278 |
| explicit | pooled | after | 192/192 | 192/192 | 192/192 | 192/192 | 0 | 0.279 |
| inferred | en | before | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.312 |
| inferred | en | after | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.311 |
| inferred | hi | before | 54/54 | 54/54 | 54/54 | 54/54 | 0 | 0.284 |
| inferred | hi | after | 54/54 | 54/54 | 54/54 | 54/54 | 0 | 0.282 |
| inferred | gu | before | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.265 |
| inferred | gu | after | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.259 |
| inferred | mr | before | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.272 |
| inferred | mr | after | 46/46 | 46/46 | 46/46 | 46/46 | 0 | 0.277 |
| inferred | pooled | before | 192/192 | 192/192 | 192/192 | 192/192 | 0 | 0.281 |
| inferred | pooled | after | 192/192 | 192/192 | 192/192 | 192/192 | 0 | 0.281 |

192 existing frozen scenarios × explicit/inferred × before/after = 768 attempts. Same deterministic template realizer and heuristic semantic gate; captured vs current pipeline. No model candidates are generated, so this does not compare model-first and template-first performance. Known Hinglish scenarios are retained and can fail; there are no post-hoc exclusions. Gate flags are heuristics, not independently native-reviewed meaning judgments. Overall success requires a complete validated sentence; clarification/literal/failure remain failures for this realization denominator. Completed times exclude unsuccessful attempts but show completion counts. No timeouts occurred.

## Paired realization uncertainty

- explicit: paired success-rate change 0.00 percentage points; 95% paired scenario bootstrap [0.00, 0.00], n=192 scenario pairs. These intervals describe this frozen replay only.
- inferred: paired success-rate change 0.00 percentage points; 95% paired scenario bootstrap [0.00, 0.00], n=192 scenario pairs. These intervals describe this frozen replay only.

## Missing evidence / target scope

- No physical touch/switch/eye-gaze hardware, platform screen reader, native-reader grammar review or AAC-user trials.
- No measured human cue-to-first-correct-symbol latency; no audible output latency; no causal human performance claim.
- Existing model-first vs template-first research comparison, board editor, migration, import/export and scanning remain later phases.
- A failed or unavailable output is preserved in the raw attempt files. No exclusions, seed 2026, 2,000 bootstrap resamples.

## All-attempt timeout sensitivity

| Condition | Attempts | Timeouts | Mean with 30 s timeout penalty, ms | Mean with 60 s timeout penalty, ms |
|---|---:|---:|---:|---:|
| before | 20 | 1 | 1601.8 | 3101.8 |
| after | 20 | 0 | 130.1 | 130.1 |

Reviewed-text task success change: 5.0 percentage points; 95% paired scenario bootstrap [0.0, 15.0], n=20 locale/task pairs. Software contracts only; no AAC-participant inference.
