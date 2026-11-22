# Version 3 manuscript revision and validation

Updated November 13, 2026. This is an evidence-bounded author review revision, not a claim of submission readiness.

## Deliverables

- Compiled PDF: `Indic_AAC_Studio_NAACL2027_Demo_v3_review.pdf` in this folder.
- Editable paper: `latex_source_v3/main.tex`, nine section bodies, native-script fonts and their license, bibliography, and editable LaTeX diagrams.
- Portable source archive: `Indic_AAC_Studio_NAACL2027_Source_v3_review.zip` (root `main.tex`; choose XeLaTeX on Overleaf).
- Requested external copy: `/home/linux/Documents/aac_system_november_11/AAC_Sys_DEMO_v3/latex_paper_here/chatgpt_review_v3/`.
- Detailed scientific records: `claim_evidence_map.md`, `paper_story.md`, `reviewer_analysis_review.md`, `CREDITS_AND_LICENSE_REVIEW.md`, `citation_records/verification_review.md`, and `qa/review_validation.json`.

## Skill and source scope

Used the supplied `/home/linux/Documents/Paper_writing_skills/paper/paper_writing_skill_prof_patil-master/SKILL.md`, read its active full profile, router, targeted-revision, voice, section-blueprint, citation, Unicode, figure, and credits guidance. The PDF skill supplied render-and-inspect checks. No sub-agents were used for this revision.

The paper starts from FINAL_NAACL_DEMO_v2. The original Version 2 is preserved. The requested revision prompt was found in this folder's `prompt/`; it has also been copied to the requested external prompt directory. The root and v2 experiment handoffs were consulted. Existing frozen application repairs were described; this manuscript revision did not modify backend or frontend application sources.

## Framing and mini-outline

1. **Establish the problem without a semantic guarantee.** A short symbol selection needs act and polarity as well as lexical content.
2. **Position the contribution against existing AAC expansion and multilingual boards.** Compansion, Karmakar–Sinha, Jellow, SpeakFaster and ConnecTone supply the closest overlaps.
3. **Explain the actual decision path.** Separate concepts, act and polarity; check candidates and templates; expose clarification and literal previews.
4. **Lead with real browser inputs.** Retain the archived negative result against the template, and use gold fields as a diagnostic.
5. **Audit errors and show the repair boundary.** Separate scorer gaps from generation mistakes and regression from generalization.
6. **Make four-language behaviour reviewable.** Figure 4 and representative appendix cases show exact inputs, candidates, routes and outputs.

The complete revised prose is in the section sources and compiled PDF. The full claim-evidence matrix is in `claim_evidence_map.md`, and five adversarial questions with responses are in `reviewer_analysis_review.md`.

## Changes that matter scientifically

- The main comparison remains scorer-v1 archived browser input: cascade 65/175, policy 97/175, template 118/175. Its policy gain is +18.29 percentage points (group-bootstrap CI 11.86–25.15); the template deficit is −12.0 points (CI −17.94 to −6.40).
- Gold-field cascade/policy/template counts are 71/175, 132/175 and 167/175. Gold fields are explicitly a controlled diagnostic, not user-selected intent evidence.
- Retention is 215/215 concept instances, not 175/175 sentences. Zero scored polarity errors does not establish semantic safety; wrong-act, added-content, and accepted-output failures remain.
- All eight gold-field template failures are Gujarati negated-feeling scorer gaps. The audit's two accepted-model and six fallback scorer gaps are acknowledged. The 37/108 and 6/67 original failure counts retain their original scorer label.
- The 32-feeling diagnostic means eight single-symbol feelings across four locales before exclusions; 27 are sent as requests. The primary family contains 30 after exclusions.
- Scorer-v2 archived rescoring (95/175 browser, 138/175 gold) and repaired 175/175 hybrid/template are explicitly labelled regression. They are not mixed with scorer v1 to estimate a repair effect.
- No automatic success score from the draft 120-scenario holdout appears in the manuscript. Its native gold checks and human rating results remain pending.
- Table 3 reports 60 of 300 source conversations per language, with 240 training sources and context denominators. English/Hindi gains are computed from counts: 25/2220 and 29/2437, or 1.126/1.190 percentage points. The Hindi bigram value is corrected to count-derived 24.0% rather than 24.1%. Gujarati and Marathi are marked not evaluated.
- The 32 browser trials are placeholder-tone playback measurements. No real-speech latency or quality result is claimed. The clean CPU test reused cached weights; backend-local inference does not imply a fully offline browser.
- Unsupported release, first-party Apache-2.0 licensing, and semantic-guarantee claims are removed. Public package and video links are not invented.

