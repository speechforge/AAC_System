# Experiments and Ablation Studies

## Setup
- **Hardware:** Local GPU execution (CUDA).
- **Environment:** `indic-aac2` Conda Environment.
- **LLM:** Qwen2.5-0.5B-Instruct
- **TTS:** AI4Bharat Indic-TTS (FastPitch + HiFi-GAN)
- **HMM:** Custom Gutenberg Dialogue Dataset (427,454 words, 114,550 Trigrams).

## 1. Baseline Evaluation
**System:** Qwen-0.5B + IndicTTS (No Semantic Loop)
- **Semantic Fidelity:** Moderate (Prone to dropping negation).
- **Latency (LLM):** ~1.5s
- **Latency (TTS):** ~0.7s
- **RTF:** ~0.14
- **Observation:** The LLM successfully stitches keywords but occasionally misinterprets the actor or drops a negation if not explicitly forced via JSON structured contexts.

## 2. Optimized System (Ablation D & E)
**System:** Qwen-0.5B + Semantic Validation Loop + Code-Mixing Segmentation + IndicTTS
- **Semantic Fidelity:** 100% on the controlled test suite (Loop guarantees semantic pass before reaching TTS).
- **Latency (LLM + Semantics):** ~2.5s (Due to double verification).
- **Code-Mixing:** Works smoothly via regex-based language segmentation and numpy audio stitching.
- **WER:** ~12% (Evaluated offline with Whisper-Tiny)

## 3. Failure Analysis
- **Code-Mixing Pronunciation Failures:** Sometimes, English words heavily embedded in Indic phrases sound abrupt because the AI4Bharat Hindi voice expects purely Devnagari phonemes. Solution: Rely on the segmentation engine to swap to the English FastPitch model seamlessly.
- **Reference-Speaker Personalization:** [BLOCKED]. AI4Bharat FastPitch checkpoints explicitly use `use_d_vector_file: false` and rely on a strict set of discrete embeddings (`speakers.pth`), meaning true zero-shot voice cloning is structurally impossible without a separate downstream Voice Conversion module (like FreeVC).

## 4. Multi-Objective Optimization
We optimized for maximum Semantic Fidelity at the expense of a slight ~1.0s latency penalty (due to the semantic verification check). We also eliminated LLM inference completely from the UI's predictive bar by offloading it to the `O(1)` custom Markov HMM.

## 5. 3-LLM Judge Cascade & 188K-Sentence HMM Benchmark
- **LLM-1 Realizer:** Minimal natural realization from Concept Ledger.
- **LLM-2 Refiner:** Intermediate semantic refiner (in Dual Mode).
- **LLM-3 Judge & Arbiter:** Quality-control evaluator using strict JSON schema, few-shot mismatch filtering, and minimal rewrite logic. Out-of-domain words (e.g. invented meal times, purchasing, locations) are explicitly detected and removed.
- **HMM Scale-Up:** Trained on **188,402 sentences** from 24 Project Gutenberg books (63,783 Bigram states, 713,845 Trigram states). Lookups remain strictly `O(1)` with <1ms latency.
- **Constraint Violation Rate (CVR):** 0% when Judge and Hard Semantic Validator are active simultaneously.

