#!/usr/bin/env bash
set -euo pipefail
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${AAC_PYTHON:-/home/linux/miniconda3/envs/taac_env/bin/python}"
exec "$PYTHON_BIN" "$BACKEND_DIR/run_local.py" start