## Multilingual and visual changes

Hindi, Gujarati and Marathi appear in the introduction, mechanism, error analysis, Figure 4 and Table 4. Language labels use bold italic emphasis, model names have restrained first-mention emphasis, and native scripts remain upright. English is the reference-language condition, while all three Indic conditions extend the same policy. It is not presented as a different baseline algorithm.

Red identifies rejected candidates or explicitly labelled unsupported additions/act cues. Blue denotes examples; green denotes returned text. Captions state that a returned or blue example is not a naturalness endorsement. Written verdicts preserve the distinction in grayscale.

Figure 1 is a compact concept illustration at the top right of page 1. Figure 2 explains the repaired workflow. Figure 3 transcribes two recorded interface states at readable size; the original captures are bundled. Figure 4 shows four languages through selection, first candidate, gate and returned text. Table 4 supplies one common message from each other scenario family. Examples preserve awkward model wording and errors.

The native text was correct in source but the initial XeTeX PDF extracted reordered glyphs incorrectly. A tested UTF-16 PDF ActualText span now preserves all 51 included native strings in extraction, including the exact three water sentences. The global XeTeX ActualText primitive produced malformed text on this Tectonic build and is not used.

## Checks run

| Check | Result |
|---|---|
| Tectonic 0.17.0 / XeTeX build | PASS; bibliography and references resolve |
| Main content | PASS; conclusion ends on page 6 |
| Ethics, acknowledgments and references | Page 7 |
| Appendix | PASS; pages 8–9, two pages |
| Figure 1 placement | PASS; top-right of page 1 |
| Included native strings | PASS; 51/51 recoverable exactly, ignoring layout whitespace |
| Water sentences | PASS; exact Unicode extraction for Hindi, Gujarati and Marathi |
| Fonts | PASS; 13/13 embedded |
| Missing glyphs / unresolved references / TeX errors | 0 / 0 / 0 |
| Official style files | PASS; byte-identical to the inherited ACL style files |
| Archived published-count audit | PASS; 20/20 reproduced claims match |
| Assets and labels | PASS; all referenced assets and labels resolve |
| Manuscript-section prose lint | PASS at high severity; language-script mentions generate five medium false positives |
| Visual inspection | All pages rendered; no clipping or visible overlap. An architecture arrow label was removed after inspection. |
| Final-column balance | One internal 2.19-point overfull vertical-box warning; rendered content stays inside the page and columns |
| New inference or human data collected here | None; evidence comes from the preserved experiment artifacts |

The raw skill readiness output is retained at `qa/paper_check_review.txt`: **NOT READY, five blocking gates and two warnings**. Its unresolved-marker gate flags the legitimate words “placeholder tone”; its prose pass scans supporting checklists and evidence notes as though they were manuscript prose. The generic venue checks assume another section naming convention and do not detect the existing Limitations/Ethics sections; they are supplemented by the manual current-call and PDF checks above. The build detector does not recognize Tectonic and reports “tex-unavailable”, despite the successful recorded Tectonic build. These limitations of the checker do not clear the genuine scientific and release blockers below.

## Remaining risks and blockers, ranked

1. **Independent native-speaker validation and human judgments.** The fresh holdout gold and the template–hybrid meaning/phrasing ratings are not complete. No naturalness, preference, generalization, or AAC-usability result can be claimed.
2. **Real speech and reviewer access.** IndicF5 weights or suitable browser voices, four-locale speech checks, an accessible package/demo link, and a verified video are still needed.
3. **Two citation cross-checks.** Karmakar–Sinha (ICON 2024) and ConnecTone (Interspeech 2024) are verified against primary records and read content, but an independent full-metadata index match was not obtained. Both remain `single-source` in the citation lock and fail the strict citation gate. Their sources are real; no secondary match was invented.
4. **Author contributions, funding, and first-party license.** The author block is unchanged, but individual CRediT roles, funding details and release rights require author confirmation. They have not been assigned by inference.
5. **Comparison scope.** The unconstrained one-prompt baseline does not establish superiority to a matched few-shot one-pass realizer. The template comparison remains a central negative result.

No reviewer score or acceptance prediction was fabricated. This deliverable is a compiled revision for author review, not a statement that these dependencies are resolved.
