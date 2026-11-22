# Indic AAC Studio — ChatGPT Version 3 source

Main document: `main.tex`. Compile with XeLaTeX or Tectonic; the official ACL style files are unchanged. Fonts and their licence notice are bundled.

On Overleaf, choose **XeLaTeX** and `main.tex`. With TeX Live: `xelatex main`, `bibtex main`, `xelatex main` twice. Locally: `TECTONIC=/path/to/tectonic ./build.sh`.

Native Hindi, Gujarati, and Marathi text is upright in script-specific fonts. The wrapper adds UTF-16BE PDF ActualText spans so shaped Indic vowel signs remain searchable and copyable. After changing any native literal, run `python3 tools/prepare_unicode_chatgpt.py` from this source package before compiling (or update `generated/unicode_actualtext.tex`). LuaLaTeX has a separate font path but was not tested here; exact extraction checks apply to the verified XeTeX build.

Tables 2–4 and Figure 4 come from `figure_sources/build_evidence_assets_chatgpt.py`; the unmodified source results are hashed in `evidence/assets.source.json`. Regeneration needs the adjacent project repository. The supplied generated assets and bundled fonts make the LaTeX package independently compilable without rerunning evaluation.

The raw example strings are preserved, including malformed or awkward accepted model outputs. Blue/green denotes example/retained text, not native validation. Red additions are explicitly labelled. English is a reference-language row, while a matched template and ungated cascade are method baselines in every language.

This is an evidence-bounded manuscript revision, not a declaration of submission readiness. See the author revision note and QA results for native validation, speech, release, credit/licensing, and citation-verification dependencies. No unreviewed holdout scores are included.
