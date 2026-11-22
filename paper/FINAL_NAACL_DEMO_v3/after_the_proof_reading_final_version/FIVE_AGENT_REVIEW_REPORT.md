# Five-agent review of the Indic AAC Studio NAACL 2027 demo paper (v3)

Date: 2026-11-14. Paper: *Indic AAC Studio: Concept-Gated Symbol-to-Speech Generation for English, Hindi, Gujarati, and Marathi* (NAACL 2027 System Demonstrations; deadline 2026-12-04, 11:59 p.m. UTC-12).
Final files: `Indic_AAC_Studio_NAACL2027_Demo_v3_final.pdf`, `latex_source_final/`, `Indic_AAC_Studio_NAACL2027_Overleaf_v3_final.zip`, `figure_sources/`, `qa_scripts/`. Each agent's full report is in `agent_reports/` (links below).

## 1. How the review was run

A frozen copy of the v3 draft (`review_input_v3_draft/`: PDF, LaTeX, text dumps, figure sources) and one briefing (`AGENT_BRIEFING.md`: constraints, evidence locations, the earlier 68/100 assessment, output format) were given to five agents with distinct roles. None edited the manuscript; each wrote a report and checked claims against the archived result files, the audit files, and the evaluated code. The first launch of all five failed on a usage-limit error before any report existed; all five were resumed from their saved transcripts after the limit reset. The main session then recomputed the agents' key claims independently (Section 5), applied the edits, and rebuilt.

| # | Agent | Report | Verdict from its viewpoint |
|---|---|---|---|
| 1 | English writing agent | `agent_reports/01_english_writing_agent.md` | writing 13/20, about 17/20 after its edits; no spelling errors or Hindi extraction damage; terminology, tense, abbreviations, typography |
| 2 | Senior scientist agent | `agent_reports/02_senior_scientist_agent.md` | 71/100, borderline; no numeric error found; the risks are over-claims, an unmatched baseline, near-tautological headline metrics, withheld primary-condition evidence |
| 3 | Ravindra-skill agent | `agent_reports/03_ravindra_skill_agent.md` | 71/100, borderline; weak reject as submitted, weak accept if three P0 items close (package, central claim, speech) |
| 4 | Full professor agent | `agent_reports/04_full_professor_agent.md` | 72/100 (earlier 68); about 84 reachable by 4 December; blockers are availability and a thesis the evidence does not carry |
| 5 | Critic reviewer agent | `agent_reports/05_critic_reviewer_agent.md` | 66/100, weak reject, confidence 4/5; demo not accessible, generated sentence adds nothing measured, same-team lexical yardstick |

Mean of the four overall scores: 70.0 (earlier assessment: 68). The draft the agents scored was the version before the edits in Section 4; the writing agent estimated 17/20 for writing after its edits, and the professor estimated up to 84 for the whole paper if the P0 author actions close.

## 2. What is missing: consolidated and ranked

"Raised by" lists agent numbers. Status: **Applied** (in the final PDF), **Partly**, **Author action** (cannot be done from this machine), **Not done** (with reason).

### P0: blocks acceptance

