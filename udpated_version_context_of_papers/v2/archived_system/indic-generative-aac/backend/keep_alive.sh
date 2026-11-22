#!/bin/bash
# keep_alive.sh — Auto-restarts app.py if it crashes

PYTHON_BIN="/home/linux/miniconda3/envs/taac_env/bin/python"
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$BACKEND_DIR/server.log"

cd "$BACKEND_DIR"

while true; do
    echo "[$(date)] Starting app.py..." | tee -a "$LOG"
    $PYTHON_BIN app.py >> "$LOG" 2>&1
    EXIT_CODE=$?
    echo "[$(date)] app.py exited with code $EXIT_CODE. Restarting in 5s..." | tee -a "$LOG"
    sleep 5
done
