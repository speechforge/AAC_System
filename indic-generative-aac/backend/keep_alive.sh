#!/bin/bash
# keep_alive.sh — Auto-restarts app.py if it crashes

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate indic-aac2

BACKEND_DIR="/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/backend"
LOG="$BACKEND_DIR/server.log"

cd "$BACKEND_DIR"

while true; do
    echo "[$(date)] Starting app.py..." | tee -a "$LOG"
    python app.py >> "$LOG" 2>&1
    EXIT_CODE=$?
    echo "[$(date)] app.py exited with code $EXIT_CODE. Restarting in 5s..." | tee -a "$LOG"
    sleep 5
done