| ID | Missing or wrong | Raised by | Recommendation | Status |
|---|---|---|---|---|
| P0-1 | **The release package is not what the paper says it is.** Agents 4 and 5 reported the URL as 404; I checked on 2026-11-14: it is public (HTTP 200, last push 2026-11-11T13:23:14Z) but holds the old snapshot, no LICENSE file (the paper says Apache-2.0), no frozen scenarios, scorer, raw outputs, or video, a README promising a "zero-hallucination" fallback and English speech, and a third-party PDF at the root. The call desk-rejects a missing or unusable link. | 3, 4, 5 | Push the repaired build with a tag, add LICENSE, scenarios, scorer, raw outputs and a CPU quick start that works without gated weights; remove the README claims; add the screencast link; keep tags `evaluated` and `repaired`. | **Author action** (checklist in Section 6). The abstract now carries the link. |
| P0-2 | **Gate claims exceeded the code.** The abstract and Table 1 said the gate confirms the "intended act"; the act test is an English "I want" pattern, and the forbidden-word and time lists are English words, so for Hindi, Gujarati and Marathi only concept presence and a negator test operate (wrong act 54 to 54). "Four-part rule" contradicted the five-term equation. | 2, 4, 5 (1 on terminology) | Scope every claim to what the gate checks; say so in System, Limitations and Table 1. | **Applied**: abstract, introduction, Table 1 ("act: EN"), Section 3 (English-only sentence), Limitations, Ethics, equation renamed `act(y)`. |
| P0-3 | **Primary-condition evidence was withheld.** Gate precision was printed for explicit fields only; under client input only 57 of 116 accepted outputs are correct and the gate admits 59 of 110 failing cascade outputs; all 33 failure-to-success flips are template sentences; the pooled gain is English-driven (Hindi, Gujarati, Marathi alone +10.1 pp); the pipeline wins 1 and loses 22 scenarios against the template (0 and 35 with explicit fields); cascade polarity errors are 2 versus 36 because explicit inputs drop the *No* entity. | 2, 4, 5 | Print these numbers and the first-stage ablation (63/175 and 67/175 against 65/175 and 71/175). | **Applied** in "Effect of the gate" and "Template baseline". |
| P0-4 | **Speech.** The title promises speech; none was produced in any language (gated weights, placeholder tone, silent screencast). The default client sends a Punjabi reference clip for every language, English included, and browser voices are reached only when the server returns no audio, so the placeholder tone blocks them. My earlier sentence that English uses an English reference clip was wrong for the default client. | 1, 2, 3, 4, 5 | State the routes and the verification status exactly; make the demo audible. | **Applied** in text (Section 3, Appendix B, abstract "unverified", Conclusion). **Author action**: obtain IndicF5 access, or make the server return no audio when the model is absent so browser voices speak; record narrated clips; keep or change the title (Section 6). |
| P0-5 | **The central claim (model phrasing beats a template) is untested**, and the call rejects demos that mainly assemble existing models. | 3, 4, 5 | Reframe as safeguard plus audit; state what the contribution is; run the native check and blind ratings. | **Partly**: reframed throughout and the contribution sentence added; native confirmation of the 120-scenario holdout and the rating packet remain **author actions**. |

### P1: should fix

| ID | Missing or wrong | Raised by | Status |
|---|---|---|---|
| P1-1 | Scorer scope: version 1 drives the headline; the scorer-v2 sentence was incoherent ("adds valid constructions", 97 to 95); negation test is presence-only; first person enforced for English only; "written independently of the gate" too strong. | 2, 3, 4, 5 | **Applied** (Section 5: 5 gained, 7 lost, pre-gate 65 to 63 and 71 to 72, gaps widen to 13.1 and 21.1 pp; Protocol; Appendix B). |
| P1-2 | Baseline fairness: the "unconstrained" prompt is zero-shot, labels only; the matched few-shot one-pass stage already exists; the verifier never changed Indic text (129 of 129) yet costs a median 4.63 s. | 2 | **Applied** (Protocol, Effect of the gate, Appendix B). |
| P1-3 | Attribution: the failure classification was AI-assisted, not "the authors'"; gold, lexicon, templates were assistant-written and not native-checked. | 2, 4, 5 | **Applied** (Appendix B, Limitations, Acknowledgements). |
| P1-4 | Provenance and disclosure: were the client inputs re-implemented or captured (checked: identical for 184 of 184); the explicit feeling intent was changed to *statement* after an aborted 54-request pilot. | 2, 5 | **Applied** (Protocol, Appendix B). |
| P1-5 | "AAC-user utterances" (Table 3) are LLM-generated English and machine-translated Hindi; the Introduction promised predictors for four languages. | 1, 2, 3, 4, 5 | **Applied** (Table 3 caption, Introduction, Limitations). Gujarati and Marathi columns **not possible**: no AAC corpus exists (the 34-language Vertanen collection contains Bengali but none of the three). |
| P1-6 | Evaluated is not demonstrated: Figure 3 shows the archived interface (voice chip "IndicF5 Voice" although only a tone existed). | 1, 3, 4, 5 | **Partly**: caption labels the evaluated build and lists what the repaired build adds. **Author action**: recapture from the repaired build (needs a running backend; four English captures exist in `reviewer_packet/demo_captures/`). |
| P1-7 | Terminology drift around the headline result: "template floor" named both the fallback component and the template-only system; "payload", "hybrid", "validator", "archived system"; RQ headings without questions; HMM count (three English plus one Hindi = four). | 1 | **Applied** with one glossary in text, tables, captions and figures (template fallback vs template baseline; client input vs explicit fields; act vs intent; pipeline). |
| P1-8 | Citations: ISO access dates; page ranges with a Unicode dash; Nature Communications article number; arXiv identifiers hidden; IndicF5 without locator; Avaz FreeSpeech URL now redirects to a page that never mentions FreeSpeech; McCoy et al. claims beyond the abstract; Table 1 had no citations in its cells. | 3 | **Applied** (access dates "Last Accessed Date: November 12th, 2026", Jellow 13th; entries fixed; FreeSpeech clause and entry removed; Compansion claim softened; citations moved into Table 1). |
| P1-9 | Novelty and prior art: no mention of constrained generation; Compansion, Karmakar and Sinha, Jellow, SpeakFaster, ConnecTone positioned. | 3, 4 | **Applied**: two ACL Anthology-verified citations (Hokamp and Liu 2017; Post and Vilar 2018) and one sentence. **Not done**: data-to-text slot-error literature (no verified citation in hand). |
| P1-10 | Ethics outside the page limit: dual use of voice cloning, language disparity, native review before Gujarati and Marathi use, gendered first-person forms, provenance and consent of default reference clips, data licences. | 3, 4 | **Partly**: first four applied; provenance and licences of the reference clips and dialogues are **author actions**. |
| P1-11 | AI-use disclosure incomplete (the call requires full disclosure in Acknowledgements). | 4, 5 | **Applied** (harness, lexicon, gold annotations, failure classification, figure scripts, reference checks, repairs; no native review). The authors must add which original code was AI-assisted. |

