# CONTEXT — Indic & English Generative AAC System (merged tree)

Single source of context for this repository. Written 2026-11-11 against branch `merged` (commit `fe4e185`).
Everything here was checked against the code in this tree unless it is marked **(claim)** — a figure or statement taken from an older doc that this tree does not back up.

---

## 1. What this is

An Augmentative & Alternative Communication (AAC) web app for people who communicate with symbol grids. The user taps symbols (words/emojis); the system predicts next words, turns the telegraphic selection into one natural sentence in **English, Hindi, Gujarati or Marathi (plus code-mixed Hinglish)**, checks that sentence for hallucinated content / dropped negation, and speaks it with zero-shot voice TTS.

Target venue/context: a demo-track system paper (baseline: Francis et al., Interspeech 2025 — `francis25_interspeech.pdf`; English-only baseline app in `baseline_english_system_demo/`).

Core ideas:
1. **Constrain the LLM, don't trust it** — a 3-stage Qwen cascade is wrapped by a *deterministic* validator and a rule-based fallback.
2. **Fast prediction without a GPU** — an ∞-gram suffix-trie (primary) over a legacy n-gram HMM (fallback).
3. **Voice identity** — IndicF5 flow-matching TTS with reference-clip voice cloning.

## 2. Provenance: how this tree was made

Two independent zip snapshots (no shared git history) were merged on 2026-11-11:

| Branch | Snapshot | Brought |
|---|---|---|
| `nov4-v1` (`a8f64b9`) | `AAC_System-novelmber_4th_2026_v1` | Google sign-in + Firestore sync, localStorage cache, My Words grid, AI symbol creator, bookmarked Quick Picks, voice cloning/presets, F5-TTS playback, ♿ Accessibility Dock, button animations |
| `infinity-gram-fixes` (`331d701`) | `AAC_System-aac_infinity_gram_fixex` | ∞-gram engine, offline transliteration, Quick Express, Un-Jumble UI, Delete-Last/Copy, Universal Core Words row, card-size control, portable paths, memory-safe Dual-HMM training |
| `merged` (`fe4e185`, current) | both | all of the above |

Hand-merged: `frontend/index.html`, `backend/app.py`, `backend/tts.py`, `README.md`. Every other conflict took the infinity-gram version (the Nov-4 copy was an older/hard-coded-path variant). Full per-file decisions, six judgement calls and the verification log are in **`MERGE_NOTES.md`** — read that before reverting anything.
`git diff nov4-v1 merged` / `git diff infinity-gram-fixes merged` show what each side contributed.

## 3. Repository map

