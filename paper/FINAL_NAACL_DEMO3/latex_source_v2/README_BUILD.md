# Indic AAC Studio, NAACL 2027 System Demonstration paper (v2)

Main file: `main.tex`. Compiler: **XeLaTeX** (or LuaLaTeX). The manuscript contains Hindi, Gujarati and Marathi text and uses the Unicode workflow of the official `acl_lualatex.tex` template.

- Overleaf: upload this ZIP, set *Menu > Compiler > XeLaTeX*, main document `main.tex`, then Recompile.
- TeX Live: `xelatex main && bibtex main && xelatex main && xelatex main`
- Tectonic: `./build.sh` (set `TECTONIC=/path/to/tectonic` if it is not on PATH).

Layout: `sections/` holds the section bodies; `generated/` holds the numbers and tables produced from the frozen evaluation (do not edit numbers by hand; v2 changed two label or caption strings only, no number); `figures/` holds the vector figures (the teaser, architecture and trace figures are produced by `figure_sources/make_figures.py` in the full v2 folder from the recorded raw outputs); `fonts/` holds Noto Sans Devanagari and Gujarati (SIL OFL 1.1); `acl.sty` and `acl_natbib.bst` are the unmodified official ACL style files.

Build facts (2026-11-12, Tectonic 0.17.0): 10 pages; body (through the Conclusion) ends at the bottom of page 6; Ethics Statement, Acknowledgements and References on pages 7-8; appendix pages 9-10 (limit: 2). The font name `TeXGyreTermesX` follows the official `acl_lualatex.tex`; v1 used a different name that did not resolve in Tectonic. `\usepackage[preprint]{acl}` shows author names (single-blind demo track); confirm against the OpenReview instructions.

Before submission the authors must set `\demourl` (public release location) and confirm `\codelicense` in `main.tex`, and confirm the author affiliations and order (author block: three authors, two title rows, `\titlebox` set to 13 line-heights).
