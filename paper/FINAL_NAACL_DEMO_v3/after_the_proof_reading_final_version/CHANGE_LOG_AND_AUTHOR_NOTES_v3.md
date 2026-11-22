# Change log and author notes: v2 to v3 (after the five-agent proofreading)

Author-only record (not part of the manuscript). Date: 2026-11-14.

## 1. Outcome of the skill invocation
`/ravindras-paper-writing-skill` was invoked through the Skill tool in this session and loaded (active profile "full" per `skills/ACTIVE.md`; `SKILL.md` read by the main session). Agent 3 applied the skill's 17 non-negotiable rules, the output contract, and its scripts: `prose_lint.py` (0 high on every section; the two "implementation vocabulary" hits are the word "script" meaning writing system), `venue_check.py` (only the Responsible-NLP statement is a true flag, now answered in the Ethics Statement), `paper_check.py`. The main session re-ran `prose_lint.py` on the final sections: 0 high.

## 2. Files changed (all under `latex_source_final/` unless noted)
- `main.tex`: model-name macro `\llm` now `\mbox{\textsc{...}}`; hyphenation exceptions for Table, Tables, Figure, Appendix, Section; Figure 1 caption (conditions per row, color legend); header comments.
- `sections/00_abstract.tex` to `06_ack.tex`: rewritten or revised (scope of the gate, client-input evidence, speech routing, terminology glossary, tense, abbreviations). `05_repair.tex` retitled "Failure Audit and Repairs".
- `sections/07_appendix.tex`: first page is a full-width `\twocolumn[...]` block (Figure 4 and Table 5); Table 6 (new outcome kinds), Table 7 (compact, refiner results), Appendix B merged; per-family table parked in `latex_paper_here/unused_generated/`.
- `generated/tab_results.tex`, `tab_pred.tex`: relabeled; captions rewritten; Hindi bigram hit@1 corrected from 24.1 to 24.0 (586/2437 = 24.05%).
- `references.bib`: access-date notes in the required display ("Last Accessed Date: November 12th, 2026"; Jellow 13th), page dash, Nature Communications article number, arXiv identifiers, IndicF5 locator, two ACL Anthology entries added (Hokamp and Liu 2017; Post and Vilar 2018), Avaz FreeSpeech entry removed.
- `figures/`: `teaser.pdf` (verdict palette, legend in caption, input condition per row), `architecture.pdf` (no step numbers, "template fallback", gate labels), `fig4_languages.pdf` (new: four-language trace; English baseline, Hindi, Gujarati, Marathi proposed), `ui_panel.pdf` unchanged; v2 `workflow.pdf` removed.
- `figure_sources/`: `make_figures.py`, `make_fig4.py`, `diagramlib.py` (colored and italic text lines, vertical scaling, small-caps model names).

## 3. Checks run on the final build (`qa_scripts/`)
| Check | Result |
|---|---|
| Build (Tectonic 0.17.0, XeTeX) and standalone build from the zip | 10 pages, no errors, no missing glyphs; all fonts embedded |
| Page limits | main content ends on page 6 (about 2.8 spare lines, `true_slack.sh`); appendix pages 9-10 (about 2.7 spare lines) |
| `xref_audit.py` | all 12 floats and Equation 1 cited; 0 unresolved references or citation keys |
| `native_text_check.py` | 29/29 Hindi, Gujarati, Marathi strings recoverable from the PDF text; the three water sentences exact; no "चा हए" |
| `numbers_check.py` | all 7 rows of Table 2 reproduce from `scored.csv`; literal join 0/175, 215/215 |
| `extra_checks.py` | paired wins and losses, group bootstrap by language, gate precision and flips, client-input provenance 184/184 |
| Text-level | `prose_lint.py` 0 high; long-sentence notes (low) remain in a few Ethics and Appendix sentences |

## 4. Claims updated and their evidence
See `CLAIM_EVIDENCE_MAP_v3.md`.

## 5. Dependencies still pending (author actions)
1. Release package: the repository is public but holds the 2026-11-11 snapshot without LICENSE, scenarios, scorer, raw outputs, or video; README claims ("zero-hallucination", English speech) contradict the paper.
2. Audible speech and a narrated screencast (IndicF5 weights are gated; or make the server return no audio when the model is absent so browser voices speak). Title decision depends on this.
3. Native-speaker confirmation of gold and templates; blind ratings (packet built, ratings pending); no holdout score is in the paper.
4. Figure 3 recapture from the repaired build.
5. Provenance and consent of default reference clips; licence of the synthetic dialogues; which original code was AI-assisted (Acknowledgements).
6. Confirm author affiliations and order, `\codelicense`, and the Availability wording once the package is complete.
7. Not feasible now: Gujarati and Marathi columns in Table 3 (no AAC corpus exists).

## 6. Addendum (2026-11-14): UTMOS22 and NISQA evaluation of the speech samples
Requested after the five-agent proofread. **IndicF5 speech does not exist yet** (weights gated; the evaluated build returned a 440 Hz placeholder tone), so the table scores what exists and says so.
- New: `mos_eval/` (`build_audio.py`, `score_mos.py`, `make_mos_table.py`, `check_mos.py`, `synth_indicf5.py`, `README_MOS.md`, `audio/` with 184 clips and `manifest.csv`, `mos_scores.csv`, `standin_vocab_loss.csv`); `generated/tab_mos.tex` and `generated/mos.tex` (written by `make_mos_table.py`, included from the appendix); three verified references (`saeki2022utmos`, `mittag2021nisqa`, `pratap2023mms`); macros `\utmos`, `\nisqa`, `\mmstts` in `main.tex`.
- Paper: Table 8 (Appendix B) with one explanatory sentence there and one in Limitations (Section 6). Abstract unchanged ("integrated but unverified, as no speech was produced" stays true).
- To fit the page limits (10 pages; appendix 3.1 spare lines; body 1.8 spare lines) the appendix was tightened. Detail dropped: Table 7 no longer names the IndicF5 training corpora ("1,417 h" only) and its Gutenberg/Hindi HMM row loses the word-type count and the role words; the Table 5 and Table 6 captions and the Figure 4 caption are shorter (the figure's own group labels already mark the baseline and the proposed languages); the runtime paragraph drops the 95th-percentile click-to-playback value (median 9.9 s stays) and the scorer paragraph reduces the first-person note to "(English only)". Row spacing and column widths of Tables 5 to 7 were tightened. Nothing in the evaluation or in a claim changed.
- Scores (UTMOS22 / NISQA v2): tone 1.54 / 1.12; human prompts EN 4.27 / 4.50, MR (3 clips) 3.20 / 4.81; default Punjabi prompt 3.83 / 4.74; stand-in voices EN 4.01 / 4.39, HI 3.66 / 3.52, GU 3.88 / 4.91, MR 3.31 / 3.95.
- Pending author action 8: accept the IndicF5 terms (huggingface.co/ai4bharat/IndicF5), install `f5_tts`, run `mos_eval/synth_indicf5.py`, then re-score; the table gains an IndicF5 column per language and the "not run" wording in Appendix B and Limitations must be revised.
- Caveats to keep: both predictors are trained on English ratings; NISQA scores signal quality, not naturalness (it rates the Gujarati stand-in 4.91 and the Hindi one 3.52); Pearson r between the two predictors is 0.47 over the 175 stand-in clips; the MMS voices drop punctuation, the danda and four vowel signs (`standin_vocab_loss.csv`); MMS-TTS weights are CC BY-NC 4.0.
