# Indic & English Generative AAC System (Demo Track)

An end-to-end Augmentative and Alternative Communication (AAC) system incorporating hierarchical LLM verification, HMM next-symbol prediction, and high-fidelity zero-shot speech synthesis for Indic languages and English.

---

## 🌟 Key Features

- **Multilingual AAC Vocabulary**:
  - Structured AAC symbols, intents (*I WANT*, *DON'T WANT*, *I FEEL / SAY*, *I'M ASKING*), and categorised symbol grids for English, Hindi (हिन्दी), Gujarati (ગુજરાતી), and Marathi (मराठी).
- **Hierarchical LLM Generation Pipeline**:
  - **LLM-1 Realizer**: Realizes symbol selections into natural target sentences using `Qwen2.5-0.5B-Instruct`.
  - **LLM-2 Refiner**: Refines and blends concepts.
  - **LLM-3 Verifier**: Strict authority hierarchy preserving semantic fidelity, negation, and preventing hallucinations.
  - **Deterministic Fallback**: Zero-hallucination rule-based fallback for speech reliability.
- **N-Gram Predictive Text**:
  - HMM Markov model (63,000+ bigram states for English, AAC-tuned model for Hindi) for real-time symbol suggestion.
- **Speech Synthesis (TTS)**:
  - Powered by **IndicF5-TTS** (CFM DiT architecture with 24kHz Vocos neural vocoder) supporting zero-shot speaker adaptation across Indic languages and English.
- **Accessible Web Frontend**:
  - High-contrast, dyslexia-friendly layout with audio MOS rating, latency metrics, and caregiver intent breakdown.

### ✨ Latest Web App Features (`indic-generative-aac/frontend/index.html`)

- **Google Sign-In + Cloud Sync (Firebase)**: Top-bar sign-in button. When signed in, *My Words* and *Quick Picks* sync across devices through Firestore (merged by ID, never overwritten). The app still works fully offline and signed-out. See [Firebase setup](#-firebase-google-sign-in-setup).
- **Local Cache**: Language, theme, accessibility settings, voices, custom words and bookmarks are stored in `localStorage` for instant, offline-ready loading.
- **My Words (custom grid)**: A pinned 📌 button in the top bar opens a personal word grid. Custom words are highlighted in pink on the Sentence Canvas.
- **AI Symbol Creator**: In *Preferences → Custom Symbol Style*, choose **Emoji** or **AI Generated**. With AI selected, *+ Add word* generates a communication pictogram from the word (text-to-image via `POST /api/generate_symbol`). Images are downscaled to 256 px so many symbols fit in the cache and in Firestore. If generation fails, the word falls back to its emoji.
- **Bookmark Sentences (Quick Picks)**: A ⭐ next to the generated sentence saves it to a highlighted *Quick Picks* shelf. Tap a saved phrase to speak it instantly.
- **F5-TTS Pipeline**: The Sentence Canvas is sent to the backend, and the synthesized IndicF5 audio is played (browser speech is the fallback). Replay is available on the output card.
- **Voice Controls**: Pick a preset voice, or upload a reference audio clip plus its exact transcript to clone a voice with IndicF5 (`/api/voice/clone`).
- **Accessibility Dock** (floating ♿ button): Text size (A−/A+), Day/Night mode, Grayscale, High Contrast and Speech Speed in one uniform panel.
- **Button Animations**: Tactile press/ripple feedback on every button.
- **Browser tab**: Custom ⚡ favicon and a clean "Indic AAC Studio" title.

---

## 📁 Repository Structure

```
├── indic-generative-aac/        # Core Generative AAC application
│   ├── backend/                 # FastAPI server (app.py), LLM pipeline (llm.py), TTS engine (tts.py), HMM (hmm.py)
│   ├── frontend/                # Interactive Web UI (index.html, all_emojis.js)
│   ├── evaluation/              # Benchmarks and evaluation scripts
│   └── tests/                   # Unit and integration tests
├── baseline_english_system_demo/# Baseline English AAC implementation (AIImageAAC React Native Expo app)
├── english_AAC_Dataset/         # English AAC training and evaluation corpus
├── hindi_AAC_Dataset/           # Hindi AAC dataset and translated pairs
├── IndicF5/                     # IndicF5 TTS module and reference voice prompts
├── AI4Bharat-Indic-TTS/         # AI4Bharat Indic-TTS configs and checkpoints utilities
├── download_models.sh           # Script to download FastPitch and HiFi-GAN acoustic checkpoints
├── run.sh                       # Quick launcher for local backend & frontend
└── francis25_interspeech.pdf    # Baseline reference paper (Interspeech 2025)
```

---

## 🚀 Quickstart

### 1. Environment Setup

Create or activate the conda environment:
```bash
conda activate taac_env
```
(Created with Python 3.10)

Install backend dependencies:
```bash
pip install fastapi uvicorn torch transformers scipy pydantic safetensors vocos
```

### 2. Download Checkpoints

Download required TTS model checkpoints:
```bash
chmod +x download_models.sh
./download_models.sh
```

### 3. Launch System

Start the server:
```bash
chmod +x run.sh
./run.sh
```
Or start manually:
```bash
cd indic-generative-aac/backend
python app.py
```

### 4. Optional: Enable AI symbols and Google sign-in

```bash
# AI Symbol Creator (key stays on the server, never sent to the browser)
export OPENAI_API_KEY="sk-..."
# optional: choose another image model (default: gpt-image-1)
export SYMBOL_IMAGE_MODEL="gpt-image-1"
```

Restart the backend after changing environment variables.

#### 🔐 Firebase Google Sign-In setup

1. Create a project at https://console.firebase.google.com and register a **Web app**.
2. Enable **Authentication → Sign-in method → Google**.
3. Create a **Firestore Database**, then publish these rules so each user can only access their own data:
   ```
   rules_version = '2';
   service cloud.firestore {
     match /databases/{db}/documents {
       match /users/{uid} {
         allow read, write: if request.auth != null && request.auth.uid == uid;
       }
     }
   }
   ```
4. Put your web config in `FIREBASE_CONFIG` inside `indic-generative-aac/frontend/index.html`. Web config values are public by design; the Firestore rules protect the data.
5. Open the app at `http://localhost:8000` (`localhost` is an authorized domain by default; add other domains under *Authentication → Settings → Authorized domains*).

Open your browser and navigate to:
- **Web UI**: `http://localhost:8001/` (or `http://localhost:8000/`)
- **API Docs**: `http://localhost:8001/docs`

### New API endpoints

| Endpoint | Purpose |
|---|---|
| `POST /generate` | Full pipeline; accepts optional `voice_id` and returns `audio_b64` |
| `GET /api/voice/list` | Preset and cloned voices, plus engine status |
| `POST /api/voice/clone` | Upload reference audio and transcript to clone a voice (IndicF5) |
| `DELETE /api/voice/{voice_id}` | Remove a cloned voice |
| `POST /api/generate_symbol` | Text-to-image AAC symbol (needs `OPENAI_API_KEY`) |
