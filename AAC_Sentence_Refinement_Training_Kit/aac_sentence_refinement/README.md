# AAC Sentence Refinement: English training and Indic expansion kit

The immediate repair is to resolve intent from selected concepts before choosing
a sentence frame. A universally inserted `I want` prefix is not user intent.
For English, start from a pretrained model, fine-tune on paired AAC selections
and sentences, and evaluate optional online-English fluency adaptation separately.
Training a new language model from scratch is unnecessary for this module.

## What is included

| File | Purpose |
|---|---|
| `CODING_AGENT_PROMPT.md` | Self-contained instructions for inspecting and integrating your actual AAC repository |
| `aac_refiner.py` | Complete `AACRefiner`, few-shot prompt, local seq2seq worker, validation, cache, raw fallback, four-example demo |
| `prepare_data.py` | Reproducible synthetic AAC pairs and optional online WikiText fluency data |
| `train.py` | GPU fine-tuning, token-weighted loss, grouped-split checks, checkpoints and logs |
| `preflight.py` | Tests the installed GPU runtime with an actual CUDA tensor operation |
| `evaluate.py` | Per-payload predictions, metric denominators, grouped bootstrap intervals, CSV/JSON and a figure |
| `run_experiment.sh` | Executes AAC-only and optional fluency-then-AAC experiments |
| `tests/test_refiner.py` | Regression, semantic guard, timeout and data-split checks |
| `docs/MULTILINGUAL_PLAN.md` | Hindi, Gujarati and Marathi roadmap |
| `docs/LLM_SYSTEM_PROMPT.txt` | Standalone copy of the few-shot system prompt for the existing Qwen pipeline |
| `FINAL_CONTEXT.md` | Actual checks performed while preparing this kit; no fabricated neural results |

## Run the four requested examples immediately

Python 3.10+ is sufficient for the rule demo and unit tests:

```bash
python3 aac_refiner.py
python3 -m unittest discover -s tests -v
```

| Selected concepts | Output from the rule path |
|---|---|
| Angry, with, Food | I am angry with the food. |
| Happy, play, outside | I am happy to play outside. |
| Water, please | I want water, please. |
| don't, want, medicine | I do not want medicine. |

These demonstrations test the immediate repair. They do not demonstrate a
trained neural model. An explicit selection of `want, happy` instead becomes
`I want to be happy.` Selecting `not, happy` becomes `I am not happy.`

## Install the training environment

