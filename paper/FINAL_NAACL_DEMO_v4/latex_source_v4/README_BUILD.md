# Indic AAC Studio, NAACL 2027 System Demonstration paper (v3, after the five-agent proofreading)

Main file: `main.tex`. Compiler: **XeLaTeX** (or LuaLaTeX). The manuscript contains Hindi, Gujarati and Marathi text and uses the Unicode workflow of the official `acl_lualatex.tex` template.

- Overleaf: upload the ZIP, set *Menu > Compiler > XeLaTeX*, main document `main.tex`, then Recompile.
- TeX Live: `xelatex main && bibtex main && xelatex main && xelatex main`
- Tectonic: `./build.sh` (set `TECTONIC=/path/to/tectonic` if it is not on PATH; about 3 s).

Layout: `sections/` holds the section bodies (`07_appendix.tex` opens the appendix with a full-width block through `\twocolumn[...]`); `generated/` holds the tables and number macros produced from the frozen evaluation (relabeled and re-captioned by hand in v3); `figures/` holds the vector figures (Figures 1, 2 and 4 come from `figure_sources/make_figures.py` and `make_fig4.py` in the full v3 folder, from recorded raw outputs; Figure 3 is a screenshot composite of the evaluated build); `fonts/` holds Noto Sans Devanagari and Gujarati (SIL OFL 1.1); `acl.sty` and `acl_natbib.bst` are the unmodified official ACL style files.

Build facts (2026-11-14, Tectonic 0.17.0): 10 pages. Main content (through the Conclusion) ends on page 6 with about 2.8 spare lines (measured with ragged-bottom columns, `qa_scripts/true_slack.sh`; the template is flush-bottom, which hides slack); Ethics Statement, Acknowledgements and References on pages 7-8; appendix pages 9-10 (limit: 2) with about 2.7 spare lines. A `\pdfstringdef` ActualText span around every Hindi, Gujarati and Marathi string keeps PDF text extraction in source order (29/29 strings recoverable, no damaged "chahie").

Before submission the authors must confirm: `\demourl` (the public package must contain the files the Availability paragraph lists, including a LICENSE file), `\codelicense`, the author affiliations and order, and the screencast statement in `sections/05_limits.tex` (currently "without audio").
