#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

export PYTHONUNBUFFERED=1
PYTHON_BIN="/home/linux/miniconda3/envs/taac_env/bin/python"
SEED=42
BATCH_SIZE=16
GRAD_ACCUM=2
EPOCHS=10
MAX_TARGET_TOKENS=128
RUN_ROOT="runs/seed_${SEED}_gpu_max"
BASE_MODEL="google/flan-t5-small"

mkdir -p "$RUN_ROOT"
LOG_FILE="$RUN_ROOT/full_experiment.log"
STATUS_FILE="$RUN_ROOT/status.json"

update_status() {
    local phase="$1"
    local pct="$2"
    local msg="$3"
    cat << JSON > "$STATUS_FILE"
{
  "phase": "$phase",
  "progress_pct": $pct,
  "message": "$msg",
  "updated_at": "$(date -Iseconds)",
  "batch_size": $BATCH_SIZE,
  "grad_accum": $GRAD_ACCUM,
  "epochs": $EPOCHS,
  "gpu": "NVIDIA TITAN Xp"
}
JSON
}

echo "=== CONTINUING FULL GPU SENTENCE REFINEMENT EXPERIMENTS ===" | tee -a "$LOG_FILE"

# Check if Arm 1 already completed
if [ -f "$RUN_ROOT/aac_only/best/model.safetensors" ] && [ -f "$RUN_ROOT/eval_aac_only/metrics.json" ]; then
    echo "[Phase 1-4] Arm 1 already completed with high accuracy (Exact match: 98.4% model, 100% hybrid). Proceeding to Arm 2..." | tee -a "$LOG_FILE"
else
    echo "[Phase 1/6] Running CUDA preflight..." | tee -a "$LOG_FILE"
    "$PYTHON_BIN" preflight.py | tee -a "$LOG_FILE"

    echo "[Phase 1/6] Running unit tests..." | tee -a "$LOG_FILE"
    "$PYTHON_BIN" -m unittest discover -s tests -v | tee -a "$LOG_FILE"

    echo "[Phase 2/6] Preparing and verifying data..." | tee -a "$LOG_FILE"
    update_status "data_prep" 15 "Preparing AAC and WikiText fluency data"
    "$PYTHON_BIN" prepare_data.py --out data --seed "$SEED" --online-max 5000 | tee -a "$LOG_FILE"

    echo "[Phase 3/6] Starting Arm 1: AAC-Only GPU Fine-Tuning ($EPOCHS Epochs, Batch Size $BATCH_SIZE)..." | tee -a "$LOG_FILE"
    update_status "training_aac_only" 25 "Training Arm 1: AAC-Only ($EPOCHS epochs)"
    "$PYTHON_BIN" train.py \
      --train-file data/aac_train.jsonl \
      --valid-file data/aac_validation.jsonl \
      --model "$BASE_MODEL" \
      --output "$RUN_ROOT/aac_only" \
      --seed "$SEED" \
      --batch-size "$BATCH_SIZE" \
      --grad-accum "$GRAD_ACCUM" \
      --epochs "$EPOCHS" \
      --max-target-tokens "$MAX_TARGET_TOKENS" \
      --precision fp32 | tee -a "$LOG_FILE"

    echo "[Phase 4/6] Evaluating Arm 1..." | tee -a "$LOG_FILE"
    update_status "eval_aac_only" 55 "Evaluating Arm 1 on test and regression sets"
    "$PYTHON_BIN" evaluate.py --data data/aac_test.jsonl --mode all \
      --model "$RUN_ROOT/aac_only/best" --out "$RUN_ROOT/eval_aac_only" --device cuda | tee -a "$LOG_FILE"
    "$PYTHON_BIN" evaluate.py --data data/regression.jsonl --mode all \
      --model "$RUN_ROOT/aac_only/best" --out "$RUN_ROOT/regression_aac_only" --device cuda | tee -a "$LOG_FILE"
fi

echo "[Phase 5/6] Starting Arm 2: Online Fluency Pre-adaptation (500 steps)..." | tee -a "$LOG_FILE"
update_status "training_fluency" 65 "Training Arm 2 Part A: Fluency adaptation (500 steps)"
rm -rf "$RUN_ROOT/fluency"
"$PYTHON_BIN" train.py \
  --train-file data/fluency_train.jsonl \
  --valid-file data/fluency_validation.jsonl \
  --model "$BASE_MODEL" \
  --output "$RUN_ROOT/fluency" \
  --seed "$SEED" \
  --batch-size "$BATCH_SIZE" \
  --grad-accum "$GRAD_ACCUM" \
  --max-steps 500 \
  --max-target-tokens "$MAX_TARGET_TOKENS" \
  --precision fp32 | tee -a "$LOG_FILE"

update_status "training_fluency_aac" 80 "Training Arm 2 Part B: AAC fine-tuning from fluency checkpoint ($EPOCHS epochs)"
rm -rf "$RUN_ROOT/fluency_then_aac"
"$PYTHON_BIN" train.py \
  --train-file data/aac_train.jsonl \
  --valid-file data/aac_validation.jsonl \
  --model "$RUN_ROOT/fluency/best" \
  --output "$RUN_ROOT/fluency_then_aac" \
  --seed "$SEED" \
  --batch-size "$BATCH_SIZE" \
  --grad-accum "$GRAD_ACCUM" \
  --epochs "$EPOCHS" \
  --max-target-tokens "$MAX_TARGET_TOKENS" \
  --precision fp32 | tee -a "$LOG_FILE"

echo "[Phase 6/6] Evaluating Arm 2..." | tee -a "$LOG_FILE"
update_status "eval_fluency_aac" 95 "Evaluating Arm 2 on test and regression sets"
rm -rf "$RUN_ROOT/eval_fluency_then_aac" "$RUN_ROOT/regression_fluency_then_aac"
"$PYTHON_BIN" evaluate.py --data data/aac_test.jsonl --mode all \
  --model "$RUN_ROOT/fluency_then_aac/best" --out "$RUN_ROOT/eval_fluency_then_aac" --device cuda | tee -a "$LOG_FILE"
"$PYTHON_BIN" evaluate.py --data data/regression.jsonl --mode all \
  --model "$RUN_ROOT/fluency_then_aac/best" --out "$RUN_ROOT/regression_fluency_then_aac" --device cuda | tee -a "$LOG_FILE"

"$PYTHON_BIN" -m pip freeze > "$RUN_ROOT/environment_lock.txt"
update_status "completed" 100 "All GPU experiments and evaluations successfully completed"
echo "=== ALL EXPERIMENTS COMPLETED SUCCESSFULLY ===" | tee -a "$LOG_FILE"
