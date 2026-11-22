# Briefing for the five reviewers (read this first)

**Paper.** *Indic AAC Studio: Concept-Gated Symbol-to-Speech Generation for English, Hindi, Gujarati, and Marathi*; NAACL 2027 **System Demonstrations** track (single-blind; deadline 2026-12-04, 11:59 p.m. UTC-12). Authors: R. M. Purohit, J. Parmar, H. A. Patil.
**Goal.** Turn the current draft into a paper that a demo-track program committee accepts. An earlier reviewer-style assessment scored it **68/100, Weak Reject**; the assessment and the requested fixes are reproduced at the end of this file.

## What you review
Frozen draft (do **not** edit anything here; write only your own report):
- PDF: `review_input_v3_draft/Indic_AAC_Studio_NAACL2027_Demo_v3_DRAFT_for_review.pdf` (10 pp.: body pp. 1-6, Ethics/Acknowledgements/References pp. 6-8, appendix pp. 9-10)
- LaTeX: `review_input_v3_draft/latex_source/` (`main.tex`, `sections/00_abstract.tex ... 07_appendix.tex`, `generated/*.tex` = tables and number macros produced from the evaluation files, `references.bib`, `figures/`)
- Text dumps: `review_input_v3_draft/draft_text_layout.txt`, `draft_text_flow.txt`; figure sources: `review_input_v3_draft/figure_sources/` (Figure 1, 2 and 4 are drawn from recorded outputs)
- Absolute base directory: `/home/linux/Documents/aac_system_november_11/AAC_System_merged/paper/FINAL_NAACL_DEMO_v3/after_the_proof_reading_final_version/`
- QA scripts you may run: `qa_scripts/xref_audit.py <latex_source>`, `qa_scripts/native_text_check.py <latex_source> <pdf>`, `qa_scripts/page_slack.py <pdf> 6`
- Build (only if you copy the source elsewhere first): Tectonic at `/usr/lib/chatgpt/resources/plugins/openai-bundled/plugins/latex/bin/tectonic`, then `TECTONIC=<that path> ./build.sh` inside a copy of `latex_source/` (XeTeX; takes ~3 s).
- Render pages to look at them: `pdftoppm -r 110 -png <pdf> /tmp/<name>` and open the PNGs.

## Evidence (verify claims against these, never against memory)
- Experiment record of the repair phase: `/home/linux/Documents/aac_system_november_11/AAC_System_merged/FINAL_CONTEXT.md` (sections 5-10 hold the audit, repairs, regression, negative results, limits, open gaps).
- Archived evaluation (the numbers in Tables 2-4): `/home/linux/Documents/aac_system_november_11/AAC_System_merged/paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results/` (`scored.csv` one row per scenario/system/condition, `raw_pipeline.jsonl`, `prediction.json`, `hmm_eval.json`, `summary.json`, `offline_check.json`).
- Audit and repair artifacts: `/home/linux/Documents/aac_system_november_11/AAC_System_merged/udpated_version_context_of_papers/v2/results/audit/` (A1_claims_check.csv, A2 exclusions, A3 failure classification, A6 feeling denominator, A7 paired CIs, A8 prediction counts, B_* repair checks, B_speech_path.json, D_clean_env_test.json) and `.../v2/results/tables/`.
- System code: archived system `.../udpated_version_context_of_papers/v2/archived_system/indic-generative-aac/backend/` (`semantic.py` is the evaluated gate, `llm.py` the cascade); repaired system in `/home/linux/Documents/aac_system_november_11/AAC_System_merged/indic-generative-aac/backend/`.
- Call for papers: https://2027.naacl.org/calls/system_demonstration/ (6 pages main content, 2-page appendix, ethics/references unlimited, 2.5-min video, live demo or installable package link, AI use disclosed in Acknowledgements).
- Writing skill: `/home/linux/.claude/skills/ravindras-paper-writing-skill/` (SKILL.md and references/).

