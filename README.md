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
conda activate indic-aac2
```

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

Open your browser and navigate to:
- **Web UI**: `http://localhost:8001/` (or `http://localhost:8000/`)
- **API Docs**: `http://localhost:8001/docs`
