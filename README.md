# Indic AAC Studio — 22 November 2026 version (paper-ready repository)

**Branch:** `November_22_2026` (builds on the 16 November snapshot below).

| What | Where |
|---|---|
| Paper (latest, proof-read LaTeX + PDF) | `paper/FINAL_NAACL_DEMO_v3/after_the_proof_reading_final_version/` (`latex_source_final/`, `Indic_AAC_Studio_NAACL2027_Demo_v3_final.pdf`) |
| Earlier paper drafts | `paper/FINAL_NAACL_DEMO_v1..v3*`, `paper/CLAUDE_WRITTEN`, `paper/CHATGPT_WRITTEN` |
| Baseline paper (Gaines & Vertanen) and our comparison | `paper/baseline_system_paper_of_AAC_system/` |
| **Running experiment log (every step, every number)** | `paper/baseline_system_paper_of_AAC_system/20_nov_changes.md` |
| Frozen baseline results (never edited) | `paper/baseline_system_paper_of_AAC_system/Results_10/` |
| New experiment code, raw results (`.json` + `.log`), LoRA adapters | `paper/baseline_system_paper_of_AAC_system/our_experiments_vs_baseline/` (`results/`) |
| Improved CPU predictor shipped in the backend | `indic-generative-aac/backend/predictor_v2.py` (+ `test_predictor_v2.py`, `predictor_data/`) |
| Listening-test (MOS) portal | `subjective_Mos_portal/` (admin password is NOT in the repo) |

Headline results (full test sets, KSR %, higher is better; details and 95% CIs in `20_nov_changes.md`):
English 56.3 → 57.5, Hindi 56.7 → 58.3, Marathi 48.7 → 51.9, Gujarati 53.0 → 55.6 for the CPU-only predictor; with the adapted
BLOOM-560m re-ranker our English KSR (62.65) ties the baseline's adapted OPT-125m (62.64) on the baseline's own sample.
5-fold cross-validation: 20/20 folds positive. Marathi/Gujarati data are machine-translated (indicative only).

Reproduce: `cd paper/baseline_system_paper_of_AAC_system/our_experiments_vs_baseline && python exp_final.py <lang>` (see the script headers and the log).
`data_native/*_native_train.txt` (large) is not stored; rebuild with `python prep_native.py`.

---

# Indic AAC Studio — final snapshot, 16 November 2026

This branch preserves the working AAC website accepted on 16 November 2026: the existing ivory-and-violet GUI, separate welcome/login pages, sentence canvas, real speech playback, and the backend-only Un-Jumble repair.

**Saved branch:** `november_16_2026_branch`

**Application:** `indic-generative-aac/`

**Local URL:** <http://localhost:8000/>

“Final snapshot” identifies this saved version. It does not mean every item in the vNext research roadmap is complete. The active communicator is `frontend/index.html`; `index_new.html` and `vnext.jsx` are alternate/historical implementations.

## What this version includes

- English, हिन्दी, ગુજરાતી, and मराठी vocabulary and interface workflows.
- A split canvas showing selected words beside the intended message, with **Speak / Pause / Resume**, **Stop audio**, and **Make sentence**.
- Comma-separated paste into **Type custom word**, preserving word order, Indic text, and multiword phrases. The three-dot canvas menu closes when the pointer leaves its combined button/popup area.
- The existing intent and polarity analysis, gated sentence generation, and checked template previews. Technical intent metadata is hidden in the normal communicator.
- **Un-Jumble:** a local English grammar rule, then Qwen, with the trained English HMM2 as an optional fallback for known vocabulary. The backend validates chip permutations and retains repeated input labels.
- Real **English-trained F5-TTS** for English and **IndicF5** for Hindi, Gujarati, and Marathi. Pausing and resuming reuse the existing audio; Stop cancels active and pending playback.
- **Online / Offline** controls. Online can generate new sentences and speech through the local backend. Offline uses installed public phrases, checked templates, and exact saved audio on the device; it cannot synthesize arbitrary unseen text.
- Local username/password accounts and optional verified Google sign-in, Redis-backed account history/bookmarks, profile-scoped My Words/photo preferences, and CSV history export.
- Shared themes, motion controls, reduced-motion support, and accessibility preferences.

## Restore the saved source

```bash
git clone --branch november_16_2026_branch git@github.com:speechforge/AAC_System.git
cd AAC_System
git lfs install
git lfs pull
```

The HMM `.pkl` files use Git LFS. Neural model weights, account databases, generated audio caches, credentials, and Python environments are separate from the source repository. A GitHub checkout alone is not a pre-provisioned speech installation.

## Run the existing local setup

The verified setup uses Linux, Python 3.10 in `taac_env`, Chrome, local Redis, and CUDA for neural inference. From the project root:

```bash
conda activate taac_env

# First setup of the project-local Redis binaries and account dependencies:
bash indic-generative-aac/scripts/setup_personal_storage.sh

# Prepare the English F5 checkpoint; existing IndicF5 weights are also required:
python indic-generative-aac/scripts/setup_speech_models.py

# Start the application and persistent local Redis:
python indic-generative-aac/backend/run_local.py start

# Inspect readiness:
python indic-generative-aac/backend/run_local.py status
```

