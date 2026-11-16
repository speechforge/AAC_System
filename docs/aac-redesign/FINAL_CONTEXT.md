# Current communicator handoff — 16 November 2026

Base commit: `fe4e185763a181674534656dbf95e30709cf83ff`. Work is uncommitted in a checkout containing other existing changes. This is a partial Phase 1 implementation, subsequently adjusted to restore the previous communicator and its backend logic at the user's request. It is not a completed Phase 1–3 release.

The active route is `http://localhost:8000/`, served from `indic-generative-aac/frontend/index.html`. The active UI is the reference React communicator, not `vnext.jsx`. Login and welcome remain separate routes. The existing backend has been left running; the latest menu/paste changes require no restart.

## Current behavior and relevant paths

- `frontend/index.html`: split draft/intended-message canvas, explicit Speak/Stop/Make sentence, automatic checked-template preview, cancellable playback, Play/Pause on the same Audio instance, and Online/Offline settings. Intent-analysis implementation remains; technical metadata is hidden from the communicator display.
- `frontend/communicator-layout.css`: shared ivory/violet layout and horizontal controls; loaded last. The latest version is `?v=2`.
- `scripts/build_sentence_templates.py`, `frontend/sentence-templates.json`: 1,872 supported previews derived from existing Python templates and validation. Other selections continue through the gated backend; these previews do not imply arbitrary offline generation.
- `frontend/offline-speech.js`: profile-scoped local speech and sentence storage in IndexedDB, public recordings, saved-history controls, explicit Online/Offline modes. Online may generate unseen speech through the backend GPU; Offline uses checked templates and exact installed/saved audio.
- `frontend/aac-sw.js`, `public-assets.json`, `quick-pack.json`, `vnext-media.js`: explicit public-shell/audio provisioning. Pack installation stages and validates assets before changing the active cache. Private API responses are not cached by the service worker.
- Existing account authorization and server endpoints remain authoritative for account data. Offline personal assets require explicit provisioning on the device. Local speech is keyed by profile, locale, and exact text. Sign-out clears the selected offline owner.
- Existing settings include `aac_studio_cache_v1`, `aac_access_v1`, `aac_words_<profile>`, `aac_photos_<profile>`, and shared theme/comfort/motion keys. Local speech is in `indic_aac_offline_v1`.

## Latest requested changes

The Sentence Canvas has a three-dot Message actions menu containing Clear, Delete Last, and Un-Jumble. It closes when the mouse leaves the combined button/popup region, stays open while moving into the popup, and supports touch/click, keyboard activation, Escape, and focus restoration. The primary speech controls remain visible.

Pasting comma-separated text into Type custom word appends separate chips in order in one state update. Whitespace and empty segments are removed. Internal spaces, Indic text, user spelling, and existing tokens are preserved. Known labels retain concept identity. Text surrounding a selected replacement is included correctly. Ordinary paste without a comma remains native text editing. Batch paste does not start competing word pronunciations. ASCII, full-width, and Arabic commas are supported; this input is a simple word list, not a quoted CSV importer.

Latest changed implementation paths: `frontend/index.html`, `frontend/communicator-layout.css`, `frontend/public-assets.json`. Regression: `tests/browser/reference-canvas-paste.cjs`.

## Reproduction and evidence

Run from the checkout root with the existing server on port 8000:

```bash
node indic-generative-aac/tests/browser/reference-canvas-paste.cjs
node indic-generative-aac/tests/browser/reference-modes-layout.cjs
node indic-generative-aac/tests/browser/reference-play-pause.cjs
node indic-generative-aac/tests/browser/reference-offline-pack.cjs
```

Dependencies: `.runtime/browser/node_modules/playwright`, `/usr/bin/google-chrome`, local demo account, real backend/models for speech checks. The clipboard/menu test uses explicit Offline mode and native Chromium clipboard actions; it does not mock speech. The other reference scripts use real Audio playback and real installed recordings/F5 responses. Firebase scripts are blocked in these tests because they use the local account workflow.

Latest verification: clipboard/menu test and modes/layout regression both passed after the latest changes. Play/Pause and full offline-pack tests passed before the latest menu/paste changes. Browser viewports checked by the layout regression: 1440×900, 1280×720, 768×1024, 390×844, 320×568, and 844×390. Clipboard/menu evidence: `evidence/canvas-paste-menu.json` and `evidence/canvas-paste-menu-mobile.png`. Current layout captures: `evidence/final-split-online-offline.png`, `evidence/final-canvas-*.png`.

