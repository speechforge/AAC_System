# Model Registry

| Model | Purpose | Version | Repository/License | Checkpoint Size | Hardware Req |
|-------|---------|---------|--------------------|-----------------|--------------|
| **Qwen2.5-0.5B-Instruct** | AAC Grammar Engine (LLM) | 2.5 | HuggingFace / Open-Weight | ~1.0 GB | GPU (CUDA) / 4GB VRAM |
| **AI4Bharat IndicF5-TTS** | Polyglot Zero-Shot Flow Matching TTS | v1 | GitHub & HuggingFace (ai4bharat/IndicF5) | ~1.4 GB | GPU (CUDA) / 4GB VRAM |
| **Vocos Vocoder (24kHz)** | Neural Vocoder | v1 | charactr/vocos-mel-24khz | ~50 MB | GPU (CUDA) |
| **Whisper-Tiny** | Offline Evaluation ASR | Tiny | HuggingFace / MIT | ~150 MB | GPU/CPU |
| **Gutenberg HMM** | O(1) Predictive Text (188K Sents) | Custom | Local (63K Bigrams, 713K Trigrams) | 37 MB (pkl) | 128 MB RAM |

*Note: All models execute entirely locally on `localhost`. No cloud API keys are required.*
