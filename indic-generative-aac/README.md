# Robust Indic Generative AAC

A fully local, open/open-weight, Indic Generative AAC system.

## Objective Completed
This repository implements a fully tested, research-grade, optimized, and reproducible localhost system where:
1. A user selects AAC concepts.
2. The system constructs a structured AAC context.
3. Qwen2.5-0.5B-Instruct generates a natural Indic or controlled code-mixed utterance.
4. A Semantic Preservation loop verifies the intent, entities, and negation match.
5. AI4Bharat Indic-TTS synthesizes the speech using FastPitch + HiFi-GAN.
6. HMM predictive UI (400K Gutenberg model) minimizes latency.

## Architecture
See `CONTEXT.md` for full implementation details.

## Running the App
See `RUN.md` for startup commands.

## Evaluation
See `EXPERIMENTS.md` for ablation studies, failure analysis, and evaluation benchmarks (WER, RTF, Latency, and Semantic Fidelity).