`evidence/reference-offline-pack.json` records 84 exact local speech pairs (5,693,646 bytes), cold reopening, real local playback, pause/resume, and zero API requests in that scenario. The browser was offline; the backend remained running. This is distinct from the older stopped-backend evidence.

The baseline source capture is `evidence/baseline-source.tar.gz`. `BEFORE_AFTER.html`, `METRICS.md`, and the paired attempt JSON files document an earlier experimental layout, not the final restored reference UI. Their measured timing values must not be presented as final-UI measurements. Those reports define observation counts, exclusions, units, software timing proxies, and bootstrap settings (seed 2026; 2,000 resamples). No human-study or audible-output claim follows from automated replay.

## Demo and remaining gaps

1. Select Gujarati globally, then No and Tea. Verify the visible refusal `મને ચા નથી જોઈતી.` before Speak. Existing Python text/audio checks covered this refusal; native-reader approval is not claimed.
2. Change to Marathi. The original category order and concept registry remain, but category-independent reserved slot identities are not completed in the restored communicator. Do not claim that demo requirement is fulfilled.
3. While online, use Set up offline phrases and wait for completion. Select Offline, reopen, and use an installed quick phrase. Actual cold-reopen/local-audio evidence is in `reference-offline-pack.json`. Do not stop the shared backend for this demonstration. Arbitrary unseen offline speech is unavailable; the exact message remains visible when its audio is missing.

No new physical switch/eye-gaze, platform screen-reader, open on-screen keyboard, audible-onset, or native-reader evaluation was performed. Stable reserved core slots across categories, frozen scanning suggestions, full utterance-onset history accounting, personal board editor/migrations, exchange/import, and research comparisons remain incomplete. Cached quick-phrase timing in the older reports is machine-specific. Offline updates require provisioning the refreshed public assets while online. Existing user tabs need one refresh to load the menu/paste change.

## Backend-only Un-Jumble import — later update, 16 November 2026

At the user's explicit direction, imported only the backend logic from `/home/linux/Downloads/Indic_AAC_Unjumble_Fix/indic-generative-aac`. `backend/word_order.py` and `backend/test_word_order.py` match the downloaded files exactly. `backend/app.py` adds their import, the English-default UnjumbleRequest, and the replacement `/api/unjumble` handler. Existing prediction, generation, auth, offline, and TTS handlers were retained. The current frontend was not replaced or edited: `evidence/unjumble-source-check.json` records unchanged hashes for the inspected GUI files.

The ordering path uses the package's local English help/let rule, then Qwen, then the optional English HMM2 fallback when all input labels are in its vocabulary. Index permutations and repeated labels are validated. The original response fields remain alongside status/order. There is no general semantic or grammatical validation of a model permutation. HMM1 prediction is unchanged.

The nine supplied unit tests passed with `/home/linux/miniconda3/envs/taac_env/bin/python -m unittest -v test_word_order` from `indic-generative-aac/backend`. The backend was restarted once using its original environment and is running on port 8000 with TTS ready. Actual API evidence in `evidence/unjumble-after.json` confirms the nine-word example, even with the current GUI's legacy payload omitting language, returns `the AAC system helps students share their thoughts clearly`. Existing chip casing and labels are retained, so the initial lowercase `the` and missing full stop are preserved in this order-only response.

`node indic-generative-aac/tests/browser/reference-unjumble.cjs` passed through the existing canvas and existing menu against the real backend; it does not fixture the endpoint. Its paste event is an explicit synthetic clipboard fixture. `evidence/unjumble-current-gui.png` shows the result. The real F5 regression `reference-play-pause.cjs` also passed after restart. The old nine-chip API request exceeded its 40-second timeout; this negative observation is retained in `evidence/unjumble-before.json`. The new single example took 2.4 ms at the API in one observation; this is not a latency distribution or a user-performance claim.

Live Qwen limits: the repeated-word/multiword-chip example returned `no_suggestion`, preserving the backend input. Hindi, Gujarati, and Marathi requests returned valid permutations but not the unit fixtures' expected canonical order; these are not native-reviewed grammatical successes. The imported GUI preview, duplicate-chip identity mapping, and stale-request guards were deliberately not applied because the user requested the existing GUI unchanged. The current GUI applies a successful result directly and does not consume the new status/order fields. Its old success toast can still appear for a 200 response with no suggestion, and duplicate chip identities or an edit during an outstanding request remain frontend gaps. The current GUI also omits the requested locale in its Un-Jumble payload; explicit non-English locale routing was tested at the API, not claimed as an end-to-end GUI fix.