### P2: polish (all applied unless noted)

Float colour semantics (Figure 1 now follows the verdict palette with a legend; Figure 2 numbers removed because they clashed with Figure 3 callouts; input condition labelled in Figures 1 and 4); model names split across lines (`\mbox`, hyphenation exceptions); abbreviations defined at first use; tense (results in past tense); "3 of 276" corrected to "3 of 272 non-negated"; Table 3 rounding note; Hindi bigram hit@1 corrected from 24.1 to 24.0 (586/2437 = 24.05%); citation order roadmap sentence; Table 6 rows that repeated Figure 1 replaced by kinds shown nowhere else. **Not done**: forest plot of the paired intervals (no page space; the intervals are in the text); scorer-v2 columns beside v1 in Table 2 (space; version 2 results are in Section 5); three scored "accepted model" English rows that are template sentences made inside the verifier; Infini-gram is published at COLM 2024 (arXiv entry kept).

## 3. Each agent's findings and recommendations

### Agent 1: English writing
- *Found*: central term "template floor" used for two things; speech wording contradicts itself; Table 3 calls synthetic data "AAC-user utterances"; mixed tense; dangling modifiers ("Even when fluent, the cascade ... it replaced"); seven abbreviations undefined (TTS, HMM, MRR, CI, pp, EN/HI/GU/MR, POS); 16 sentences over 45 words; model names broken across lines; colour legends missing or inconsistent.
- *Recommended*: a glossary (client input / explicit fields; act vs intent; scenario vs selection; template fallback vs template baseline; pipeline not "hybrid"); plain headings instead of RQ labels; past tense for what was run; split long sentences; `\mbox` around model names and hyphenation exceptions; a tested 24-hunk patch (net line-neutral).
- *Outcome*: the glossary, headings, tense, abbreviations, typography and caption fixes were applied by hand to the revised text (the patch itself targeted the pre-revision text).

### Agent 2: senior scientist
- *Found*: every number reproduces; the abstract's "confirms intended act" is wrong for Indic text; "no polarity error" and "215/215" are near-tautological (the scorer and the gate share a presence test; the template echoes labels); client-condition gate precision missing; English-driven gain; unmatched baseline; scorer first-person check only for English; provenance wording; speech routing (Punjabi default clip; browser unreachable with a placeholder tone).
- *Recommended*: rescope the abstract; print client precision, Indic-only effect and the stage ablation; zero-shot label; scorer caveats; edit the verifier and speech sentences; denominator 272.
- *Outcome*: all applied; the recomputed numbers match mine (Section 5).

### Agent 3: Ravindra-skill (Prof. Patil lab standards)
- *Found*: 17-rule audit (paragraph focus, contributions, trade-offs, access-date format, bibliographic fields, native scripts); the printed URL is public but stale and unlicensed; title says Speech though none was produced; citation defects; Table 3 data description; ethics lacks dual use and native review; `prose_lint` 0 high (two false positives on "script"); `venue_check` flags only the Responsible-NLP statement as true.
- *Recommended*: the edit package in its report (contribution and delta sentence, bibliography fixes, "payload" to "input", ethics sentences, lexically constrained decoding sentence).
- *Outcome*: applied (arXiv identifiers are now printed through `howpublished`); the title decision is left to the authors (Section 6).

