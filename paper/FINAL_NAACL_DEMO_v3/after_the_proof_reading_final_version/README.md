# Final v3 paper after the five-agent proofreading (2026-11-14)

Start here:
- `Indic_AAC_Studio_NAACL2027_Demo_v3_final.pdf`: the paper (10 pages: main content pages 1-6, Ethics, Acknowledgements and References pages 7-8, appendix pages 9-10).
- `FIVE_AGENT_REVIEW_REPORT.md`: the consolidated report (what is missing and the recommendations of all five agents, what was applied, what only the authors can do).

Sources and packaging:
- `latex_source_final/`: LaTeX source (compile with XeLaTeX; `README_BUILD.md` inside). `Indic_AAC_Studio_NAACL2027_Overleaf_v3_final.zip`: the same source for Overleaf.
- `figure_sources/`: scripts that draw Figures 1, 2 and 4 from the recorded outputs.
- `citation_records/`: citation verification notes (`citation_verification_v3_additions.md` lists the v3 checks).

Records:
- `CHANGE_LOG_AND_AUTHOR_NOTES_v3.md`: files changed, checks run, pending author actions.
- `CLAIM_EVIDENCE_MAP_v3.md`: each claim, its evidence file, and its status.
- `agent_reports/`: the five full reports (English writing, senior scientist, Ravindra skill, full professor, critic reviewer). `AGENT_BRIEFING.md`: the briefing they received. `review_input_v3_draft/`: the frozen draft they reviewed.
- `mos_eval/`: UTMOS22 and NISQA v2 evaluation of the speech samples (Table 8): audio, scores, scripts, `README_MOS.md` (what was scored, what was not, how to add IndicF5 speech).
- `qa_scripts/`: `finalize.sh` (rebuild, check, copy), `xref_audit.py` (every float cited), `native_text_check.py` (Indic text survives PDF extraction), `numbers_check.py` (Table 2 recount), `extra_checks.py` (paired counts, gate precision, payload provenance), `true_slack.sh` (spare lines at the page limits), `make_overleaf_zip.sh`.

Before submission the authors must: make the public repository match the paper (LICENSE, scenarios, scorer, raw outputs, install guide, video), make the demo audible, and confirm affiliations, license, and the Availability wording. See section 6 of the report; section 8 covers the speech-quality scores (IndicF5 itself still unscored).
