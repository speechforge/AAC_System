#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON_BIN="${AAC_PYTHON:-/home/linux/miniconda3/envs/taac_env/bin/python}"
mkdir -p "$PROJECT_DIR/.runtime/packages" "$PROJECT_DIR/.runtime/python" "$PROJECT_DIR/.runtime/redis"
cd "$PROJECT_DIR/.runtime/packages"
# Download/extract distribution binaries locally; this does not install system packages.
apt-get download redis-server redis-tools liblzf1 libjemalloc2
for package in ./*.deb; do dpkg-deb -x "$package" "$PROJECT_DIR/.runtime/redis"; done
PIP_CACHE_DIR="$PROJECT_DIR/.runtime/pip-cache" "$PYTHON_BIN" -m pip install --upgrade \
  --target "$PROJECT_DIR/.runtime/python" -r "$PROJECT_DIR/indic-generative-aac/backend/requirements-personal.txt"
echo "Local dependencies are ready. Start with:"
echo "$PYTHON_BIN $PROJECT_DIR/indic-generative-aac/backend/run_local.py start"
