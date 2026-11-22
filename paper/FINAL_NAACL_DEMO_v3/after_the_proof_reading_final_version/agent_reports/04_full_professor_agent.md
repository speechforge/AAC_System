# 04 Full professor agent: meta-review of the v3 draft

## 1. Verdict and score

**Weak Reject, borderline: 72/100 (earlier 68).** The audit is honest and is the real asset; the blockers are availability and a thesis the evidence does not carry. About 84 (Accept) is reachable by 4 December.

**Thesis the evidence supports:** *treating a symbol selection as a contract lets deterministic checks remove dropped or replaced concepts and inverted negation from a 0.5B model's Indic output, but not wrong acts, third-person drift or stilted phrasing, and a template floor does as well under a lexical scorer.* The title and Conclusion sentence 1 claim instead that a prompted model "can sit in front of an AAC voice" behind a gate. Strongest honest framing: a checkable contract between symbol selection and spoken sentence, plus an audit of what such checks catch and miss. **Title:** *Indic AAC Studio: A Checkable Contract for Symbol-to-Speech in English, Hindi, Gujarati, and Marathi* (keep "Speech" only once audible; otherwise "Symbol-to-Sentence").

**Narrative leaks (verified)**
- L1 Title, abstract and Conclusion sell generation; RQ3 shows the template matches or beats the pipeline in every language, and every scenario the gate turns from failure to success is a template sentence (33 client, 61 explicit; `scored.csv`).
- L2 Abstract, Introduction and Table 1 say the gate confirms the "intended act". The evaluated gate tests act only with an English "I want" pattern and question cues, and its forbidden-word and time lists are English words that cannot fire on Devanagari or Gujarati; for Indic requests and feelings only concept presence and a negator test operate (wrong act: 54 to 54, Table 2).
- L3 Primary-condition numbers are withheld: "no polarity error" lacks its baseline (2 to 0; 36 to 0 is explicit-only); gate precision is printed for explicit fields only (71/108), not client input (57/116, 49%).
- L4 Evaluated is not demonstrated: Section 3 and Figure 3 show the archived interface (with the "IndicF5 Voice" badge the repair removed); the package ships the repaired one, and nothing in Section 3 or the caption says which build is shown.
- L5 RQ4 is off-thesis; Table 3 calls LLM-generated, machine-translated dialogues "AAC-user utterances".

**Score.** Fit 14/15. Technical 14/20: modest design, well-scoped novelty. Evidence 20/30: paired CIs, exclusions, honest regression; lexical scorer, same-team gold, superseded build, no human judgement. Demo 9/15: install tests good; link 404, no licence file, silent video, speech unverified. Writing 15/20: claims and typography improved; thesis leaks, unreadable Figure 3. **Total 72.** Five changes (about 84), by return per page:
1. (0 pages, +5) Public or archived release with licence, CPU quick start without gated weights, audible captioned screencast.
2. (0 pages, +4) New title, abstract, contribution sentence, Conclusion; gate scoped to what it checks (tested below).
3. (0 pages, +2) Figure 3 from the repaired build, in Hindi and Gujarati; tag the evaluated build.
4. (about 4 lines, +2) Print client-condition gate decisions and a realiser ablation (few-shot realiser alone 63/175 client, 67 explicit, against 65 and 71 for the cascade; A7); cite data-to-text faithfulness work (slot error rate; verify).
5. (about 10 lines, +5, a week of raters) Native-confirm the 120-scenario holdout gold; two blind raters per language on its 32 differing pairs: the released build gets a test, not a regression target.

**Must not be claimed:** gate guarantees or act confirmation in Indic text; model gains in quality or naturalness; speech in any language; 175/175 or holdout scores as results; that the evaluation describes the released build; AAC-user benefit; priority over Jellow, Cboard, Avaz; scorer independence; native-checked templates or gold.

## 2. What is missing