### Agent 4: full professor
- *Found*: the evidence supports "a checkable contract plus an audit", not "concept-gated generation"; every failure-to-success flip is a template sentence; evaluated is not demonstrated; availability is the largest single risk; ethics gaps; data-to-text lineage missing.
- *Recommended*: new title, abstract and Conclusion; client-condition gate decisions and a realiser ablation; Figure 3 from the repaired build; native-confirmed holdout plus blind ratings; a 150-second storyboard and an availability statement (Section 6).
- *Outcome*: abstract, Conclusion, gate evidence, ablation and ethics applied; the title and Figure 3 recapture left to the authors.

### Agent 5: critic reviewer
- *Found*: five damaging weaknesses (demo access; unmeasured value of the generated sentence; weak same-team yardstick; evaluated not demonstrated; residual absolutes); a float audit (limits respected, scripts pass; Figure 3 legibility, grayscale colour loss, Figure 1 colour semantics, citation order); scorer-v2 sentence incoherent; AI disclosure incomplete.
- *Recommended*: twelve line-costed edits; paired counts; recapture Figure 3; forest plot.
- *Outcome*: edits 1 to 11 applied in substance; the forest plot and Figure 3 recapture not done.

## 4. What changed in the paper (summary)

Abstract, Introduction, Related Work (Table 1 now five columns with year citations), System (gate scope, speech routing, verifier), Evaluation (client first; paired counts; precision; Indic-only effect; provenance), Failure Audit and Repairs (coherent scorer sentence, regression caveats), Availability and Limitations, Conclusion, Ethics, Acknowledgements, Appendix (Figure 4 with all four languages, English as baseline; Table 5 grid with sizes; Table 6 new outcome kinds; compact Table 7; Appendix B merged), generated tables (relabeled; one corrected cell), Figures 1, 2, 4 (recoloured, relabeled, small-caps model names), bibliography. Full list with files and checks: `CHANGE_LOG_AND_AUTHOR_NOTES_v3.md`. Final build: 10 pages; main content ends on page 6 (about 2.8 spare lines, measured with ragged-bottom columns); appendix pages 9-10 (about 2.7 spare lines); every figure, table and the equation cited in the text; 29 of 29 native-script strings recoverable from the PDF; all fonts embedded; prose lint 0 high; Table 2 recounts exactly from the raw outputs.

## 5. Claims the main session verified independently

| Claim (agent) | Result |
|---|---|
| Client condition: 116 accepted, 57 correct; 59 fallbacks, 40 correct; 110 failing candidates, 59 admitted; explicit 108/71, 67/61, 104/37 (2, 4, 5) | confirmed (`qa_scripts/extra_checks.py`) |
| All failure-to-success flips are template sentences: 33 client, 61 explicit (4) | confirmed; English supplies 20 of the 33 |
| Paired against the template: deployed wins 1, loses 22 (client); wins 0, loses 35 (explicit) (5) | confirmed |
| Hindi, Gujarati, Marathi alone: +10.1 pp client, +25.6 explicit (2) | confirmed; my bootstrap interval 5.2 to 16.0 (agent: 4.8 to 16.0); the text uses 5.2 to 16.0 |
| Verifier never changed Indic first-stage text (129 of 129); English changed in 28 of 46 (client) (2) | confirmed |
| Client inputs equal real-page captures (5, question) | 184 of 184 identical |
| Default client sends the Punjabi clip; browser speech only when no server audio (2) | confirmed in the archived front end and `tts.py` |
| Vertanen (2026): 34 languages, none of Hindi, Gujarati, Marathi (3) | confirmed from the paper's Table 1 (Bengali only) |
| Hokamp and Liu 2017; Post and Vilar 2018 metadata (3) | confirmed from the ACL Anthology BibTeX |
| Release repository state (3, versus 4 and 5) | public (HTTP 200), pushed 2026-11-11, no LICENSE |

## 6. What only the authors can do, ranked by return

