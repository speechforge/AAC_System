# Local AAC speech setup

Run from `indic-generative-aac/backend` with:

```bash
/home/linux/miniconda3/envs/taac_env/bin/python app.py
```

The normal URL is http://localhost:8000/ (the existing launcher selects 8001 if 8000 is occupied).

English (`en`), Hindi (`hi`), Gujarati (`gu`), and Marathi (`mr`) are exposed by the voice API and language selector. All speech actions, including word taps, quick phrases, replay, and generated sentences, use local neural speech: IndicF5 for Hindi/Gujarati/Marathi and the original English-trained F5-TTS model for English. Browser speech and dummy-tone synthesis have been removed. Model or synthesis errors return an error rather than substitute speech. `/api/tts` accepts `text`, `language`, and an optional matching `voice_id`. `/api/health` and `/api/voice/list` report actual speech readiness.

The engine loads `AI4Bharat-Indic-TTS/checkpoint/model.safetensors` and `vocab.txt` with the local `IndicF5/f5_tts` code and Vocos. It requires the existing `taac_env` environment and cached Vocos model. No fresh gated model download is required.

Hindi and Marathi use the existing Marathi recording (`IndicF5/prompts/MAR_F_WIKI_00001.wav`) with its matching transcript. Gujarati now uses a human Gujarati recording (`backend/reference_audio/gu_fleurs.wav`) and its exact Gujarati transcript from FLEURS. Its source, CC-BY-4.0 attribution and checksum are in `backend/reference_audio/gu_fleurs.json`. This is a human reference recording, not Google TTS. IndicF5 still generates all output locally. Gujarati uses 64 sampling steps, guidance 1.0 and synthesis speed 0.9. Short words receive a minimum synthesis duration. Punjabi, Kannada, Tamil and other unrelated voice presets and the custom voice selection/upload UI are removed. Original upstream sample files are retained as repository assets but never selected by this engine.

Official model documentation: https://github.com/AI4Bharat/IndicF5 . Its inference contract is synthesis text, reference audio and the reference audio transcript; it has no language-ID argument. Hindi and Marathi share Devanagari, so script alone cannot distinguish them: provide actual Hindi or Marathi wording.

Static interface translations are in `indic-generative-aac/frontend/locales.js`. A language switch changes interface labels, symbol labels, known selected board words, predictions and document language, and discards old generated text/audio. User-authored personal names/words are preserved; saved phrases are shown only in their saved language. These are not automatically machine-translated. The existing Roman-to-native input control remains available for typed text.

The existing prediction corpus contains English and Hindi, not trained Gujarati/Marathi language models. Predictions are localized through board concepts and filtered to native script, with board-word suggestions when no suitable prediction exists. This does not create a trained Gujarati/Marathi predictor. Existing HMM pickle files in this checkout are Git LFS pointers; loading them fails and the existing HMM fallback remains in use.

Regression checks:

```bash
cd indic-generative-aac/backend
/home/linux/miniconda3/envs/taac_env/bin/python -m unittest test_tts_contract -v
```

English is available again throughout the UI, generation, prediction and account-storage APIs. English speech uses the original English-trained F5-TTS model and `IndicF5/f5_tts/infer/examples/basic/basic_ref_en.wav` with its exact transcript. Its output metadata is `f5tts`, not `indicf5`. English text is stored in its own Redis language namespace, with the same account isolation as the Indic languages.

See [SPEECH_QUALITY_FIX.md](SPEECH_QUALITY_FIX.md) for the reference/transcript correction, the separate English model setup, ASR sanity-check results and remaining pronunciation limitations.
