# Indic AAC Studio, NAACL 2027 demo: v1 review, v2 change log, and blockers

Editorial file for the authors; none of it belongs in the manuscript. Written 2026-11-12. Skill used: `ravindras-paper-writing-skill` (profile: full), journey = draft review + targeted revision (`references/20`, `10`, `04`).

**Deliverables (this folder)**
| File | What |
|---|---|
| `Indic_AAC_Studio_NAACL2027_Demo_v2.pdf` | v2 manuscript, 10 pages (body 1-6, Ethics/Acknowledgements/References 6-8, appendix 9-10) |
| `Indic_AAC_Studio_NAACL2027_Overleaf_v2.zip` | manuscript sources only; builds from a clean copy (Tectonic 0.17.0, text identical to the PDF) |
| `latex_source_v2/` | same sources, working copy |
| `figure_sources/make_figures.py` | regenerates the teaser, architecture and trace figures from the recorded raw outputs |
| `CLAIM_EVIDENCE_MAP_AND_SELF_REVIEW_v2.md` | claim matrix, adversarial self-review |
| `citation_records/` | double-verification report and lock for 9 references |

## 0. Flagged assumptions (redirect me if wrong)
1. v1 is the base: it already merged the Claude draft (frozen protocol, five systems, tables) and the ChatGPT draft (interface walkthrough, explicit-versus-inferred framing, interface probes). v2 does not re-merge; it repairs v1.
2. Framing unchanged: the paper's contribution is the **selection contract** (ledger, gate, template floor) with an honest evaluation, not a quality gain over templates. Contributions cut from four to three.
3. I changed no number. `numbers.tex`, `extra.tex`, `tab_type.tex` are byte-identical to v1; two hand-edited strings (a row label in Table 2, a caption sentence in Table 3) are listed in section 3.
4. Authors (added on your request): Ravindrakumar M. Purohit (Speech Research Lab, Dhirubhai Ambani University (DA-IICT), Gandhinagar), Jaydeep Parmar ("PDEU" expanded by me to Pandit Deendayal Energy University, Gandhinagar; no department given), Hemant A. Patil (same lab and wording as the first author, from the skill's Patil-lab material). No e-mail addresses. Please confirm the affiliations and the order. The release URL, licence and screencast are still the v1 values (section 5).

## 1. Review of v1 (evidence-first; simulated reviewer, not a venue decision)
Coverage: v1 PDF and sources, claim map, ChatGPT and Claude drafts, Claude `FINAL_CONTEXT.md`, raw evaluation files (`scored.csv`, `raw_pipeline.jsonl`, `hmm_eval.json`, `reliability_ui.json`), the deployed validator (re-run on three recorded candidates). Not read: the OpenReview portal; the NAACL call page beyond what `FINAL_CONTEXT.md` records.

**Strengths.** (S1) Frozen, paired protocol with matched baselines; I recomputed every success, polarity, wrong-act, no-act, added and off-task count of Table 2 from the 2,100 primary scored rows and all match. (S2) The negative result (template alone beats the pipeline) is stated up front. (S3) Scoped related-work claims ("documented capabilities", `n.s.`). (S4) Limitations are specific.

| ID | Location (v1) | Observation | Severity | v2 action |
|---|---|---|---|---|
| M1 | whole paper, 3 figures | 25 high-severity coding-vocabulary hits (endpoint names, field names, file paths, a commit hash, a model repository id); the architecture figure labelled "FastAPI app.py", "localStorage", "Git LFS"; the trace figure printed `intent=… entities=[…]` | high (skill hard rule) | all text and figures rewritten in plain language; lint now 0 high |
| M2 | Sec. 4 RQ4 | "HMMs trained on … the Hindi dialogues alone are weaker … which supports training on in-domain AAC dialogues." The Hindi HMM *is* in-domain (24.5% hit@1 vs trigram 25.9%, trie 27.0%), so the inference does not follow; only the out-of-domain Gutenberg HMM (6.7%) supports it | high (claim not supported) | sentence replaced by the exact numbers, no inference |
| M3 | Table 3 caption | "all models share the training split": false for the Gutenberg HMM (trained on 188,402 book sentences, `hmm_eval.json`) | medium | caption corrected |
| M4 | Abstract | "IndicF5 voices the result" while the evaluated build ran without IndicF5 weights (placeholder tone) and the screencast is silent | high (unsupported implication) | abstract states speech is integrated but not evaluated; Limitations: "speech quality was not assessed" (v1 said it "is that of IndicF5 as released", which no run showed) |
| M5 | Conclusion | "the template floor guarantees a valid sentence": contradicted by the paper's own finding that the template returns "I want No Pizza." and is returned without re-validation | high (overclaim) | "the template floor speaks only the user's own labels" |
| M6 | Limitations | HMM-1 and HMM-2 are listed as components, but the evaluated build ran without their checkpoints (private LFS objects) | medium | stated explicitly in Sec. 3 and Limitations |
| M7 | Teaser | Figure 1 (architecture) sat on page 4; the introduction's three failure examples were only prose | medium | new page-top teaser (page 2; see note) built from three recorded requests and the deployed validator: two rejections, one gate miss |
| M8 | Appendix trace figure | included at about 0.5 text width: type rendered at about 4 pt | medium | redrawn at full width (type about 7 pt); architecture figure redrawn without code vocabulary (type about 6.5 pt, v1 about 6 pt: still small, enlarge if space allows) |
| M9 | Protocol | "We froze 184 scenarios" omits the 8 Hinglish ones (the ChatGPT draft says 192) | low | "184 monolingual and 8 exploratory Hinglish" |
| M10 | Sec. 5 | accessibility wording omitted measured facts (no live region, no explicit labels, blank page without CDNs) | low | added from `reliability_ui.json`; see note 2 below |
| M11 | Font | `\babelfont{rm}{TeX Gyre Termes}` fails in Tectonic ("font cannot be found"); the official ACL Unicode template uses `TeXGyreTermesX` | medium (build) | switched to the official name |
| M12 | Reference | Karmakar and Sinha lacked pages; authors came from the ChatGPT bib | low | re-read on the ACL Anthology: authors, venue, publisher match; added December 2024 and pages 324-331 |
| M13 | Intro | four contributions, the fourth the evaluation; results repeated in a closing paragraph | low | three contributions; the findings now sit in the third |
| M14 | Hard-coded numbers | "215" typed in text (abstract, RQ1) | low | macro `\NConc` (denominator of Table 2, Kept column) |

Notes. (1) Page 1 keeps the abstract and introduction; a two-column float spanning both columns cannot be placed on page 1 by the official style, and the title block there has a fixed height, so the teaser is the first float on page 2. I did not alter the style file. (2) The ChatGPT draft states that sequential tabbing did not reach the symbol grid. That claim rests on `focus_reaches_symbol_cards: false`, which `reliability_ui.py` computes by exact text match against "Yes", "No", "Want", "Help", while the tab stops carry an emoji prefix ("👍 Yes"); the recorded stops do include those cards. I therefore did **not** carry the claim into v2; only measured facts are stated. A proper tab-order probe is still worth running.

## 2. Merge provenance (what each source contributed)
- **Claude draft:** the frozen scenario protocol, the five systems, Tables 2-5, trained-component table, figures, verified bib, all result files.
- **ChatGPT draft:** intent inferred versus explicit as the central experimental contrast, interface walkthrough, "UI" and "explicit" conditions, latency table, probes; its Dryer (word order) and ASHA (AAC definition) citations were not carried into v1 and I did not restore them (not verified here).
- **v1:** rebuilt related-work table from vendor pages; dropped unverifiable claims (Census speech-impairment counts, SpeakFaster percentages, Vertanen coverage).

## 3. Change log v1 to v2 (claims, not words)
- **Weakened:** speech (abstract and Limitations); template "guarantees" (Conclusion); HMM inference (RQ4).
- **Removed:** the appendix UI-failure screenshot (the teaser row 3 shows the same recorded request; file kept in `figure_sources/unused/`); the per-language paired gains over the unconstrained prompt (kept in `numbers.tex`, dropped from the text for space); the Hinglish sentence moved to Appendix B.
- **Added:** teaser figure; accessibility measurements; HMM-1/HMM-2 absence; explicit "under explicit fields" qualifier on the template's 95% in the abstract.
- **Hand-edited generated strings (no number changed):** Table 2 row label ("explicit intent and negation fields", no code font); Table 3 caption (training data of each model).
- **Authors:** second and third author added; the title box is enlarged to 13 line-heights (the adjustment the official template allows) and the body was trimmed by about five lines (availability and limitations wording, two related-work sentences) so the Conclusion still ends on page 6.
- **Layout:** body ends before the bottom of page 6 (limit 6 pages plus unlimited ethics and references); appendix exactly 2 pages (limit 2).

## 4. Checks run
| Check | Result |
|---|---|
| Build (Tectonic 0.17.0, XeTeX), clean-copy from the zip | pass; 10 pages; text identical to the delivered PDF; no undefined references or citations; no overfull box above 5 pt |
| `prose_lint.py` | 0 high; 2 medium (the word "script" meaning writing system), 6 low (long sentences). v1: 25 high |
| Table 2 recount from `scored.csv` | all cells match |
| Numbers files vs v1 | `numbers.tex`, `extra.tex`, `tab_type.tex` identical |
| `citations.py verify` (9 entries with an identifier) | 7 verified (two independent indexes); Qwen2.5 report: *conflict* confined to the first-author field (Semantic Scholar) while title, year and arXiv id agree, and v1 already cites the institutional author; Karmakar and Sinha: single index (ACL Anthology, re-read by hand) |
| Other 8 references (ISCA pages, vendor pages, IndicF5 repository, news article) | no index record exists; they were read from their pages on 2026-11-12 by the earlier session; not re-verified here |
| `venue_check.py --venue acl` | not meaningful: it expects the skill's own folder layout, so it reports files "missing" that this paper keeps in different places. By hand: Limitations present; Ethics Statement present; licences stated; hyperparameters and hardware stated; confidence intervals reported; human annotation: none (not applicable); AI-use disclosure present |
| `paper_check.py ready` | not run (needs the skill's workspace layout) |

**Not verified:** compilation on Overleaf or with TeX Live (only Tectonic); the OpenReview format requirements; speech output of IndicF5; anything about HMM-1/HMM-2 (checkpoints not on this machine); the primary Census release (see 5.7).

## 5. Remaining blockers and risks, ranked
1. **Release URL.** `\demourl` points to `github.com/speechforge/AAC_System`, which returned 404 (private) when checked. The call requires a live demo or an installation link; the abstract and Sec. 5 say the code is released. Make it public or anonymized, or reword.
2. **Screencast.** Existing one is 2:03, silent, captioned; the paper's Sec. 5 says "captioned screencast". Record an audible one (needs the gated IndicF5 weights).
3. **Licence.** Sec. 5 names Apache-2.0 (`\codelicense`); no licence file exists. Confirm, and confirm rights to the dialogues (gpt-4o-mini generated) and the voice prompts.
4. **Authors.** Three authors are now listed (see section 0, item 4); confirm affiliations, order and any further co-authors. A CRediT statement (skill rule) is still unwritten and needs each author's roles.
5. **Central scientific risk.** The template alone (95%) beats the pipeline (75%) on the lexical criterion. v2 frames the gate as a safeguard, but a reviewer will ask what model phrasing adds. Cheapest strengthening: a native-speaker rating of the 175 outputs (two raters per language, agreement reported).
6. **HMM-1 and HMM-2** are described as trained components but are not evaluated; the three LFS objects named in `paper/CLAUDE_WRITTEN/naacl2027_demo/FINAL_CONTEXT.md`, section 6, are needed.
7. **Census citation** is a news article. The official release exists (PIB, Ministry of Social Justice and Empowerment) but returned HTTP 403 to my fetch, so I did not swap it in; open it in a browser and replace the entry.
8. Native-speaker review of the Indic lexicon; clean-environment install test; OpenReview `preprint` versus `review` option; completeness of the AI-use disclosure.

## 6. Final self-review statement
The paper is currently strongest on a frozen, paired, recounted evaluation whose negative result is stated first. The highest remaining reviewer risk is "what does the language model add over a template". The main evidence for the central claim (the gate preserves selected concepts and polarity) is Table 2: 215/215 concepts kept and 0/175 polarity errors, against 175-185/215 and 2-36/175 before the gate. Claims intentionally weakened or removed are listed in section 3. Submission-blocking issues: items 1 to 4 above.
