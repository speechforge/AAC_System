#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -n "${AAC_TECTONIC:-}" ]]; then
  "$AAC_TECTONIC" -X compile --keep-logs main.tex
elif command -v tectonic >/dev/null 2>&1; then
  tectonic -X compile --keep-logs main.tex
elif command -v xelatex >/dev/null 2>&1; then
  xelatex -interaction=nonstopmode -halt-on-error main.tex
  bibtex main
  xelatex -interaction=nonstopmode -halt-on-error main.tex
  xelatex -interaction=nonstopmode -halt-on-error main.tex
else
  printf '%s\n' 'Use XeLaTeX on Overleaf, or install Tectonic/XeLaTeX.' >&2
  exit 1
fi
