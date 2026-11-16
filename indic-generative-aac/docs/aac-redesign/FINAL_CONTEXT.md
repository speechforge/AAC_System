# Indic AAC Studio vNext: Phase 1 progress (slice 1)

Baseline snapshot (before vNext): `../AAC_System_snapshot_v1_stable_2026-11-16/` (+ .zip), 116 files, SHA256SUMS.txt inside.
Backups of the exact pre-change files: scratchpad `index.before-vnext.html`, `app.before-vnext.py`.

## Baseline (recorded)
- Quick Express order: Help, Water, Bathroom, Pain, Food, Thanks, Hello (first four match the spec).
- Board: 69 concept IDs in 9 categories (backend/board_concepts.json). Storage keys: aac_studio_cache_v1, aac_theme_v1, aac_comfort_v1, aac_motion_v1, aac_routine_v1, aac_words_<profile>, aac_photos_<profile>.
- Legacy /generate: returned text + audio_b64 for sentence outcomes (default unchanged).

## Done in slice 1
1. `/generate` accepts `include_audio` (default true, backward compatible). `false` skips TTS (backend/app.py).
2. Composer: **Speak** (strongest filled action, speaks the exact visible text), **Stop audio** (always in place, disabled when idle), secondary **Polish** (text suggestion only, never autoplays). Result panel: **Use suggestion & speak**.
3. Localised labels (hi/gu/mr) for the new controls.
4. Verified in browser (Chrome via Playwright, demo account): controls present, Stop disabled when idle, Polish request carries include_audio:false, no page errors.

## Not done yet (remaining Phase 1)
Stable core-slot anchors and slot IDs; frozen prediction region; language-switch preservation of tokens; polarity/act conflict UI (Angry+Food etc.); offline quick-phrase pack and local audio; 2x2 quick phrases on narrow screens; request-cancellation for Polish vs Quick Express; paired metrics and screenshots; screen-reader test. Backend needs restart to load `include_audio` and the concept predictor.
