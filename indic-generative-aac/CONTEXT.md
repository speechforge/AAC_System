# Indic Generative AAC - Implementation Context

This document serves as the master architectural context file for the Indic Generative AAC system. It outlines the complete tech stack, AI pipelines, and custom features built into the current implementation.

## 1. System Architecture
- **Frontend:** Single-page application (`index.html`) using Vanilla JavaScript and TailwindCSS (via CDN).
- **Backend:** Python FastAPI (`app.py`) running a highly optimized local AI stack.
- **Hardware/Environment:** Linux environment using Conda (`indic-aac2`), executing heavy PyTorch models on GPU (CUDA).

## 2. Core AI Modules

### A. The 3-LLM Cascade Architecture (`llm.py`)
- **Base Model:** `Qwen2.5-0.5B-Instruct`
- **Stage 1 (LLM-1 Realizer):** Takes user-selected AAC concepts and semantic ledger, realizes a minimal candidate sentence.
- **Stage 2 (LLM-2 Refiner - Dual Mode):** Performs candidate refinement to strip unsupported concepts while preserving grammatical structure.
- **Stage 3 (LLM-3 Judge & Arbiter):** Specialized quality-control prompt acting as linguistic judge. Evaluates against `REQUIRED CONCEPTS` and `FORBIDDEN CONCEPTS`. Employs few-shot mismatch filtering to eliminate out-of-context words (e.g. invented times, planning, buying, store, hungry) and emits a structured JSON verdict with PASS/FAIL, reason, identified violations, and the minimal rewritten sentence.
- **Strict Prompting:** Chatbot behaviors (replying, conversational greetings, asking hallucinatory questions) are strictly banned.

### B. The Predictive HMM Engine (`hmm.py`)
- **Model:** Custom N-Gram Markov Chain (Bigram & Trigram states with Backoff).
- **Scale:** Trained on **188,402 sentences** sourced from 24 Project Gutenberg online books via `train_hmm_large.py`.
- **State Space:** **63,783 Bigram states** and **713,845 Trigram states**.
- **Role:** Powers real-time token and word predictions in `O(1)` time to minimize keystroke latency without GPU overhead.
- **Persistence:** Serialized to `hmm_model.pkl` with automated load/reload API (`/api/hmm_info`, `/api/hmm_reload`).

### C. Text-to-Speech Engine (`tts.py`)
- **Model:** AI4Bharat IndicF5-TTS (Flow Matching DiT + Vocos 24kHz neural vocoder).
- **Role:** Converts the final LLM-generated sentence into expressive offline speech across 11 Indian languages and English using zero-shot voice styling. Returns the synthesized audio at 24kHz as a Base64-encoded WAV to the frontend for immediate client-side playback.

### D. Semantic Validator (`validation.py`)
- **Role:** Intercepts LLM outputs and mathematically evaluates semantic coherency to ensure the output isn't wildly hallucinated.

## 3. Frontend UI & Features (`index.html`)

- **Dynamic Tokenization Bar:** Users can type free-text (e.g., "Banana, milk"). Pressing comma or enter instantly tokenizes the word into a visual chip and automatically assigns a matching emoji by scanning the local dictionary.
- **Predictive HMM Bar:** Sits below the sentence bar. Fetches and displays the top 5 predicted next words dynamically as the user types.
- **Magic Context Suggester:** Users can type a scenario (e.g., "At the park") and the LLM dynamically generates 15 situationally relevant AAC buttons.
- **Comprehensive Emoji Dictionary:** A static script (`all_emojis.js`) containing 5,225 Unicode emojis mapped to text labels, enabling instant client-side searching.
- **Accessibility Engine:** 
  - **Font Scale:** 1 to 5 sliding scale (modifies root `rem` for fluid Tailwind scaling without box-cropping).
  - **Themes:** Dark Mode and Light Mode with high-contrast overrides.
  - **Color Profiles:** Full Color or Grayscale/Black & White modes.
- **Particle Animations:** Clicking "Generate & Speak" launches a smooth, 4-7 second staggered flying emoji animation.

## 4. Networking & Access
- The FastAPI server binds to `0.0.0.0:8000`, making it accessible on the local Wi-Fi network (e.g., `http://192.168.1.19:8000`).
- Because of Wi-Fi router AP Isolation, a permanent keep-alive SSH tunnel is actively running via `localhost.run` to provide a secure, public HTTPS link that bypasses the router.
