# Indic AAC Studio: demo installation and reviewer instructions

Status of this document: **verified on the evaluation machine only** (existing conda env, not a clean one). A clean-environment install test is **pending**; the exact procedure is in "Clean-environment test" below.

## What a reviewer gets
- Installation package: the repository tree at commit `fe4e185` (`merged`), plus `paper/naacl2027_demo/` (evaluation harness, fixtures, figures, paper source).
- No hosted live demo exists. **Download/hosting URL: to be inserted at submission** (the GitHub remote of the original repository is not publicly accessible: HTTP 404 without credentials).
- Screencast: `demo/screencast/screencast_silent_captioned.mp4` (2:03, captioned, **silent**); `demo/SCREENCAST_SCRIPT.md` has the narration for the audible take.

## Prerequisites (versions used for the paper)
| Item | Used |
|---|---|
| OS | Linux 7.0.0-42 (glibc 2.39), x86-64 |
| GPU | NVIDIA GTX 1650, 4 GB (holds one model copy; two copies ran out of memory). The code falls back to CPU when CUDA is absent; that path was not tested |
| Python | 3.13.13 |
| Packages | torch 2.11.0+cu130, transformers 5.14.1, fastapi 0.136.3, uvicorn 0.52.0, scipy 1.18.0, pydantic 2.13.2, safetensors 0.8.0, vocos 0.1.0, numpy 2.4.6 |
| Browser | Chrome (the only browser tested) |
| Network on first run | Hugging Face Hub (Qwen/Qwen2.5-0.5B-Instruct, about 1 GB, revision `7ae557604adf67be50417f59c2c2f167def9a775`); the web client loads React 18, Babel, Tailwind, Firebase SDK and Google Fonts from CDNs **at every page load** |

## Setup and launch
```bash
conda create -n taac_env python=3.13 -y && conda activate taac_env      # or any Python 3.13 venv
pip install torch                                                         # choose the build for your CUDA driver
pip install transformers fastapi uvicorn scipy pydantic safetensors vocos numpy python-multipart
cd indic-generative-aac/backend && python app.py                          # http://localhost:8000  (8001 if 8000 is busy; $PORT overrides)
```
First start downloads Qwen. Afterwards `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python app.py` runs without the Hub (verified with a socket guard: `eval/offline_guard.py`; the only outbound attempt was the optional Google Input Tools transliteration fallback). The page itself still needs the CDNs.

### Optional: real IndicF5 speech (not verified here)
1. Accept the terms of the gated model `ai4bharat/IndicF5` on the Hugging Face Hub, then download `model.safetensors` and `checkpoints/vocab.txt` into `AI4Bharat-Indic-TTS/checkpoint/`.
2. `pip install x_transformers` (missing in the evaluation env) and make `IndicF5/` importable (`PYTHONPATH=$PWD/IndicF5`).
3. Without these, `/generate` returns a **placeholder tone** and the card still shows the "IndicF5 Voice" badge.

### Optional: HMM checkpoints
`dual_hmm_streaming_kit/models/*.pkl` and `indic-generative-aac/backend/hmm_model.pkl` are Git LFS pointers in this tree. Without the objects, HMM-1/HMM-2 do not load, **Un-Jumble returns the input order**, and prediction relies on the infinity-gram engine (which builds from the bundled JSONL files in about 0.5 s). With the objects: `git lfs pull` (needs access to the original LFS remote), then `python paper/naacl2027_demo/eval/hmm_eval.py` scores HMM-1 and HMM-2 automatically.

## Example inputs and expected behavior (observed on the evaluation machine)
| Language | Selection (board path) | Observed result |
|---|---|---|
| English | Food & Drink > **Water**, then *AI Polish & Speak* | Cascade proposed "I need food." and was rejected (concept missing); returned template "I want Water." Median request about 12 s (two attempts) |
| Gujarati | switch language; Core > **ના** (No); Food > **પાણી** (Water) | Accepted: "મને પાણી ના જોઈએ છે." Median about 7.5 s |
| English | Feelings > **Tired** | Intent-sensitive failure: accepted "The user is tired of waiting for their meal and wants to go out." or template "I want Tired." (English output is sampled; results vary per run) |
| Any | **Speak** button | Voices the literal labels with the browser's speech synthesis (no server call) |

Latency (this machine, no speech synthesis): first request after start about 13.9 s; accepted requests 6.1 to 9.8 s median by language; twice-rejected requests 12.0 to 18.8 s.

## Known behaviors a reviewer will meet
- The output card always says "Natural Realization" and "Accuracy: 100%" for template output, and does not show that a fallback occurred.
- Gujarati contexts show English next-word suggestions; Marathi contexts show Hindi function words.
- The client marks "Nose" (and two Gujarati labels) as a negation.
- A second model copy on a 4 GB GPU triggers CUDA out-of-memory; the server then silently returns the template (log: `eval/logs/evidence_cuda_oom_two_servers_fallback.log`).

## Clean-environment test (pending)
```bash
python3 -m venv /tmp/aac_clean && . /tmp/aac_clean/bin/activate
pip install torch transformers fastapi uvicorn scipy pydantic safetensors vocos numpy python-multipart
cd indic-generative-aac/backend && python app.py &
curl -s localhost:8000/api/health   # expect {"status":"ok",...}
curl -s -X POST localhost:8000/generate -H 'Content-Type: application/json' \
  -d '{"intent":"REQUEST","negation":false,"entities":["Water"],"language":"en","generation_mode":"dual"}'
```
Record the result in `FINAL_CONTEXT.md` (section "Remaining items").
