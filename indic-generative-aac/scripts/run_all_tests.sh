#!/bin/bash
set -e
echo "Activating env..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate indic-aac2

echo "Running LLM test..."
python ../backend/test_llm.py

echo "Running TTS test..."
python ../backend/test_tts.py

echo "Running Ablation Study..."
python ../evaluation/ablation.py

echo "All tests completed!"
