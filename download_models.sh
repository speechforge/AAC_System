#!/bin/bash
# DEPRECATED — This script downloads legacy Indic-TTS (FastPitch) checkpoints
# into indic-generative-aac/indictts/inference/checkpoints/ which no longer exists.
#
# The project now uses IndicF5 (flow-matching TTS) via AI4Bharat-Indic-TTS.
# Model weights are already present at:
#   AI4Bharat-Indic-TTS/checkpoint/model.safetensors  (1.4 GB)
#   IndicF5/prompts/                                   (reference audio)
#
# If you need to re-download IndicF5 weights, follow:
#   https://github.com/AI4Bharat/IndicF5
#
# Keeping this file for historical reference only. DO NOT RUN.
echo "[download_models.sh] DEPRECATED — IndicF5 weights are already present. See comments above."
exit 0