**P0** (with L2, L4)
- Link. The call desk-rejects submissions without a live demo or installable package, and reviewers must use it. `speechforge/AAC_System` is 404 with no licence file, yet Section 6 states Apache-2.0. Reviewers look for a quick start without gated weights, the licence, the figures' interface, one command regenerating Table 2, and the video.
- Audible demo. A silent video is allowed but invites "does it speak?". Browser voices (check the device's hi-IN, gu-IN, mr-IN list) or accepting the gated IndicF5 terms make speech audible quickly.

**P1**
- L3, L5.
- Novelty. The call rejects demos that mainly wrap existing models, and the paper says both are "used as released": say that this is a system demonstration plus audit, whose substance is the contract, the three-language templates and the evaluation. Related work ignores data-to-text faithfulness (slot error rate, reranking), so an NLG reviewer will call the check known; claim its application to AAC with a safe fallback. The template floor plays Compansion's role, so the finding fits rule-first design. Jellow's row omits two-tap sentence building; cite Cboard's repository (a fetch found Hindi and Marathi translations, no Gujarati; verify). Karmakar-Sinha and ConnecTone verified (ACL Anthology, ISCA).
- Attribution. Appendix B calls the failure classification "the authors'"; the record says the authoring assistant made it, not native-checked. Disclose gold, classification and template authorship in Acknowledgements.
- Cost. Model path 6-19 s on the 4 GB GPU, template under 1 ms.
- Ethics (outside the page limit). Objections: preview-and-confirm unimplemented; guardian-consented voice cloning without stated misuse safeguards or provenance of the default reference voice; no stated AAC-user or clinician input; gendered first-person verbs; unstated data licence.

**P2** Table 4 repeats Table 5 rows 3-4 and floats a page after its citation; Table 6 rows 1-3 repeat Figure 1; "written independently of the gate" is too strong.

## 3. Concrete edits

Built in a scratch copy (manuscript untouched): edits 1-6 leave 4.4 spare lines after the Conclusion (baseline 5.3), and 7.3 with caption trims 7-10 and the ablation sentence; the body stays at 6 pages. Per-edit counts are approximate.

1. Title: "Concept-Gated Symbol-to-Speech Generation / for English" to "A Checkable Contract for Symbol-to-Speech / in English" (0).
2. Abstract, sentences 3-9 become: "\sys{} ... treats the selection as a contract: a model sentence is spoken only if deterministic checks confirm the selected concepts and polarity, and otherwise a template built from the user's own labels is spoken. On 175 frozen scenarios sent as the web client builds them, the checks keep all 215 required concept instances with no polarity error, but only 49% of the sentences they accept are fully correct, 54 of the 78 failures express the wrong act, and a template alone outscores the pipeline (118 against 97) under a lexical scorer. The released build repairs the audited defects (regression check only). Speech output was not verified in the evaluated build. Code, scenarios, and a screencast are at URL." (-2)
3. Introduction: "the application and evaluation of explicit concept, polarity, and act checks" to "a checkable contract between a symbol selection and a spoken sentence, and an audit of what its checks catch and miss"; three bullets become two (-1).
4. RQ1: "With explicit fields the gate lets model text through on 62% of requests; accepted outputs are fully correct in 71/108 ..." to "Under client payloads the gate accepts 116 model sentences, 57 fully correct (explicit fields: 71 of 108); template fallbacks succeed in 40/59 (61/67), and all 33 scenarios the gate turns from failure to success are template sentences (one is lost)" (+1.5); add the realiser ablation (+1).
5. Conclusion, sentences 1-2: "A small prompted language model can sit in front of an AAC voice ..." to "Across 175 frozen scenarios in four languages, deterministic checks kept every selected concept and removed all polarity errors, but only half of the sentences accepted under web-client input were fully correct, and a template floor matched or exceeded the pipeline under a lexical scorer." (+1)
6. Move Availability to the end of Section 3; Section 6 becomes "Limitations" (0).
7-10. Captions: Table 2, drop "Success requires ..." and the off-task definition (Appendix B) (-3); Table 3, "synthetic AAC dialogues" (-1); Figure 1, drop "built from the user's labels" and the Marathi-gloss sentence (-2); Figure 2, one sentence (-2).
11. Ethics: the P1 items. 12. Figure 3: use `reviewer_packet/demo_captures` ("No + Pizza" with route chip; clarification card), in Hindi and Gujarati (0).

**Availability statement (when true):** "Source, installation guide (CPU quick start; browser voices speak; IndicF5 optional, gated), frozen scenarios, scorer and raw outputs that regenerate Tables 2-8, and a narrated 2.5-minute screencast: URL (archive DOI). Apache License 2.0; the release tagged `evaluated` reproduces Tables 2-4."

**Storyboard (150 s, real audio).** 0:00 problem: "No + Water", three sentences. 0:12 Hindi request; Gujarati and Marathi refusals spoken, route chips shown. 0:40 English rejection ("I am not and will eat at"), gate reason, template spoken. 1:10 "Nose": clarification card. 1:30 next-word shelf, Quick Express. 1:50 one command regenerates Table 2. 2:15 URL, licence, install line.

**Arrangement.** Introduction; System (UI figure first, architecture second, availability last); Evaluation (Table 2, RQ1-RQ3, Figure 4 cited, RQ4 shrunk); Repair; Limitations; Conclusion. All 12 floats are cited; Table 3 and Figure 4 keep their numbers; define Table 4 before RQ2. Appendix: drop Table 6 rows 1-3 (about 9 lines for the gate-decision breakdown or rating table).

## 4. Claims checked

| Claim | Evidence | Status | Correction |
|---|---|---|---|
| 97, 118, 65 of 175; 215/215; 8/175; CIs | A1, A7 | verified | none |
| Gate confirms "intended act" | archived semantic.py | wrong for Indic | scope to concepts, polarity |
| Accepted correct 71/108 | scored.csv | verified, explicit only | add 57/116 |
| Classification "the authors'" | A3 note | wrong attribution | assistant, not native-checked |

**Earlier fixes.** (1) Client first, 215/215, zero polarity, hedged: adequate except client gate precision. (2) Novelty (Gap, Table 1): scoped well; NLG lineage missing. (3) Off-task, 32 vs 30, hit@1 counts, Gujarati failures by identifier: adequate, verified (A3, A6, A8). (4) Speech, latency, CDN, extraction: stated; no audible speech remains.

## 5. Questions to the authors
1. Can the repository be public, licensed and installable before 4 December, with audible Hindi, Gujarati and Marathi speech without gated weights?
2. Whose voice are the default reference clips, and what consent covers them?
3. Who classified the failures and wrote the gold: the authors or an assistant?
4. How does the ledger scale beyond 69 symbols?