## Constraints the revision must respect
1. **Page limit is hard**: body through the Conclusion <= 6 pages (currently ends on p. 6 with ~4 lines to spare); appendix <= 2 pages (full). Every addition you propose needs an offsetting cut; state the net line count of each edit.
2. Never invent a number, citation, URL, or result. Holdout scores are deliberately excluded (gold annotation awaits native-speaker confirmation). 175/175 is a regression target, not a result. 8/175 is the unconstrained-prompt result.
3. Style: concise, formal ACL prose; US English; no coding vocabulary in the prose (no file/function/flag names); HMMs are **trained** components (never write that "nothing is trained"); model names are set in small capitals through macros (user request); native-script examples are upright with a bold-italic language label and an italic English gloss; **green/blue = correct or selected, red = unwanted addition or wrong act**.
4. Official ACL style files are unmodified; XeLaTeX/Tectonic Unicode workflow.
5. Already-known open items (do not report as new discoveries, but you may rank them): public release URL is private (404) and no licence file exists; the screencast is silent (IndicF5 weights gated, no real speech verified); no native-speaker ratings or native-checked gold; Gujarati/Marathi next-word prediction cannot be evaluated (no AAC dialogue corpus), so Table 3 covers English and Hindi only; two citations (Karmakar-Sinha, ConnecTone) have a single-source verification.

## What the user asked for (this session)
Highlight model names in small caps; show Hindi, Gujarati and Marathi examples together (never one language alone) in results and analysis, red for unwanted additions, green/blue otherwise; Figure 4 with all four languages (English = baseline, Hindi/Gujarati/Marathi = proposed); extend Table 3 to Gujarati/Marathi only if results exist (they do not); scenario examples and test cases of each kind in the appendix; a short empirical-results-and-repairs section; make the paper beautiful; every figure/table cited in the text; arrangement that leads to acceptance; proofread.

## Output format (mandatory)
Write **one Markdown file** to `agent_reports/<your-file-name>.md` (name given in your task) and end with a final message of <= 250 words that states the file path, your verdict, and your 5 most important findings. Structure of the file (<= 1,700 words):
1. **Verdict and score** from your viewpoint (use the 100-point rubric below where relevant).
2. **What is missing**, ranked P0 (blocks acceptance), P1 (should fix), P2 (polish), each with location (file, section, line or caption) and why it matters.
3. **Concrete edits**: exact old text -> new text (quote the source), with net line change; group by file. Prefer edits that are line-neutral.
4. **Claims checked** (table: claim | evidence file | status = verified / wrong / unverifiable | correction).
5. **Questions to the authors** (<= 5).
Be specific, evidence-based and unsparing; do not pad. Think deeply and verify before asserting.

## Rubric used by the earlier assessment (100 points)
Problem and track fit 15; Technical contribution 20; Experimental evidence 30; Demo and reproducibility 15; Writing and presentation 20.

## The earlier assessment (verbatim summary)
68/100 Weak Reject. Problem/track fit 14/15; technical contribution 13/20 (gate and fallback are concrete; strongest novelty = design and evaluation for Indic symbol-to-speech); experimental evidence 18/30 (gating helps the cascade; the deployed system trails the template; lexical scorer leaves naturalness unmeasured); demo and reproducibility 10/15 (end-to-end speech and clean installation open); writing 13/20 (tighter claims about the gate, clearer input-condition labels, consistent multilingual typography). Web client: ungated 65/175, deployed 97/175, template 118/175 (deployed vs template -12.0 pp); explicit fields: 71/175, 132/175, 167/175 (-20.0 pp). 37 of 108 accepted outputs failed the full scorer even with gold inputs. Keep 8/175 for the unconstrained prompt; use 175/175 as a regression target. Most likely to move toward Accept: a fresh paired comparison showing the revised hybrid preserves meaning as reliably as the repaired template and that native speakers prefer its phrasing.
Fixes requested: (1) lead with web-client results, use gold fields as a diagnostic, state 215/215 retention and zero polarity errors on the benchmark, then report wrong-act and added-content errors, replace absolute guarantees by what the gate checks; (2) sharpen novelty (Compansion, Karmakar-Sinha incl. Bengali, Jellow's sentence construction and Gujarati/Hindi/Marathi support) toward how candidate sentences are checked and what the paired evaluation reveals; (3) resolve ambiguities: define off-task model refusal vs valid user refusal, explain the 32 feeling selections vs Table 4's 30, check hit@1 differences against unrounded counts, verify by scenario ID that all eight gold-field template failures are Gujarati negated feelings; (4) specify what actually speaks per language, verify the English route, distinguish text-generation latency from time to audible speech and backend-local inference from CDN dependence; introduction example for a water request with language labels set apart, native text upright, italic English gloss; check the Hindi extraction damage ("चा हए") in source and PDF; official ACL Unicode template with XeLaTeX or LuaLaTeX; restrained emphasis on first mention of model names at body size.
