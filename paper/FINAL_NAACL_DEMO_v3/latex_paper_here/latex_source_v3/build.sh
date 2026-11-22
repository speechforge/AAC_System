#!/usr/bin/env bash
# Local build with Tectonic (XeTeX). On Overleaf choose XeLaTeX and main.tex.
# TeX Live alternative:  xelatex main && bibtex main && xelatex main && xelatex main
set -e
cd "$(dirname "$0")"
TECTONIC="${TECTONIC:-tectonic}"
"$TECTONIC" -X compile --keep-logs main.tex
