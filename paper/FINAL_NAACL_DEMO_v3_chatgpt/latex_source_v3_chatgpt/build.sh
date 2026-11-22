#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
AAC_TECTONIC="${TECTONIC:-tectonic}"
"$AAC_TECTONIC" -X compile --keep-logs main.tex