1. **Make the release match the paper (0 pages, largest gain).** Push the repaired build; tags `evaluated` (reproduces Tables 2 to 4) and `repaired`; LICENSE (Apache-2.0 is claimed); frozen scenarios, scorer, raw outputs; a CPU quick start that works without gated weights (the clean-environment test needed `python-multipart` and ran 44 s per request); delete the "zero-hallucination" and English-speech claims from the README; remove the third-party PDF; archive with a DOI. Then confirm the Availability sentence. Suggested statement once true: "Source, installation guide (CPU quick start; browser voices speak; IndicF5 optional, gated), frozen scenarios, scorer and raw outputs that regenerate Tables 2 to 8, and a narrated 2.5-minute screencast: URL (archive DOI). Apache License 2.0; the release tagged `evaluated` reproduces Tables 2 to 4."
2. **Make the demo audible.** Either accept the IndicF5 terms (a free request) or make the server return no audio when the model is absent so that hi-IN, gu-IN and mr-IN browser voices speak; re-record the screencast with sound. If neither is possible before the deadline, retitle to "Symbol-to-Sentence".
3. **Native-speaker work.** Two speakers per language confirm the gold of the 120 fresh scenarios and rate the 32 differing template-versus-pipeline pairs from the prepared packet (`reviewer_packet/`); this turns the regression target into a test and answers the central claim.
4. **Recapture Figure 3** from the repaired build (message-type control, route chips, clarification card), ideally with Hindi and Gujarati labels; crop to the canvas and output card so the text prints at about 6 pt.
5. **Record provenance and consent** for the default reference clips and the synthetic dialogues; state who wrote the original code with AI assistance (Acknowledgements).
6. **Title.** Keep "Concept-Gated Symbol-to-Speech Generation" only if audible speech lands. The professor's alternative: *Indic AAC Studio: A Checkable Contract for Symbol-to-Speech in English, Hindi, Gujarati, and Marathi*.

**Storyboard for the 2.5-minute screencast (agent 4, 150 s, real audio).** 0:00 problem, "No + Water" and three sentences; 0:12 Hindi request, Gujarati and Marathi refusals spoken, route chips shown; 0:40 English rejection ("I am not and will eat at"), gate reason, template spoken; 1:10 "Nose": clarification card; 1:30 next-word shelf and Quick Express; 1:50 one command regenerates Table 2; 2:15 URL, licence, install line.

## 7. Expected effect

The edits remove the over-claims and the withheld evidence that all four scoring agents named, and the writing agent expects the writing criterion to rise from 13/20 to about 17/20. Fit, honesty and evidence presentation improve, but the demo and reproducibility criterion (8 to 10 of 15 in the agents' scores) and the central-claim evidence (17 to 21 of 30) cannot move without the author actions above. An honest range for the revised paper with those actions open is the low-to-mid 70s; the professor's estimate of about 84 assumes items 1 to 3 close.

## 8. Addendum (2026-11-14): speech-quality (UTMOS22, NISQA v2) evaluation
The only open item that needed new computation after the review. The five agents had flagged the absence of any speech evidence (section 2, P0); this addendum adds what can honestly be measured now and states what cannot.
- **What exists:** Table 8 (Appendix B) scores the evaluated build's placeholder tone (UTMOS22 1.54, NISQA 1.12), the eight human voice-prompt clips (UTMOS22 2.66 to 4.27; the default Punjabi prompt 3.83 / 4.74), and, as a pipeline check, the 175 deployed sentences read by open MMS-TTS voices (UTMOS22 3.31 to 4.01; NISQA 3.52 to 4.91). Everything is under `mos_eval/` with the audio, scripts, scores, and an independent recount (`check_mos.py`).
- **What does not exist:** IndicF5 speech. The weights are gated and I cannot accept the terms for you, so no IndicF5 clip was scored and the paper says so in the table, in Appendix B, and in Limitations. The numbers do not support any claim about the system's speech quality.
- **Reviewer view:** this does not close P0 (audible speech). It removes one weakness (a reader can now see that the scoring route works, how a tone and human speech score, and that nothing was claimed beyond that) and it adds a risk if misread, so the caption and text say "stand-in", "not IndicF5", "English-trained predictors", and "indicative only".
- **Author action (8):** accept the IndicF5 terms, install `f5_tts`, run `mos_eval/synth_indicf5.py`, re-score, and rewrite the "not run" wording (README_MOS.md lists the places). Also consider a native-speaker rating of the IndicF5 clips, because UTMOS22 and NISQA are English-trained and NISQA mainly rates signal quality.
- **Page budget:** the paper is still 10 pages (body 6, appendix 2); the appendix has about 3 lines spare and the body 1.8 lines, so any further addition needs an equal cut.
