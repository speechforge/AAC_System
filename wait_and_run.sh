#!/bin/bash
source $(conda info --base)/etc/profile.d/conda.sh

echo "Waiting for PyTorch to be installed..."
while ! conda run -n indic-aac2 python -c "import torch" 2>/dev/null; do
    sleep 5
done
echo "PyTorch installed!"

echo "Installing requirements..."
conda activate indic-aac2
pip install -r indic-generative-aac/indictts/inference/requirements-ml.txt -r indic-generative-aac/indictts/inference/requirements-utils.txt -r indic-generative-aac/indictts/inference/requirements-server.txt jiwer accelerate

echo "Running tests..."
cd indic-generative-aac
bash scripts/run_all_tests.sh