| Path | What it is | Status |
|---|---|---|
| `indic-generative-aac/` | **The application.** `backend/` (FastAPI), `frontend/` (single-page UI), `evaluation/`, `tests/semantic/`, `experiments/`, `scripts/`, plus older design docs | Active |
| `dual_hmm_streaming_kit/` | Trainer + models for HMM-1 (next-word 4-gram) and HMM-2 (un-jumble); `models_def.py` is shared with the backend via symlink | Active |
| `AAC_Sentence_Refinement_Training_Kit/` | Standalone flan-t5-small sentence-refinement experiment (rules + seq2seq hybrid) with executed GPU results | **Not wired into the app** (nothing imports `aac_refiner`) |
| `IndicF5/` | Vendored AI4Bharat IndicF5 package (`f5_tts`) + reference voice prompts in `prompts/` (KAN/MAR/PAN/TAM wavs) | Active (TTS) |
| `AI4Bharat-Indic-TTS/` | Legacy FastPitch Indic-TTS repo; also the *expected location of IndicF5 weights* (`checkpoint/`) | Legacy, but path still used |
| `indic-generative-aac/indictts/` | Near-duplicate of `AI4Bharat-Indic-TTS/` (only `main.py` differs; infinity-gram copy kept) | Legacy |
| `english_AAC_Dataset/`, `hindi_AAC_Dataset/` | 15 English + 6 Hindi JSONL files × 100 rows each (May 2025 batches): synthetic caregiver↔AAC-user conversations (`utterance`, `utterance_intended`, `is_aac_user`); the English set also holds OpenAI batch request/metadata files. The Hindi set mirrors the English batches (`translate_dataset.py` is the opus-mt translation script). **`*.jsonl` in both folders feed the ∞-gram engine at startup** | Data |
| `baseline_english_system_demo/AIImageAAC/` | English baseline: React Native / Expo 52 app (`app/index.tsx`) | Reference only |
| `aac_system_dashboard.html` | Standalone static architecture/audit dashboard (self-audit of bugs and fixes) | Reference |
| `PROJECT_PROPOSAL_CONTEXT.md` | Proposal/grant narrative, RQs, novelty claims, mermaid architecture (identical copy in `indic-generative-aac/`) | See §11 — numbers are claims |
| `README.md`, `MERGE_NOTES.md`, `run.sh` | User-facing README, merge log, launcher | Current |
| Root `*.py` helpers | `train_hindi_hmm_dataset.py` (builds `hmm_hindi.pkl`), `translate_dataset.py` (opus-mt-en-hi), `gen_emojis.py` (writes `all_emojis.js`), `apply_aac_design*.py` + `fix_html.py` (one-shot restyles of the legacy `index_new.html`), `update_html*.py` (old one-shot patches, hard-coded to another machine's path — will fail here) | Mostly one-shot |

## 4. Runtime architecture

```
Browser (index.html, React 18 UMD + Babel-standalone + Tailwind CDN + Firebase compat)
  │  fetch()                                   ┌──────────── localStorage `aac_studio_cache_v1`
  ▼                                            │             (prefs, My Words, bookmarks, symbolStyle, cardSize…)
FastAPI  backend/app.py  (0.0.0.0, port 8000 → 8001 if 8000 busy, or $PORT; also serves ../frontend statically)
  ├─ /predict_next ─► hmm.AACHMM.predict_next ─► infinity_gram (primary) ─► n-gram Markov (fallback)
  ├─ /api/unjumble ─► hmm.unjumble ─► HMM-2 (dual_hmm_streaming_kit/models/hmm2_unjumble_latest.pkl)
  ├─ /api/transliterate ─► offline word map ─► Google Input Tools (0.8 s timeout) ─► passthrough
  ├─ /api/voice/{list,clone,DELETE} ─► tts.IndicF5Engine
  ├─ /api/generate_symbol ─► OpenAI Images API (needs OPENAI_API_KEY)
  └─ /generate  ─► llm.generate_sentence ─► semantic.validate ─► [fallback] ─► tts.generate_speech ─► base64 WAV
```

### `/generate` pipeline (`app.py:285`, `llm.py:688`)
1. Build a canonical context from the request (`intent, actor, entities, attributes, relations, temporal_state, location, people, actions, negation, speaker_role` + `language`, `code_mix`, `generation_mode`, `voice_id`). `negation` is also forced true when the intent is `NEGATION` or contains `NOT`.
2. `IndicLLM.build_structured_context` → `build_concept_ledger` (required / forbidden concept sets).
3. **LLM-1 Realizer** (Qwen2.5-0.5B-Instruct) → minimal sentence. `generation_mode == "single"` stops here (LLM-3 skipped, reported as `edit_type: single_fast`).
4. **LLM-2 Refiner** (dual mode only) → strips unsupported concepts.
5. **LLM-3 Verifier/Arbiter** → JSON verdict (`PASS`/`REFINE`/`REJECT`) + minimal rewrite; decode `max_new_tokens=120, temperature=0.0`.
6. **`SemanticValidator.validate`** (`semantic.py`) — purely deterministic (no LLM call, despite older docs): negation-word match, entity substring/Indic-stem match, forbidden-concept regex, unrequested-temporal-word regex, simple intent checks → score + hard gate. Up to **2 attempts** (`MAX_RETRIES = 2`; the comment in `app.py` saying 1 is stale).
7. If both fail → `llm.generate_deterministic_fallback` (template from the user's own concepts). **The fallback is marked valid unconditionally** (`app.py:359`) — it is not required to pass the validator.
8. `tts.generate_speech` (24 kHz) → base64 WAV in `audio_b64`; response also carries `ledger`, `candidate_llm1/2`, `llm3_decision`, `caregiver_context`, `fallback_used` and a `metrics` latency block.

Authority order used in prompts: User selection ≻ structured context ≻ concept ledger ≻ hard constraints ≻ LLM-3 ≻ LLM-2 ≻ LLM-1.

### Backend modules (`indic-generative-aac/backend/`)
| File | Role |
|---|---|
| `app.py` | Routes, CORS `*`, static mount. **Constructs `IndicLLM()` and `IndicTTSEngine()` at import**, so startup needs torch/transformers and Qwen weights (local `../models/Qwen2.5-0.5B-Instruct` if present, else downloads `Qwen/Qwen2.5-0.5B-Instruct`). |
| `llm.py` (748 lines) | `IndicLLM`: context/ledger builders, 3-stage cascade, deterministic fallback, `parse_and_repair_context` (caregiver view). |
| `semantic.py` | `SemanticValidator` (above). |
| `hmm.py` | `AACHMM` (`hmm_engine` singleton). Loads `hmm_hindi.pkl`, Dual-HMM-1 (4-gram → mapped into tri/bi/uni stores) and HMM-2 from the dual kit; falls back to a small built-in English vocab. `predict_next` tries ∞-gram first. `/api/hmm_reload` re-trains/reloads. |
| `infinity_gram.py` | `AACInfinityGramEngine` (`infinity_gram_engine` singleton): arbitrary-depth suffix trie, backoff α = 0.4, EN + HI roots, emoji attached per word. Builds at import from the seed corpora + `english_AAC_Dataset/*.jsonl` + `hindi_AAC_Dataset/*.jsonl`. **Measured here:** 15,505 sentences, 112,875 tokens, max depth 181, EN vocab 2,228, HI vocab 2,596, init ≈ 450 ms. Each prediction returns `word, prob, emoji, order, order_label` (`order 0` = "Prior" for empty context — the UI must not render it as text; this was a merge bug fixed in `fe4e185`). |
| `tts.py` | `IndicF5Engine` (aliased `IndicTTSEngine`): preset voices `indic_female`, `english_female`; `register_custom_voice` (needs reference audio **and its exact transcript**); 24 kHz; **mock audio when weights are absent**; fallback-prompt search is portable but still lists a stale `/media/linux/ShreejiPers1/…` candidate. |
| `segmentation.py` | Script-based segmentation + crossfade stitching for code-mixed speech. |
| `models_def.py` | Symlink → `../../dual_hmm_streaming_kit/models_def.py`. |
| `train_hmm_large.py`, `build_large_hmm.py` | Build the Gutenberg English n-gram `hmm_model.pkl` (188,402 sentences, 24 books, 63,783 bigram / 713,845 trigram states **per older docs**). `build_large_hmm.py` has a hard-coded foreign path. |
| `evaluate.py`, `test_llm.py`, `test_tts.py`, `keep_alive.sh`, `start_server.sh` | Eval helpers, smoke scripts, auto-restart loop (hard-coded `PYTHON_BIN`). |

### API surface
| Endpoint | Purpose |
|---|---|
| `POST /generate` | Full pipeline (above) |
| `POST /predict_next` | `{context | current_words, language}` → top-10 `{word, prob, emoji, order, order_label}` |
| `POST /api/unjumble` | Re-order words with HMM-2 → `{jumbled, unjumbled, score, sentence}` (returns input order if HMM-2 not loaded) |
| `POST /api/transliterate` | Roman → Devanagari/Gujarati/Marathi; response has `source`: `offline` / `google` / `passthrough` |
| `GET /api/voice/list`, `POST /api/voice/clone`, `DELETE /api/voice/{id}` | Voices; clone accepts `audio/*` or `video/webm`, 20 MB cap; only `custom_*` deletable; stored in memory for the session |
| `POST /api/generate_symbol` | Text→pictogram; 501 without `OPENAI_API_KEY`; model via `SYMBOL_IMAGE_MODEL` (default `gpt-image-1`) |
| `GET /api/health`, `GET /api/hmm_info`, `POST /api/hmm_reload` | Health, model stats incl. `infinity_gram_enabled/_stats`, reload |
| `/`, `/static` | Static frontend, resolved relative to `app.py` (cwd-independent) |

## 5. Frontend (`indic-generative-aac/frontend/index.html`, 2,834 lines)

Single file: **React 18 (UMD from unpkg, unpinned `react@18`) transpiled in-browser by Babel-standalone**, Tailwind via CDN, Firebase 10.12.2 compat SDKs, Google Fonts. *(Older docs call this "vanilla JS" — it is not.)* The page therefore needs internet for its scripts even though data/preferences are cached locally. Languages: `en`, `hi`, `gu`, `mr` (UI chrome and symbol grids localised). Other files: `all_emojis.js` (5,225 emojis, generated by `gen_emojis.py`), `evaluate.html`, and `index_new.html` (legacy design variant, only touched by `apply_aac_design*.py`/`fix_html.py`).

Features, by origin:
- **Nov-4 line:** Google sign-in + Firestore sync (My Words and Quick Picks merged by id, never overwritten; `FIREBASE_CONFIG` is filled in, rules in `README.md` must be published in the Firebase console); localStorage cache `aac_studio_cache_v1`; **My Words** custom grid (📌, pink on canvas); **AI Symbol Creator** (Emoji vs AI Generated, images downscaled to 256 px); **bookmarked Quick Picks** (⭐ shelf, tap to speak); **voice presets + cloning**; **F5-TTS playback** with browser speech as fallback and *Replay Voice*; **♿ Accessibility Dock** (A−/A+, day/night, grayscale, high contrast, speech speed); tactile button animations; "Indic AAC Studio" title and ⚡ favicon.
- **Infinity-gram line:** **∞-gram next-word shelf** (label "Top Words:", probability + `∞-Ng` badge for ≥4-word context); **1-tap Quick Express** phrases (localised ×4); **Un-Jumble**; **Delete Last** and **Copy** (reports clipboard failure); **Universal Core Words** row; **card size** Compact/Standard/Large (category bar + Preferences, cached); speaking indicator; offline-first transliteration.
- Merge decisions: Speech Speed and High Contrast live only in the dock; "Quick Picks" now means only the bookmark shelf; Quick Express clears stale IndicF5 audio so Replay Voice replays the right sentence.

## 6. Dual HMM kit (`dual_hmm_streaming_kit/`)
- `models_def.py`: `AACNextWordHMM` (HMM-1, 4-gram next word) and `AACUnjumbleHMM` (HMM-2, syntactic permutation decoder); shares transition stores between the two to avoid ~12 GB duplicate RAM; `trim_memory`.
- `train_dual_hmm_streaming.py`: streams Hugging Face data in ~500K-sentence chunks (`agentlans/high-quality-english-sentences`, Tatoeba ×2, then `monology/pile-uncopyrighted` slices), prunes, evaluates on `test_suite.py` (24 clinical/conversational sentences → next-word top-1/3/5 and un-jumble exact match), writes `models/*_latest.pkl` and `logs/` (git-ignored).
- `monitor_daemon.py`: 10-minute health check (GPU/RAM/disk), restarts a stalled trainer.
- Models in git are **LFS pointers** (see §9). Kept sizes: HMM-1 210.6 MB, HMM-2 816.6 MB (infinity-gram side); the Nov-4 versions (1250 MB / 1042 MB) remain on `nov4-v1`.

## 7. Sentence-refinement kit (`AAC_Sentence_Refinement_Training_Kit/`)
Fixes the "intent-blind `I want …` prefix" problem: resolve intent from selected concepts first, then choose a frame. Pieces: `aac_refiner.py` (rules + local seq2seq worker + validator + cache + raw fallback), `prepare_data.py` (synthetic pairs + WikiText-2 denoising), `train.py`, `evaluate.py`, 38 unit tests, `docs/MULTILINGUAL_PLAN.md` (hi/gu/mr roadmap: concept IDs, no inferred gender), `docs/LLM_SYSTEM_PROMPT.txt`. Executed on a TITAN Xp (Nov 2): `google/flan-t5-small`, seed 42, 10 epochs.

| Method (384 synthetic test payloads) | Exact match | Negation errors | Latency |
|---|---|---|---|
| Rules | 100% | 0/172 | ~0.08 ms |
| AAC-only fine-tune | 98.44% | 0/172 | ~23 ms |
| Fluency→AAC fine-tune | 98.70% | 0/172 | ~24 ms |
| Hybrid (rules + model) | 100% | 0/172 | ~0.07 ms |

The data is synthetic (3,820 payloads / 398 groups), so treat these as pilot numbers. English only; **not integrated into `backend/`**. Checkpoints live under `runs/seed_42_gpu_max/` (tokenizers/JSON are in git; weights are not).

## 8. How to run

```bash
conda activate taac_env            # Python 3.10 — the env used by README, run.sh, RUN.md
pip install fastapi uvicorn torch transformers scipy pydantic safetensors vocos
./run.sh                           # or: cd indic-generative-aac/backend && python app.py
# UI  http://localhost:8000  (8001 if 8000 is busy)    API docs  /docs
```
- Optional env: `OPENAI_API_KEY`, `SYMBOL_IMAGE_MODEL`, `PORT`. Restart after changing.
- IndicF5 weights are **not in git**: put them in `AI4Bharat-Indic-TTS/checkpoint/` (`model.safetensors`, `vocab.txt`); reference prompts are already in `IndicF5/prompts/`. Without weights the app runs with mock audio.
- `indic-aac2` appears in `wait_and_run.sh`, `scripts/run_all_tests.sh`, `EXPERIMENTS.md`, old `CONTEXT.md` — an earlier env name; use `taac_env`.
- Tests: `indic-generative-aac/tests/semantic/` (`test_llm3_eval.py` and `evaluate_modes.py` call the **live** backend on :8000), `scripts/run_all_tests.sh` (stale env), `dual_hmm_streaming_kit/test_suite.py` (benchmark cases, not a pytest file), kit tests via `python3 -m unittest discover -s tests -v`.

## 9. Current state of this checkout (as of 2026-11-11)
- `git lfs` is **not installed** here and all four `.pkl` models are 131–134-byte LFS pointer files (`hmm_model.pkl` → 816 MB, `hmm_hindi.pkl`, `hmm1_nextword_latest.pkl`, `hmm2_unjumble_latest.pkl`). Consequences: the Gutenberg/Hindi/HMM-1 models do not load (a caught exception → built-in small vocab), **Un-Jumble returns the input order**, but the ∞-gram engine still works because it builds from the JSONL datasets. Fix: install git-lfs and `git lfs pull` against the remote that holds the objects (the objects are not in the zips).
- `AI4Bharat-Indic-TTS/checkpoint/` and `indic-generative-aac/models/` do not exist → TTS runs in mock mode; Qwen would be downloaded from Hugging Face on first start.
- Working tree clean on `merged`.

## 10. Verification status
Verified during the merge (details in `MERGE_NOTES.md`): all Python compiles; JSX compiles with Babel; 17-check backend smoke test (with `llm`/`semantic` stubbed); 39-check headless-Chrome run of the real merged UI (both feature sets, preferences incl. card size and My Words survive reload, Hindi localisation, no JS errors). Re-verified for this file: the ∞-gram engine runs and returns the expected `order`/`order_label` values.

**Not verified:** live Firebase Google sign-in; AI symbol generation (needs key); real IndicF5 synthesis and cloning (mock mode only); `llm.py` end-to-end (downloads a model).

Measured LLM-pipeline results that exist in the repo (`tests/semantic/llm3_eval_report.json`, 10 cases, older run): overall validity 90%, entity 100%, negation 100%, intent 80%, unsupported-avoidance 100%, **4 of 10 needed the deterministic fallback**, LLM-3 verdicts 1 PASS / 9 REFINE, TTS success 90%, one case's total 17.9 s (LLM-3 10.3 s).

## 11. Claims in older docs that this tree does not support
`PROJECT_PROPOSAL_CONTEXT.md` (and parts of `REPORT.md` / `EXPERIMENTS.md`) state: **0.0% constraint-violation and negation-drop rate "guaranteed"**, ~3.5–5.5 s end-to-end, <1 ms prediction, "zero external API dependencies / 100% local, HIPAA/GDPR compliant". Before reusing them in a paper or proposal:
- The only measured pipeline data is the 10-case report above, which is not 0% and not that fast; `experiments/baseline/baseline_metrics.json` lists every metric as `NOT MEASURED`. The refinement kit's own `CODING_AGENT_PROMPT.md` says to treat these latency/zero-error statements as unverified.
- The fallback path bypasses the validator (§4), and the validator is substring/regex based, so "guaranteed" overstates it.
- "Fully local / no external services" is **no longer true** for the merged app: Firebase auth/Firestore, optional OpenAI image generation, Google Input Tools transliteration fallback, and CDN-loaded scripts/fonts all leave the machine. Re-word privacy claims accordingly.
- `indic-generative-aac/CONTEXT.md` is stale (calls the UI vanilla JS, references a non-existent `validation.py`, a `localhost.run` tunnel, env `indic-aac2`); `indic-generative-aac/README.md`, `EXPERIMENTS.md`, `REPORT.md` still describe FastPitch Indic-TTS as the engine (now IndicF5). **This file supersedes them.**

## 12. Gotchas & open issues
1. **Leftover hard-coded paths** (the merge only portable-ised the infinity-gram-side files): `dual_hmm_streaming_kit/train_dual_hmm_streaming.py:41` (`BACKEND_HMM_PATH` → another machine's `AAC_System-jaydeep/…`), `monitor_daemon.py:20`, `backend/keep_alive.sh:4`, `backend/build_large_hmm.py:45`, `AAC_Sentence_Refinement_Training_Kit/.../run_full_gpu_experiment.sh:6` (miniconda `taac_env` python), `gen_emojis.py` and `update_html*.py` (`/home/linux/Documents/2026/…`), stale `/media/linux/ShreejiPers1/…` candidates in `tts.py`. Training the HMMs from this tree would write to the wrong place until fixed.
2. **Security posture is demo-grade:** CORS `*` with credentials, binds `0.0.0.0`, unauthenticated `/api/voice/clone`, `/api/hmm_reload`, and `/api/generate_symbol` (spends the server's OpenAI key). Firebase web config is committed (public by design; Firestore rules are the protection — publish them). Do not expose beyond a trusted network as-is.
3. **Validator behaviour to remember:** `now`, `later`, `today`… are rejected when `temporal_state` is empty; entity match is substring-based (can pass wrongly or fail on inflected Indic forms); intent checks only cover FEEL/STATEMENT/QUESTION.
4. `AACRequest.temporal_state` / `location` are `str | None`, while the proposal doc describes lists.
5. Frontend depends on unpinned CDNs (`react@18`, `@babel/standalone`, `cdn.tailwindcss.com`) — a CDN change can break it; no build step exists.
6. Voice clones are held in process memory only (lost on restart); preset availability depends on the reference prompts and weights being present.
7. Repo size: HMM pickles (≈ 1.8 GB combined) are LFS; `.gitignore` excludes `*.safetensors`, `checkpoint(s)/`, `*.wav` test artifacts, `indic-generative-aac/models/`.

## 13. Where to look next
| Question | File |
|---|---|
| Why was X merged this way? | `MERGE_NOTES.md` |
| How do I use/configure it? | `README.md` (Firebase setup, endpoints) |
| Proposal narrative, RQs, novelty framing | `PROJECT_PROPOSAL_CONTEXT.md` (verify numbers first, §11) |
| Refiner experiment details | `AAC_Sentence_Refinement_Training_Kit/aac_sentence_refinement/FINAL_CONTEXT.md` |
| Known-bug audit by the earlier author | `aac_system_dashboard.html` |
| Prompt wording / ledger logic | `indic-generative-aac/backend/llm.py` |