The scripts default to `/home/linux/miniconda3/envs/taac_env/bin/python` on the verified machine. On another installation, set `AAC_PYTHON` to your Python executable when using the shell setup/launcher scripts. Install the existing F5 implementation's dependencies from `IndicF5/requirements.txt` as appropriate for your Torch/CUDA environment; FastAPI, Uvicorn, Transformers, SciPy, Pydantic, and `python-multipart` are also needed by the backend. Account dependencies are listed in `backend/requirements-personal.txt`. These are setup requirements, not a promise of a one-command fresh-machine installation.

Open:

| Route | Purpose |
| --- | --- |
| `/welcome` | Landing page |
| `/login` | Sign in |
| `/signup` | Create a local account |
| `/` | AAC communicator |
| `/api/health` | Backend, speech, and storage readiness |
| `/docs` | API documentation |

The bundled demo login is `demo` / `AACdemo@2026`. It is a shared demonstration account. For personal data, create a separate account. Google sign-in uses Firebase identity verification and requires its Google provider and authorized domain configuration; Redis remains the backend account store. My Words/photos remain device-cached by profile and are not a general cloud-sync service.

Stop only when needed:

```bash
python indic-generative-aac/backend/run_local.py stop
```

This stops AAC and leaves Redis running. Account data and sessions are not shipped with the saved source.

## Model files and speech setup

| Component | Expected location / behavior |
| --- | --- |
| Qwen2.5-0.5B-Instruct | Local `indic-generative-aac/models/Qwen2.5-0.5B-Instruct/` when present; otherwise the Hugging Face cache/download |
| IndicF5 | `AI4Bharat-Indic-TTS/checkpoint/model.safetensors` and `vocab.txt` |
| English F5 | `.runtime/models/f5-english/F5TTS_Base/model_1200000.safetensors` and `vocab.txt` |
| Vocos | Local `indic-generative-aac/models/vocos/` when present; otherwise the configured upstream cache/download |
| HMM1 / HMM2 | `dual_hmm_streaming_kit/models/`, retrieved through Git LFS |
| Hindi HMM | `indic-generative-aac/backend/hmm_hindi.pkl`, retrieved through Git LFS |
| Voice references | `IndicF5/prompts/`, the English F5 example reference, and `backend/reference_audio/` |

See [INDICF5_LOCAL_SETUP.md](INDICF5_LOCAL_SETUP.md), [SPEECH_QUALITY_FIX.md](SPEECH_QUALITY_FIX.md), [ACCOUNTS_GUIDE.md](ACCOUNTS_GUIDE.md), and [PERSONAL_SERVICE_SETUP.md](PERSONAL_SERVICE_SETUP.md) for implementation details. Some older setup/evaluation documents describe earlier snapshots; this README and the current [handoff](docs/aac-redesign/FINAL_CONTEXT.md) identify the active version. Missing speech dependencies or weights produce an explicit unavailable/error state, not placeholder speech.

## Verify the Un-Jumble repair

1. Select English and paste this list into **Type custom word**:

   ```text
   share, AAC, clearly, students, the, helps, system, thoughts, their
   ```

2. Select **⋯ → Un-Jumble**. The existing GUI applies the order directly. It should arrange the nine chips as:

   ```text
   the AAC system helps students share their thoughts clearly
   ```

3. Use **Speak**. The order-only operation retains the authored casing and punctuation of the chips.

The imported fix changed the backend; the downloaded replacement GUI and its “Use this order” preview were intentionally not applied.

```bash
# Pure backend ordering checks; run from the project root:
python -m unittest discover -s indic-generative-aac/backend -p test_word_order.py -v

# Other backend regression checks:
python -m unittest discover -s indic-generative-aac/backend -p test_tts_contract.py -v
```

For the current browser regression scripts, prepare Playwright under the project-local runtime directory, keep the backend running, and use the installed Chrome path expected by the scripts:

```bash
npm install --prefix .runtime/browser playwright@1.51.1
node indic-generative-aac/tests/browser/reference-unjumble.cjs
node indic-generative-aac/tests/browser/reference-canvas-paste.cjs
node indic-generative-aac/tests/browser/reference-play-pause.cjs
node indic-generative-aac/tests/browser/reference-modes-layout.cjs
node indic-generative-aac/tests/browser/reference-offline-pack.cjs
```

The `reference-*` scripts cover the restored active communicator. Older `vnext-*` scripts and paired metrics describe an earlier experimental UI and are not all release gates for this saved GUI. Evidence and limitations are recorded in [docs/aac-redesign/FINAL_CONTEXT.md](docs/aac-redesign/FINAL_CONTEXT.md) and [the release record](docs/releases/2026-11-16.md).

## Known limits of this snapshot

- Qwen cannot reliably reorder every construction. A valid permutation alone is not proof of grammatical or semantic correctness. The exact nine-chip example passed both the live API and the existing browser flow.
- The unchanged GUI still has older handling for no-suggestion responses, duplicate chip identities, and edits during an outstanding Un-Jumble request. The backend returns status and position information, but the current GUI does not consume all of it. Its Un-Jumble payload omits locale; explicit non-English routing has been checked at the API.
- Offline use requires setup while online. Only installed/saved matching audio is available without the backend; initial provisioning and new speech need services.
- Stable reserved core slots across categories, a full board editor, switch scanning, interoperability/import, and the broader research evaluation remain unfinished.
- Automated playback checks verify browser media events. No claim is made of native-reader grammar review, physical assistive-hardware testing, screen-reader certification, or a completed AAC-user study.
