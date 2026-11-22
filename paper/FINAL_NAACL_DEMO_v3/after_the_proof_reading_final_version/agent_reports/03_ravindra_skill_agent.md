# Agent 3: Ravindra-skill audit (frozen v3 draft)

Method: skill reviewer mode; scripts and test builds in /tmp/agent3_work/; manuscript and skill untouched.

## 1. Verdict and score
**Borderline: Weak Reject as submitted, Weak Accept if the three P0 items close.** Fit 14/15, technical 13/20, evidence 20/30, demo and reproducibility 8/15, writing 16/20 = **71/100**. Claims are bounded and the evaluation is frozen and paired, but the decisive claim (model phrasing beats a template) is untested and the package differs from the paper.

Scripts:
- prose_lint (10 files): 0 high; 2 medium, false positives ("script" = writing system, Secs. 3-4); 13 low long sentences, valid. Missed: "payload" (about 10 uses).
- venue_check (naacl): 13 FAIL from file layout and skill artifacts (false positives); mapped, 5 FAIL: claim map and citation lock (skill artifacts); "anonymous" (false: single-blind track); annotator/agreement (false: none reported); **Responsible NLP (true: no misuse, bias or fairness text)**.
- paper_check: 3 todo hits, all "placeholder" (false); assets OK; novelty thread in all five sections. xref_audit OK; native_text_check 30/30. Rebuild: 10 pp., no errors; style files hash-identical to the pinned official ACL commit.

## 2. Seventeen rules (P pass, Pt partial, F fail)
1. Paragraphs **Pt**: multi-topic: Sec. 3 "Prediction, speech, and training" (179 words, 4 topics), "Systems and scoring", RQ1 (29 numbers), RQ3, Ethics para. 2.
2. Contributions **Pt**: bullet 2 is evidenced for English and Hindi only, on synthetic data; "four-part rule" vs five tests in Eq. 1.
3. Opening **P.**
4. Figure 1 **Pt**: self-contained, recorded outputs, but on p. 2 (ACL title block; `dblfloatfix` and pre-title placement both fail); stage colours (wrong cascade outputs green) contradict the verdict colours of Tables 4-6, Fig. 4.
5. Trade-offs **P.**
6. No invented number or citation **Pt**: abstract point estimates recomputed, agree; citation defects below.
7. Human English **P**, except "payload", "rev. 7ae5576".
8. Novelty thread **P** mechanically; type and delta only in Sec. 2.
9. Evidence gaps **Pt**: bounded honestly; native comparison, real speech open.
10. Credit, licence **Pt**: no licence file; no rights statement for dialogues or reference clips; no contribution statement.
11. Figures from data **P**, except Fig. 3 (screenshot text prints at about 2 pt).
12. Website **N/A.** 13. Template **P.**
14. Names, author actions **Pt**: small caps at every use (user request overrides "once"); "awaits two native speakers" is an author action.
15. Native scripts **P**; intro water example not labelled authored.
16. Access dates **F** in the frozen draft (ISO, four references, Table 1 caption); the working copy prints "Last Accessed Date: November 12th, 2026" correctly (Jellow 13th): keep.
17. Bibliographic fields **Pt/F** (Sec. 4).

## 3. What is missing
**P0**
1. Package: the printed URL now resolves (public) but holds the 2026-11-11 snapshot: no licence file despite Apache-2.0; no frozen scenarios, scorer, raw outputs or video (searched by name); the README promises a "zero-hallucination" fallback and English speech (the paper disclaims both); a third-party PDF at the root. A missing link is a desk rejection and reviewers run the demo. Push v3, add LICENSE, put the link in the abstract.
2. Central claim untested: pipeline trails template (97 vs 118; 132 vs 167); repaired build is a regression target. The call rejects "assembling off-the-shelf models without substantive technical or evaluative work". Score the 120 fresh scenarios after native annotation plus a blind preference test, or confine the headline to what the gate keeps.
3. Title says Speech; none was produced (placeholder tone; silent video). The model-card gate is an access request: obtain weights, record Hindi, Gujarati and Marathi clips, or retitle.

