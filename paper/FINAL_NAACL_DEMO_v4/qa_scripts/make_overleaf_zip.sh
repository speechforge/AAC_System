#!/usr/bin/env bash
# Package the LaTeX source as an Overleaf-ready zip (root = main.tex; compile with XeLaTeX) and prove that the zip compiles standalone.
# Usage: make_overleaf_zip.sh <latex_source_dir> <out.zip>
set -euo pipefail
SRC="$(cd "$1" && pwd)"; OUT="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
rm -f "$OUT"
( cd "$SRC" && zip -qr "$OUT" main.tex acl.sty acl_natbib.bst references.bib build.sh README_BUILD.md sections generated figures fonts )
TMP="$(mktemp -d)"; unzip -q "$OUT" -d "$TMP"
( cd "$TMP" && TECTONIC="${TECTONIC:-tectonic}" ./build.sh >/dev/null 2>&1 && pdfinfo main.pdf | grep Pages ) || { echo "standalone compile FAILED"; exit 1; }
echo "zip ok: $OUT"; rm -rf "$TMP"
