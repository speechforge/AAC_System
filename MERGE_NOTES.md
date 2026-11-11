# Merge notes

This tree is the merge of two zip snapshots (neither had git history, so each was committed as its own root):

| Branch | Source zip | Contents |
|---|---|---|
| `nov4-v1` | `AAC_System-novelmber_4th_2026_v1.zip` | Google sign-in (Firebase), local-cache personalization, My Words, AI symbol creator, bookmarks, voice cloning, F5-TTS audio playback, accessibility dock, button animations |
| `infinity-gram-fixes` | `AAC_System-aac_infinity_gram_fixex.zip` | ∞-gram engine, offline transliteration, Quick Express, Un-Jumble UI, Delete-Last / Copy, Core-Words row, card-size control, portable paths, memory-safe HMM training |
| `merged` | both | everything above |

`git diff nov4-v1 merged` shows exactly what was brought in from the infinity-gram line, and
`git diff infinity-gram-fixes merged` shows exactly what was brought in from the Nov-4 line.

## How each conflicting file was resolved

**Hand-merged (both sides had real changes)**

| File | Result |
|---|---|
| `indic-generative-aac/frontend/index.html` | Nov-4 file as base + all infinity-gram UI ported in (see below) |
| `indic-generative-aac/backend/app.py` | Nov-4 (voice clone/list/delete, `generate_symbol`, `voice_id`) + infinity-gram (offline transliteration, `hmm_info` ∞-gram stats, cwd-independent static path) |
| `indic-generative-aac/backend/tts.py` | Nov-4 (voice cloning, custom voices) + infinity-gram (portable fallback-prompt search) |
| `README.md` | Nov-4 README + the infinity-gram features, endpoints and corrected checkpoint instructions |

**Took the infinity-gram version** (the Nov-4 copy was only an older / hard-coded-path version of the same file):
`hmm.py` (real Dual-HMM loading + ∞-gram primary engine; Nov-4 had a stub that hard-returned), `llm.py`, `evaluate.py`,
`tests/semantic/evaluate_modes.py`, `indictts/main.py`, `apply_aac_design*.py`, `fix_html.py`, `train_hindi_hmm_dataset.py`,
`translate_dataset.py`, `download_models.sh`, `dual_hmm_streaming_kit/{models_def,monitor_daemon,train_dual_hmm_streaming}.py`,
and `backend/models_def.py` (relative symlink; the Nov-4 one was an absolute path into another machine's home directory).

**Only in infinity-gram, kept:** `backend/infinity_gram.py`, `aac_system_dashboard.html`.

## Judgement calls to review

1. **Settings drawer.** The infinity-gram UI had Speech Speed and High Contrast in the Preferences drawer; the Nov-4 UI moved both into the ♿ Accessibility Dock. Kept them in the dock only (no duplicate controls for the same state). Card Size was added to the drawer *and* the category bar, and is saved in the local cache like the other preferences.
2. **"Top Words:" vs "Quick Picks:".** The infinity-gram UI labelled the top-5 row "Quick Picks:", which now collides with the Nov-4 bookmark shelf of the same name. Kept "Top Words:" for the row and "Quick Picks" for bookmarks.
3. **Page title / favicon.** Kept the Nov-4 "Indic AAC Studio" title and ⚡ favicon (documented in its README).
4. **Inline "Suggestions" strip → ∞-gram shelf.** The Nov-4 inline suggestion pills were replaced by the dedicated ∞-gram shelf; same click behaviour plus probability and the `∞-Ng` badge.
5. **`llm.py` LLM-3 decode** now uses `max_new_tokens=120, temperature=0.0` (infinity-gram side) instead of `220 / 0.01`.
6. **HMM model pickles are Git LFS pointers**, so only one version can live at each path. Kept the infinity-gram side, which matches its pruned-training code. The Nov-4 pointers are still on branch `nov4-v1`:

   | File | kept (infinity-gram) | Nov-4 (on `nov4-v1`) |
   |---|---|---|
   | `dual_hmm_streaming_kit/models/hmm1_nextword_latest.pkl` | `e724fc41a0ef…` 210.6 MB | `706da2cae104…` 1250.3 MB |
   | `dual_hmm_streaming_kit/models/hmm2_unjumble_latest.pkl` | `0fcaaf6c5758…` 816.6 MB | `df7e06a442ae…` 1041.6 MB |
   | `indic-generative-aac/backend/hmm_model.pkl` | `9a5a073e4378…` 816.3 MB | `4cc17e20449e…` 1037.8 MB |
   | `indic-generative-aac/backend/hmm_hindi.pkl` | identical on both sides | |

   The pointers need the real objects on your LFS remote; they are not in the zips.

## Small fixes made while merging

- **Stray "0" in prediction pills.** The ∞-gram shelf used `{pred.order && pred.order >= 4 && …}`; the backend returns `order: 0` ("Prior") for an empty context, and React renders a literal `0`. Every pill on the initial screen showed it. Now `pred.order >= 4 && …` (same for `prob`).
- **Quick Express vs "Replay Voice".** Tapping a Quick Express phrase now clears the cached IndicF5 audio, so *Replay Voice* replays that phrase instead of the previous AI sentence.
- **Un-Jumble** gives newly created tokens an `id` (the strip is keyed by `token.id`).
- **Copy** reports failure (blocked clipboard / insecure context) instead of failing silently.

## Verification performed

- All Python files compile; the JSX compiles with Babel (both parents compile with the same checker).
- Backend smoke test (17 checks): real `app.py` / `hmm.py` / `infinity_gram.py` / `tts.py` with only the heavy `llm` / `semantic` modules stubbed — health, `hmm_info` ∞-gram stats, `predict_next` with `order`, offline transliteration, `unjumble`, voice list / clone / reject-non-audio / delete / refuse-preset-delete, `generate_symbol` (501 without a key), static frontend served independent of cwd.
- Headless Chrome run (39 checks) against the real merged app: every feature from both sides renders and works together, preferences (including card size) and My Words survive a reload, Hindi localisation, no JS runtime errors. The stray-"0" check was confirmed to **fail** on the pre-fix code and pass after.
- Line-level coverage of `index.html`: every line present in either parent but absent from the merge was reviewed (CSS-class variants, replaced layout, or the judgement calls above).

**Not verified:** Google sign-in against live Firebase (needs a real Google account interaction), AI symbol generation (needs `OPENAI_API_KEY`), real IndicF5 synthesis and voice cloning (weights are not in the repo; tested in mock mode), and the LLM pipeline (`llm.py` was not run; it downloads a model).
