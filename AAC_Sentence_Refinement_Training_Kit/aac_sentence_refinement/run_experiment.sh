#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Dependencies must already be installed in the selected Python environment.
PYTHON_BIN="${PYTHON_BIN:-python3}"
SEED="${SEED:-42}"
ONLINE_MAX="${ONLINE_MAX:-5000}"
BATCH_SIZE="${BATCH_SIZE:-2}"
GRAD_ACCUM="${GRAD_ACCUM:-4}"
RUN_ROOT="${RUN_ROOT:-runs/seed_${SEED}}"
BASE_MODEL="${BASE_MODEL:-google/flan-t5-small}"

"$PYTHON_BIN" preflight.py
"$PYTHON_BIN" -m unittest discover -s tests -v
"$PYTHON_BIN" prepare_data.py --out data --seed 42 --online-max "$ONLINE_MAX"

# Primary task-only baseline: do not assume generic fluency adaptation helps.
"$PYTHON_BIN" train.py --train-file data/aac_train.jsonl --valid-file data/aac_validation.jsonl \
  --model "$BASE_MODEL" --output "$RUN_ROOT/aac_only" --seed "$SEED" \
  --batch-size "$BATCH_SIZE" --grad-accum "$GRAD_ACCUM" --epochs 5 --precision fp32
"$PYTHON_BIN" evaluate.py --data data/aac_test.jsonl --mode all \
  --model "$RUN_ROOT/aac_only/best" --out "$RUN_ROOT/eval_aac_only" --device cuda
"$PYTHON_BIN" evaluate.py --data data/regression.jsonl --mode all \
  --model "$RUN_ROOT/aac_only/best" --out "$RUN_ROOT/regression_aac_only" --device cuda

if (( ONLINE_MAX > 0 )); then
  "$PYTHON_BIN" train.py --train-file data/fluency_train.jsonl --valid-file data/fluency_validation.jsonl \
    --model "$BASE_MODEL" --output "$RUN_ROOT/fluency" --seed "$SEED" \
    --batch-size "$BATCH_SIZE" --grad-accum "$GRAD_ACCUM" --max-steps 300 --precision fp32
  "$PYTHON_BIN" train.py --train-file data/aac_train.jsonl --valid-file data/aac_validation.jsonl \
    --model "$RUN_ROOT/fluency/best" --output "$RUN_ROOT/fluency_then_aac" --seed "$SEED" \
    --batch-size "$BATCH_SIZE" --grad-accum "$GRAD_ACCUM" --epochs 5 --precision fp32
  "$PYTHON_BIN" evaluate.py --data data/aac_test.jsonl --mode all \
    --model "$RUN_ROOT/fluency_then_aac/best" --out "$RUN_ROOT/eval_fluency_then_aac" --device cuda
  "$PYTHON_BIN" evaluate.py --data data/regression.jsonl --mode all \
    --model "$RUN_ROOT/fluency_then_aac/best" --out "$RUN_ROOT/regression_fluency_then_aac" --device cuda
fi

# Environment recording is separate from the curated dependency file.
"$PYTHON_BIN" -m pip freeze > "$RUN_ROOT/environment_lock.txt"
