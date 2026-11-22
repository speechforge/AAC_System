# ChatGPT Version 3 — revision and evidence handoff

**Deliverable:** compiled manuscript revision, editable LaTeX/BibTeX/figures, evidence tables and traces, source ZIP, and author notes. **Scientific status: not submission-ready.** The available evidence does not justify claims of native-judged generalization, superior phrasing, AAC usability, real speech, or a public release.

## Files and locations

- `Indic_AAC_Studio_NAACL2027_Demo_v3_chatgpt.pdf`: the compiled paper.
- `latex_source_v3_chatgpt/main.tex`: canonical source for this revision; `sections/`, `generated/`, `figures/`, `fonts/`, and `references.bib` are editable.
- `Indic_AAC_Studio_NAACL2027_LaTeX_v3_chatgpt.zip`: standalone XeLaTeX/Overleaf sources, bundled fonts, and exact-Unicode helper.
- `plan/section_mini_outlines_chatgpt.md`, `plan/paper_story_chatgpt.md`, `plan/claim_evidence_map_chatgpt.md`, `plan/adversarial_self_review_chatgpt.md`: the writing skill's outline, narrative, claim matrix, and skeptical review.
- `figure_sources/build_evidence_assets_chatgpt.py`, `prepare_unicode_chatgpt.py`, `verify_evidence_chatgpt.py`: deterministic tables/traces, PDF Unicode preparation, and independent release checks.
- `evidence/`: exact counts, paired intervals, prediction audit, test-tone audit, original trace strings, and source hashes. No draft holdout performance is packaged.
- `qa/evidence_verification_chatgpt.json`, `evidence_verification_chatgpt.txt`, `fonts_chatgpt.txt`, `manuscript_prose_chatgpt.txt`, `citation_check_chatgpt.txt`, `skill_ready_chatgpt.txt`: checks and their actual outcomes.
- A matching PDF, main source, fonts, figures, ZIP, and this note are copied to `/home/linux/Documents/aac_system_november_11/AAC_Sys_DEMO_v3/latex_paper_here`.

Concurrent source edits were detected in `latex_source_v3`. They were preserved, and this revision was built independently in `latex_source_v3_chatgpt`. Version 2 and application code were not changed by this revision.

## Skill and prompt used

The user-supplied skill at `/home/linux/Documents/Paper_writing_skills/paper/paper_writing_skill_prof_patil-master/SKILL.md` was available and used, with ACTIVE.md's full profile and the targeted-revision journey. Reviewer, prose, section, citation, Unicode, figure, and credit guidance was read. The PDF skill was used for rendering and visual QA. No subagents were used.

The requested sibling revision prompt was initially absent. The matching prompt in `paper/FINAL_NAACL_DEMO_v3_chatgpt/prompt/AAC_02_NAACL_Manuscript_Revision.md` was read and copied to the requested sibling `prompt/` directory.

## What changed and why

1. The abstract and results now lead with the archived actual-browser comparison, 65/175 → 97/175 versus 118/175 for the matched template. Gold act/polarity remains a controlled diagnostic: 71/175 → 132/175 versus 167/175. The full gate/retry/fallback policy is named as the intervention.
2. The main claim is an inspectable acceptance policy and its audit. Compansion, Karmakar and Sinha's Bengali work, Jellow Basic's Hindi/Gujarati/Marathi support, SpeakFaster, and ConnecTone bound the novelty. Unsupported first-system and model-quality claims were removed.
3. Hindi, Gujarati, and Marathi are labelled consistently in the introduction, method, and failure analysis. Native text stays upright; labels are bold italic, English glosses italic, and model names receive restrained first-mention emphasis at body size.
4. Figure 4 contains two recorded selections in all four languages, each with selection → candidate → check/route → returned text. English is the reference-language row, not a competing algorithm. Every language uses the same method baselines. Red content is explicitly labelled as an addition; blue/green examples do not imply native validation.
5. The appendix samples all six archived scenario families in all four languages: request, refusal, feeling, negated feeling, action–object, and call/help-to-person. Awkward accepted outputs are preserved verbatim. Clarification and server-unavailable behavior are discussed separately.
6. Revised scores are explicitly regression evidence on the same 175 cases that informed repairs. Scorer v1 and v2 are separated. Revised cascade 88/175; hybrid and repaired template 175/175. The fresh 120-case set is described as awaiting native gold confirmation; its scores and preference claims are excluded, following `udpated_version_context_of_papers/v2/sections/GAPS.md`.
7. The feeling diagnostic denominator is 32 isolated symbol–locale selections, not the 30 evaluated feeling scenarios. The eight Gujarati gold-field template failures are identified as scorer lexical gaps. Off-task model refusal is distinguished from a user's valid refusal.
8. Table 3 specifies **60 of 300 source conversations** per evaluated language, 240 train / 60 test, with 2,220 English and 2,437 Hindi contexts. Raw-count gains are +1.126 and +1.190 percentage points. Gujarati/Marathi coverage is shown as unmeasured, with no invented scores.
9. Speech routing and missing weights are described honestly. All 32 browser runs played a 440 Hz test tone; the reported warm median 9.9 s and p95 20.8 s end at an audio playback event. The title and verified scope therefore concern symbol-to-sentence generation. Backend-local execution is separated from CDN-dependent browser assets.
10. Unverified public release and Apache licensing claims for project assets were removed. AI use is disclosed in Acknowledgments; no author-specific CRediT roles, funding, licence grant, human ratings, or native judgments were invented.

