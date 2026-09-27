# Localhost Run Instructions

To boot the fully optimized and verified Indic Generative AAC system on your local machine, run the following commands:

```bash
# 1. Activate the environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate indic-aac2

# 2. Start the Backend API Server
cd indic-generative-aac/backend
python app.py

# 3. Access the Frontend UI
# Open your web browser and navigate to:
http://localhost:8001
# (or http://localhost:8000 if port 8000 is free; port is configurable via PORT env var)
```

*Note: The frontend is statically served by FastAPI on port 8001 (or 8000) alongside the backend endpoints.*
