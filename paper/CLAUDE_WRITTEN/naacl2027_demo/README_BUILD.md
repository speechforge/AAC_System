# Build instructions (Overleaf-ready)

Main file: `main.tex`. Compiler: **XeLaTeX** (or LuaLaTeX); the manuscript contains Hindi, Gujarati and Marathi text, which needs the Unicode workflow of the official `acl_lualatex.tex` template.

- Overleaf: upload this ZIP, set *Menu > Compiler > XeLaTeX*, main document `main.tex`, then Recompile.
- TeX Live: `xelatex main && bibtex main && xelatex main && xelatex main`
- Tectonic: `./build.sh` (set `TECTONIC=/path/to/tectonic` if it is not on PATH).

Contents: `acl.sty` and `acl_natbib.bst` are unmodified copies of https://github.com/acl-org/acl-style-files (upstream commit d5adc823ff, checked 2026-11-12); `fonts/` holds Noto Sans Devanagari and Gujarati (SIL OFL 1.1, see `fonts/README.txt`); `figures/` holds the compiled vector figures; `generated/` is regenerated from the evaluation results by `eval/make_tex.py` in the full package and must not be edited by hand. `\usepackage[preprint]{acl}` shows author names (single-blind demo track); the author block in `main.tex` is a placeholder.
