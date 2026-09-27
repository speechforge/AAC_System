#!/bin/bash
echo "Activating conda environment..."
source $(conda info --base)/etc/profile.d/conda.sh
conda activate indic-aac2

echo "Verifying models..."

echo "Starting Backend..."
cd indic-generative-aac/backend
python app.py &
BACKEND_PID=$!

echo "Waiting for backend to start..."
sleep 5

echo "----------------------------------------"
echo "Frontend: http://localhost:8001/ (or :8000 if free)"
echo "Backend API: http://localhost:8001/docs"
echo "----------------------------------------"

wait $BACKEND_PID
