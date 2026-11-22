#!/usr/bin/env bash
# Local build with Tectonic (XeTeX). On Overleaf choose XeLaTeX (or LuaLaTeX) and main.tex.
# Alternatively with TeX Live:  xelatex main && bibtex main && xelatex main && xelatex main
set -e
cd "$(dirname "$0")"
TECTONIC="${TECTONIC:-tectonic}"
"$TECTONIC" -X compile --keep-logs main.tex