## Validation and limits

| Check | Actual outcome |
|---|---|
| XeTeX/Tectonic build | Compiled successfully using Tectonic 0.17.0; official ACL style hash matches upstream |
| Content layout | Six pages through the conclusion and AI acknowledgment; ethics and references outside main content; two appendix pages |
| Visual QA | Every rendered page inspected; Figure 1 is at top-right on page 1; Figure 4 begins the appendix |
| Build diagnostics | Zero overfull boxes, missing-glyph warnings, or undefined references/citations |
| Font embedding | All 13 fonts embedded, with Unicode maps |
| Native-script source/PDF | All 47 native literals match Poppler extraction exactly, including Hindi `चाहिए`, Gujarati `જોઈએ`, and the three water sentences |
| Secondary extraction | pypdf still misreads a shaped Hindi i-vowel glyph as IPA `ɟ` because it does not honor every ActualText span. This is an extractor limitation; it is recorded, not counted as a pass |
| Evidence verification | 23/23 checks pass: exact scenario counts, independent regression summary, prediction counts, four-language/six-family coverage, Unicode, page allocation, font embedding, and compile diagnostics |
| Scientific prose lint | Zero high findings in manuscript section/figure/table sources. Two medium hits are the linguistic word “script”; low findings are retained in the report |
| Citation syntax | All eight cited keys resolve and compile; no unresolved LaTeX citation |
| Citation integrity | Seven resources verified/documented; **Karmakar and Sinha (2024) remains primary-only**. Its real ACL record, BibTeX, and abstract support the statement, but OpenAlex/DBLP did not resolve an independent record and Semantic Scholar was rate-limited |
| Skill `paper_check.py ... ready` | Executed and saved verbatim; **NOT READY**. Citation and CRediT dependencies remain. Its broad prose scan includes author build notes, its venue checks expect scaffold-specific filenames, and its build detector does not recognize Tectonic. These tool limitations do not replace the explicit checks above |

The current [NAACL 2027 demonstration call](https://2027.naacl.org/calls/system_demonstration/) and [official ACL Unicode example](https://github.com/acl-org/acl-style-files/blob/master/acl_lualatex.tex) were checked on November 13, 2026. Single-blind author names, six content pages, two appendix pages, AI disclosure, video length up to 2.5 minutes, and a usable demo/package link were checked against that call. No claim is made that the required public links have been supplied.

## Ranked remaining scientific and submission dependencies

1. **Native review and fresh generalization:** two native speakers per language must confirm the new gold annotation; then re-score and collect the blind meaning/phrasing judgments. The same authoring assistant developed rules/gold/scoring, so independent review matters. No new GPU or human experiment was run during this manuscript revision.
2. **Actual speech and accessible demo:** obtain authorized IndicF5 weights or working locale voices, verify actual speech in each language, and provide a working installable/demo link and a suitable video. Test first-time download and a clean GPU install. The present test tones are not speech evidence.
3. **Credits and licensing:** authors must supply actual CRediT roles and confirm release rights/licences for project code, synthetic data, paper/figures, and media; no funding statement is inferred.
4. **Citation cross-check:** resolve an independent bibliographic index for Karmakar and Sinha (2024), or explicitly waive that skill gate on the strength of its checked primary record. The reference is not fabricated.
5. **Other coverage:** Gujarati/Marathi prediction, target-user usability, native phrasing quality, and offline frontend operation remain unmeasured. Template/hybrid lexical ties do not show a phrasing preference.

These dependencies remain outside the manuscript's claimed findings. The manuscript revision is delivered with them explicitly recorded rather than converted into stronger results.
