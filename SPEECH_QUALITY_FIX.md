# Speech intelligibility repair

Open the listening check at http://localhost:8000/static/speech-check.html . It contains fresh audio for English, Hindi, Gujarati and Marathi and can regenerate the same text with the live local models. Playback is fixed at normal speed on this page so it can be compared independently of saved accessibility settings.

## Findings and changes

1. The earlier `MAR_F_HAPPY_00001.wav` reference did **not** say the configured Hampi transcript. Local speech recognition identified a different sentence about diesel prices. Both Hindi and Marathi were conditioned on that mismatched audio/text pair. They now use `MAR_F_WIKI_00001.wav` and the exact transcript published in the [official IndicF5 demo](https://huggingface.co/spaces/ai4bharat/IndicF5/blob/main/app.py).
2. The official IndicF5 language list contains 11 Indic languages and excludes English. Routing English through it produced garbled output despite valid WAV files. English now uses the original [SWivid/F5-TTS English-trained base checkpoint](https://huggingface.co/SWivid/F5-TTS), with its own vocabulary and the matching English reference. This runs locally; it is not Google TTS or browser speech. API audio metadata reports `f5tts` for English and `indicf5` for Indic speech. English model assets are in `.runtime/models/f5-english`; the model publisher specifies CC-BY-NC-4.0.
3. Gujarati retains its human Gujarati FLEURS reference and matching transcript. A controlled comparison of guidance strengths 1, 2, 3 and 4 on the same sentence found 1 more accurate than the prior 2; the configured value is now 1.0, with 64 sampling steps.
4. Short AAC words receive a minimum synthesis duration rather than being compressed into a fraction of a second. This changes model sampling duration, rather than slowing an already distorted waveform.
5. Output has RMS level control, a capped amplification gain, PCM headroom and short fades. Arbitrarily quiet decoder output is no longer boosted to full scale. Saved legacy playback speeds reset once to normal speed; current speeds are bounded and preserve pitch.
6. The official IndicF5 weights and vocabulary were verified against the publisher's hashes. All 364 acoustic and 83 vocoder tensors load strictly, and all 364 English acoustic tensors load strictly. No unexpected tensors are silently ignored. The current mel filterbank matches the checkpoint exactly; the installed rotary implementation matches the legacy positional frequencies exactly. Experimental changes to attention layout worsened output and were **not** applied.

## Evidence and limits

The previous checks established only model readiness and valid non-empty WAV audio. Those checks were insufficient to establish intelligibility. A locally downloaded Whisper-large-v3-turbo recognizer was used to transcribe the before/after samples independently of browser playback.

For four short sanity-check sentences, punctuation/spacing-normalized character error rates changed as follows:

| Language | Before | After |
| --- | ---: | ---: |
| English | 0.516 | 0.000 |
| Hindi | 0.600 | 0.086 |
| Gujarati | 1.289 | 0.211 |
| Marathi | 0.441 | 0.118 |

CER can exceed 1 because of inserted characters. These are four diagnostic samples, not a held-out benchmark or a human naturalness assessment. ASR itself has accent, spelling and script errors. Remaining pronunciation differences are visible in the transcripts; these results do not establish perfect native-speaker quality.

All generated audio is 24 kHz PCM. The detailed expected text and before/after transcripts are in `.runtime/reports/speech-quality/comparison.json`.

## Setup and regression checks

The existing IndicF5 checkpoint remains in `AI4Bharat-Indic-TTS/checkpoint`. To prepare the separate English model on another checkout:

```bash
/home/linux/miniconda3/envs/taac_env/bin/python indic-generative-aac/scripts/setup_speech_models.py
```

Speech regression tests:

```bash
/home/linux/miniconda3/envs/taac_env/bin/python -m unittest discover -s indic-generative-aac/backend -p test_tts_contract.py -v
```

Optional ASR-assisted sanity check (the ASR model is only a test tool and is not loaded by the app):

```bash
/home/linux/miniconda3/envs/taac_env/bin/python indic-generative-aac/tests/check_speech_intelligibility.py --download-asr
```

All test tools, downloads, samples and logs reside inside this checkout. Google/guest session storage and the Redis database remain separate from speech synthesis.