Keep the current production AAC environment intact; use a separate environment.
Python 3.10 or 3.11 and a compatible PyTorch installation are a practical starting
point. Install PyTorch for the actual GPU/driver using its official instructions:
[PyTorch installation](https://pytorch.org/get-started/locally/).
The scripts use the PyTorch 2.6+ API. Do not replace an existing working CUDA
installation blindly, particularly on TITAN Xp/Pascal hardware.

```bash
python3 -m venv .venv
source .venv/bin/activate
# Install the appropriate PyTorch 2.6+ CUDA build using the official selector.
python -m pip install -r requirements.txt
python preflight.py
```

The actual matrix operation in `preflight.py` must pass. Seeing a GPU in
`nvidia-smi` is insufficient to establish wheel/kernel compatibility.
FP32 is the default, including for TITAN Xp. BF16 is optional and checked at
runtime. This pilot does not require bitsandbytes or FlashAttention.

## Start the GPU experiment

After dependencies and CUDA preflight are ready:

```bash
bash run_experiment.sh
```

The launcher downloads `google/flan-t5-small` and up to 5,000 filtered English
denoising examples from `Salesforce/wikitext`, configuration
`wikitext-2-raw-v1`. It records the resolved Hugging Face revisions and data hashes.
The initial run requires internet access to Hugging Face and its model/data hosts.
No model or dataset is downloaded simply by importing `AACRefiner`.

It runs these two arms on identical AAC splits:

1. Pretrained FLAN-T5-small → AAC fine-tuning → evaluation.
2. Pretrained FLAN-T5-small → short English denoising adaptation → AAC fine-tuning → evaluation.

Each arm evaluates raw drafts, deterministic rules, model-first with validation,
and the hybrid rule/model path on the same payloads. Individual pre-validation
model candidates are recorded when the model is attempted. A rejected model
candidate produces the original raw sentence, not a fabricated substitute.

For a smaller-memory GPU, reduce the microbatch without changing the nominal
effective batch size:

```bash
BATCH_SIZE=1 GRAD_ACCUM=8 bash run_experiment.sh
```

To omit general-English adaptation and run only the task-specific baseline:

```bash
ONLINE_MAX=0 RUN_ROOT=runs/aac_only_pilot bash run_experiment.sh
```

For separate optimization seeds, retain the same data-split seed:

```bash
SEED=17 bash run_experiment.sh
SEED=42 bash run_experiment.sh
SEED=73 bash run_experiment.sh
```

Use new output directories for new experiments. The trainer refuses to overwrite
an existing run configuration. It can resume this script's completed-epoch
checkpoints with `--resume runs/.../last` and the same configuration. A checkpoint
stopped by a step cap partway through an epoch is valid for inference; exact
mid-epoch resumption is deliberately unsupported.

## Use a trained checkpoint

For an English payload:

```bash
python aac_refiner.py --model runs/seed_42/aac_only/best --device cuda \
  --json '{"raw_sentence":"I want Angry with Food","selected_concepts":["Angry","with","Food"]}'
```

The default hybrid uses rules for supported clear frames. To exercise the neural
path on those same examples, add `--model-first`. The local model is loaded and
warmed once in a persistent subprocess. Generation is greedy with a short token
cap. The parent serializes model calls and terminates a worker that times out;
the worker is not automatically reloaded during the next utterance. Recreate the
backend outside the interactive path to recover service after a timeout.

```python
from aac_refiner import AACRefiner, LocalSeq2SeqBackend

def main():
    with LocalSeq2SeqBackend("runs/seed_42/aac_only/best", device="cuda") as backend:
        refiner = AACRefiner(backend=backend, timeout_s=2.0)
        print(refiner.refine({
            "raw_sentence": "Water please",
            "selected_concepts": ["Water", "please"],
            "user_intent": "request_object",
        }))

if __name__ == "__main__":
    main()
```

The main guard is required by Python's spawn-based worker. Create a refiner at
application/service startup, not inside every HTTP request. An async HTTP server
should offload the synchronous call to its bounded worker/executor and reject
stale UI revisions before starting TTS.

## Data and evaluation scope

The bundled seed-42 pilot contains 3,820 synthetic AAC payloads: 3,052 train,
384 validation and 384 test. Their 398 selection groups are split 318/40/40,
stratified by template family. Positive, negative, polite, draft-corruption and
optional-intent variants stay in one group. A separate eight-case regression
file includes the four primary examples. Those four semantic groups are excluded
from the synthetic corpus; the remaining regression cases are implementation
checks and are not claimed as independent held-out data.

The online data are article-grouped English denoising pairs, not AAC intent
labels. Only articles from WikiText's original training split are used. Their
internal validation articles stay separate. The preparation step deletes some
articles/copulas while retaining content order and negation. This is auxiliary
fluency training; whether it helps AAC is an experimental question.

The rule grammar and synthetic labels share templates. Passing these tests is an
implementation consistency check, not evidence of general language understanding.
The first independent benchmark should use manually authored selections and
human-reviewed reference sentences, including minimal pairs, ambiguities and
out-of-vocabulary concepts. The coding-agent prompt specifies that work.

This baseline handles first-person English and a limited explicit vocabulary.
Closed frames use a finite set of admissible realizations. A small generic
first-person statement path uses lexical/order checks and is heuristic. Complex
roles, unresolved negation, unknown intents and non-English inputs retain raw
text. Explicit unsupported actor/ledger metadata is rejected rather than ignored.
String checks are not a proof of semantic equivalence. No zero-hallucination,
clinical-reliability or universal real-time guarantee is made.

The existing Qwen cascade, HMM predictor, UI and TTS were described in the
attachment; their source code and checkpoint files were not supplied. Integration
must inspect the real repository and compare the existing Qwen model before
replacing it. The multilingual roadmap requires native data and evaluation;
the shipped English guard intentionally does not generate Indic sentences.

## Primary references

- [FLAN-T5-small model and loading examples](https://huggingface.co/google/flan-t5-small)
- [WikiText dataset](https://huggingface.co/datasets/Salesforce/wikitext)
- [Transformers generation options](https://huggingface.co/docs/transformers/v4.48.2/en/main_classes/text_generation)
- [Current Qwen2.5-0.5B-Instruct model](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
- [mT5-small and its multilingual training coverage](https://huggingface.co/google/mt5-small)
- [AI4Bharat IndicTrans2](https://github.com/AI4Bharat/IndicTrans2)