**P1** 4. Citation defects (Sec. 4). 5. Introduction has no citation and no delta. 6. Table 3 says "AAC-user utterances"; the dialogues are synthetic (gpt-4o-mini; machine-translated Hindi), disclosed only in the Acknowledgements. Vertanen (2026), in the .bib but uncited, covers 34 languages (Bengali, not Hindi, Gujarati or Marathi): it supports "no corpus". 7. Ethics lacks dual use (cloning), language disparity (explicit-field template 46/46 English, 34/42 Gujarati) and native review; the call rejects sensitive-task papers that omit such issues. 8. Table 5 marks green sentences a Hindi reader will find unnatural.

**P2** Table 3 cited after Table 4 (swap costs +1 to +4 lines, measured: skip); "payload"; one 64-word Limitations sentence; Fig. 3 unreadable (show panel b alone); misplaced HMM sentence in Ethics.

## 4. Citations
Verified against primary records: Karmakar and Sinha (full text: Bliss to English, Bengali, no check, no speech), ConnecTone, Mohan, Francis 2025, SpeakFaster, F5-TTS, IndicF5 (11 languages, no English; gated; MIT), Jellow (24 languages incl. all three; pre-made sentences; keyboard; Google TTS), Cboard ("46" in FAQ; none named), Avaz AAC. McCoy 1998: "expands telegraphic input" verified; "English" and "syntactic and semantic rules" are not in the abstract. **Avaz FreeSpeech: the cited URL now 301-redirects to the Avaz AAC page, which never mentions FreeSpeech; Wayback snapshots (2025-12-26, 2026-10-19) support the claim.** The two single-source items match their primary records; no second index was reachable.
Print defects: Francis 2025 "page 4960-4962" (Unicode dash); Cai lacks article number 9449; Vocos, Infini-gram, Qwen print "arXiv preprint." with no identifier; IndicF5 no locator (the style hides URLs behind titles); "Jellow basic"; Infini-gram is published (COLM 2024).

## 5. Edits (net body lines)
Rebuilt as a package: Conclusion still ends on p. 6, **net +1 line**; appendix unchanged; bibliography prints correctly.
- `main.tex` Fig. 1 caption: delete " Marathi glosses are given in quotation marks." (-1). `\demourl`: public URL (0).
- `00_abstract`: "a reviewer package and a screencast accompany the submission." → "code, scenarios, and a screencast are at \demourl{}." (0/+1)
- `01_intro`: "Our contribution is the application and evaluation of ... fallback policy, for" → "Among the closest systems (Section~\ref{sec:related}), none documents a check that the spoken sentence keeps the selected concepts and polarity; we contribute that check for Indic symbol-to-speech, its paired evaluation, and its fallback cost, for" (+1). "with predictors trained on AAC dialogues (Section~\ref{sec:system}, Appendix Table~\ref{tab:models})" → "whose suffix-trie predictor exceeds trigram backoff by 1.1 (English) and 1.2 (Hindi) hit@1 points on synthetic dialogues (Table~\ref{tab:pred})" (+1).
- `02_related`: delete ", and its FreeSpeech app teaches grammar by sentence building \citep{avazfreespeech}" and the .bib entry (-1).
- `03_system`: "\qwen{} is prompted and \indicf{} is used as released; we train" → "We train" (-1; release statement stays in Sec. 1, Table 7).
- `tab_pred` caption: "on AAC-user utterances:" → "on AAC-user turns of synthetic dialogues (LLM-generated English, machine-translated Hindi):"; "because no AAC dialogue corpus exists for them" → ": the 34-language collection of \citet{vertanen2026multilingual} has neither, and we know of no other corpus" (+2, float).
- `04_eval`, `tab_results`, `tab_type`, `07_appendix`: "payload(s)" → "input(s)" (0).
- `06_ethics` (free space): replace the last sentence ("The evaluated build ran without the HMM-1 and HMM-2 checkpoints, ...") with "Cloning can also impersonate a person, so keep the consent requirement above. Template success differs by language (explicit fields: 46/46 English, 34/42 Gujarati), and no native speaker has reviewed the Indic sentences; Gujarati and Marathi deployments need that review first."
- `07_appendix` Table 5 caption: "No native speaker has judged these outcomes;" → "Green marks a scorer pass, not a native judgment (several sentences read as unnatural);" (0).
- `references.bib`: `pages={4960–4962}` → `{4960--4962}`; Cai `eid={9449}`; Vocos, Infini-gram, Qwen: `publisher = {arXiv},` → `eprint = {<id>}, archivePrefix = {arXiv},` (2306.00814, 2401.17377, 2412.15115); IndicF5 `howpublished = {Hugging Face model card, \url{https://huggingface.co/ai4bharat/IndicF5}},`; `{{Jellow Basic}}`; access-date notes as in the working copy.

## 6. Claims checked and claim-evidence matrix
| Claim | Evidence | Status |
|---|---|---|
| Gate raises success | Table 2: 65 to 97/175 (+18.3 pp, CI 11.9-25.2); 71 to 132 | verified; lexical scorer v1 |
| All concepts kept, no polarity error | 215/215 vs 175/215; polarity 0 vs 2 and 36 | verified; bounded |
| Template beats pipeline | RQ3: 118 vs 97; 167 vs 132 | verified |
| Model phrasing adds value | none | unsupported |
| Trie beats trigram | Table 3: +1.1 (381/356 of 2,220), +1.2 (659/630 of 2,437) | verified; EN/HI, synthetic |
| "None documents a check" | Table 1, six sources | supported, bounded |

## 7. Output-contract pieces
**Mini-outline.** Abstract: **state problem, safeguard, paired result and bound.** 1: **show the harm of a misstated selection and the contract.** 2: **place the work among five expanders and four boards; state the gap.** 3: **show how a selection becomes speech.** 4: **answer RQ1-RQ4 against the template floor.** 5: **show audit-to-repair without claiming a result.** 6-7, Ethics, Appendix: **bound scope, release, risk; supply cases.**

**Scorecard (ref 05).** Contribution: needs revision (thin delta). Clarity: pass, dense paragraphs. Rigor: pass (frozen, paired, intervals, leakage); one lexical scorer. Completeness: needs evidence (speech, Gujarati/Marathi prediction, users). Soundness: needs revision (stale package, no licence file).

**Novelty check.** Type: new system plus evaluation protocol, not a new model. Delta: vs Compansion (rule-based English; no model, no post-hoc check) a model realizer with a deterministic check in four languages; vs Karmakar and Sinha (no check, no speech) a check plus speech route; vs Jellow (24 languages; pre-made and typed sentences) generation from selections, but the template floor resembles Jellow and wins on the lexical scorer; vs SpeakFaster (user verifies) deterministic verification; vs ConnecTone (user picks suggestions) symbol input and a check. Isolating experiment: Table 2, cascade before gate vs deployed (same response). Reviewers may cite lexically constrained decoding as prior art (Hokamp and Liu 2017, P17-1141; Post and Vilar 2018, N18-1119; verified): add one sentence.

## 8. Arrangement
Abstract: context, gap, mechanism, numbers (208 words); no link. Introduction: CARS, 327 words, no citation. Floats: F1 p2, T1 p3, F2 p3, F3 p4, T2 p5, T3 p5, T4 p6, all cited before or near; T3 first cited after T4. Present: Ethics, AI disclosure (Acknowledgements), licence statement, two-minute video (limit 2.5); Limitations not mandated. Missing: working package, licence file; confirm the Responsible NLP checklist in the portal.

## 9. Questions
1. Can the v3 package (tag, LICENSE, scenarios, scorer, raw outputs, screencast) be public before 4 December?
2. Can IndicF5 access be obtained for real speech?
3. Which two native speakers per language can annotate the 120 fresh scenarios, by when?
4. Are the gpt-4o-mini dialogues and reference clips cleared for release?
5. Does another submission overlap this one by more than 25%?
