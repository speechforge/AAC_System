# Agent 1: English writing review

## 1. Verdict and score
Writing and presentation: **13/20 now, about 17/20 after the edits below.** The prose is concise; the source has no spelling errors, doubled words or Hindi extraction damage (native-text check 30/30, no "चा हए"). Checked and fine: "e.g.," usage, US quotation marks in the body, en dashes in ranges, no em dashes, thin spaces before units, Table/Figure/Section capitalization, the "Appendix B" and "Appendix Table 7" pattern. Weaknesses: terminology drift around the central finding, mixed tense, 16 sentences over 45 words, seven undefined abbreviations, model names split across lines.

**Tested patch.** All edits were applied to a scratch copy and built with Tectonic: 10 pages; the Conclusion ends 4.3 lines higher on p. 6 (slack about 5 → 9 lines); appendix unchanged at two pages. Applied alone, net lines: evaluation −2, repair +1, main.tex +1, others 0. The complete diff (24 hunks, every replacement; apply to a copy with `patch -p1` from `review_input_v3_draft/`): `/tmp/claude-1000/-home-linux-Documents-aac-system-november-11-AAC-System-merged/c8c8cef4-ff02-456d-84e5-24b4a66e8f2c/scratchpad/english_agent_edits.diff`.

**Glossary (applied)**
- *client* / *explicit*: the two input conditions ("client input", "explicit fields"); drop "payload", "web-client input".
- *intent*: the client's field. *act*: what a sentence does, so Eq. (1) tests `act(y)`. *polarity*: the property; *negation*: the field or word.
- *scenario*: evaluation item; *selection*: what the user taps; *request*: only an act.
- *template fallback*: spoken after two rejections. *template baseline*: system (v). Retire "floor", "template alone/only", "fallback template".
- *ungated cascade*, *pipeline* (not "hybrid"), *evaluated*/*repaired build*; no "validator".

## 2. What is missing, ranked
**P0**
1. "Template floor" names two things: the fallback component (Figs. 1, 2, 4; Table 4) and the template-only system (Tables 2, 8; Conclusion). The headline result (template ≥ pipeline) depends on the distinction.
2. Speech wording contradicts itself: abstract "integrated but was not evaluated"; Limitations "Speech was synthesized in placeholder mode"; Section 3 "neither route produced speech". The title promises "Speech".
3. Table 3 says "AAC-user utterances"; the dialogues are LLM-generated, Hindi machine-translated (Acknowledgements; Ethics: "synthetic dialogues"). "AAC dialogues" is unqualified in the Introduction and Section 3.

**P1**
4. Tense: results in the present (abstract, Sections 4–5), past in the Conclusion. Rule applied: present for method, past for what was run.
5. Dangling or misattached: "Even when fluent, the cascade ... fails ... it replaced"; "driving the real page, the original client sent"; "scenarios, whose few-shot prompt reproduces"; Fig. 1 caption "The gate ... speaks a template".
6. "four defects" but three bold labels; "four-part" rule vs five conjuncts in Eq. (1); "hybrid" undefined; "a Hindi HMM, two English HMMs" vs four HMMs in Table 7.
7. Undefined at first use: TTS, HMM ("a second HMM" precedes any first), MRR, CI, pp, EN/HI/GU/MR, POS (and the term Hinglish).
8. Over 45 words (16): Introduction 48; Related 54; System 56, 53; Evaluation 50, 54, 53; Repair 56, 61, 51; Limitations 62; Ethics 63, 57; Appendix 54, 53, 60. The patch splits 13.
9. Colour: Fig. 1 has no legend and its cascade boxes are green though all three outputs are unwanted (rule: green = correct); Fig. 2 colours the template red, Fig. 4 blue; Table 6 coloured correct template sentences blue, Table 5 green (fixed). Fig. 1 row 2 and Table 6 row 2 show Marathi alone, unlike Tables 4–5 and Fig. 4.
10. Figs. 1 and 4 set labels in bold roman (Fig. 1: upright glosses), unlike the tables. One rejection is "negation mismatch" (Fig. 1) and "negation missing" (Table 6, Fig. 4).

**P2**
11. Model names split (IN-/DICF5, RE-/QUEST, QWEN2.5-/0.5B-INSTRUCT ×3), "Ta-/ble" ×5, "Ap-/pendix" ×3; "Failure audit." stranded at the foot of the left column on p. 9 (a bare paragraph break overflows the appendix to page 11, tested); "page 4960–4962" (en dash in `pages`; use `4960--4962`, not in the diff).
12. Small caps reused for intent values; RQ1–RQ4 unreferenced and not questions; "From Audit to a Workable Build" figurative; stock phrase "sit in front of an AAC voice"; "used as released" ×3; abstract and Conclusion near-verbatim; "Acknowledgements" (US: Acknowledgments).

## 3. Concrete edits (old → new; every one is in the diff)
**main.tex (+1 alone).** `\llm{IndicF5}` → `\llm{\mbox{IndicF5}}` (also Vocos); add `\hyphenation{Appendix Table Tables Water}`; "Acknowledgments". Fig. 1 caption (still three lines): "requests" → "scenarios"; "explicit negation field) and speaks a template built from the user's labels; it accepts" → "explicit fields), and the system speaks a template instead; the gate accepts"; "Marathi glosses are given in quotation marks." → "Red: unwanted output or gate miss; blue: selection or template." (recolour column 2 red).

**Abstract (0).** raises/keeps/rises/reaches/exceeds → past tense; "no polarity error" → "no scored polarity error"; "integrated but was not evaluated; ... a screencast" → "integrated but unverified; ... a silent screencast".

**Introduction (0).**
- "Even when fluent, the cascade evaluated here fails in three ways (Figure 1): it replaced" → "Fluent output can still fail in three ways (Figure 1): the cascade evaluated here replaced".
- Split the ledger sentence after "a prompted cascade proposes a sentence" and end it "...; otherwise the system speaks a template ..." (was passive, "and otherwise a template ... is spoken"); delete "QWEN and INDICF5 are used as released."; cite Qwen at this first mention.
- "..., including the consequences of its fallback policy, for symbol-board users and the caregivers" → "... workflow for symbol-board users and the caregivers and clinicians who configure boards, including the effect of the template fallback."
- Bullets: "template floor" → "template fallback"; "A four-language demo with predictors trained on AAC dialogues" → "Four-language demo: predictors trained on synthetic AAC dialogues".

**Related work (0; Table 1 caption +1 line, absorbed).** "a style-adaptive TTS" → "style-adaptive text-to-speech (TTS)"; "check that preserves selected concepts" → "check of selected concepts"; "Indian-language sentences" → "Indic sentences". Table 1 caption: "Jellow and Karmakar and Sinha re-read" → "Jellow and the Karmakar--Sinha paper re-read"; add "EN, HI, GU, MR: English, Hindi, Gujarati, Marathi."

**System (0).** Fig. 3: "the validator's heuristic score, not a gate threshold" → "a heuristic score that the gate does not use". "a second HMM" → "a hidden Markov model (HMM)"; italicize *Quick Express*, *Un-Jumble*, *My Words* like *Speak*. "Request and concept ledger" → "Input and concept ledger". Eq. (1) and text: `intent(y)` → `act(y)`; "intent rejects 'I want' for feeling intents" → "The act test rejects 'I want' for feelings". Split the 56- and 53-word sentences. "a Hindi HMM, two English HMMs" → "four HMMs".

**Evaluation (−2).**
- Headings "RQ1: the gate preserves what the cascade loses." → "Effect of the gate."; RQ2 → "Remaining errors."; "RQ3: a template is a strong floor." → "Template baseline."; "RQ4: next-word prediction." → "Next-word prediction."
- "whose few-shot prompt reproduces a prompt example" → "which duplicate a few-shot prompt example"; "(v) the template alone" → "(v) the template baseline"; "Differences are paired, with 95% bootstrap intervals" → "Differences (in percentage points, pp) are paired, with 95% bootstrap confidence intervals (CIs)".
- Mechanical: results to past tense; "client payloads" → "client input"; "requests" → "scenarios"; `\textsc{request}` → `\emph{request}`; split the 54- and 53-word sentences.
- "Joining the eight ... by scenario identifier" → "Matching the eight ... to their scenarios"; "bounds what model phrasing adds without measuring it" → "cannot measure what model phrasing adds".
- Table 4 caption "model accepted model output, template template floor" → "model = accepted model output; template = template fallback".

**Repair (+1).** "four defects, each repaired before any new scenario was drawn and frozen by recorded file hashes" → "four defects, each repaired, with the build frozen by recorded hashes before any new scenario was drawn"; "Gate and templates:" → "Gate:" plus "Templates:"; "; driving the real page, the original client" → ". Tested on the real page, the evaluated client"; hybrid → pipeline; template floor → template baseline; title → "Failure Audit and Repairs".

**Limitations, Conclusion (0).** "Speech was synthesized in placeholder mode, so latency ... excludes synthesis and speech quality" → "Speech was a placeholder tone, so latency ... excludes synthesis, and speech quality"; "the Hindi dialogues are machine translations" → "The dialogues are model-generated and the Hindi ones machine-translated". Conclusion: "A small prompted language model can sit in front of an AAC voice when a deterministic gate decides what is spoken." → "A deterministic gate can decide which sentences from a small prompted language model reach an AAC voice."; "removed all polarity errors" → "left no scored polarity error".

**Appendix and generated tables (0).** Table 5 caption: commas and final period inside the closing quotes. Table 6: `\sel{I want Water.}`, `\sel{मला पाणी नको आहे.}` → `\kept{...}`. Fig. 4 caption "template floor" → "template fallback" (regenerate labels in Figs. 1, 2, 4). Table 7: ".50/.30/.15/.05" → "0.50/0.30/0.15/0.05"; "POS" → "part-of-speech". Appendix B off-task list made parallel ("if it is empty, exceeds 25 tokens, contains Latin text ..., or is a model refusal ..."). Table 2: "Unconstrained Qwen" in small caps, "Cascade before gate" → "Ungated cascade", "Template floor" → "Template baseline". Table 3 caption: "AAC-user utterances" → "synthetic AAC dialogues"; define hit@k and MRR.

## 4. Claims checked
| Claim | Evidence | Status |
|---|---|---|
| +18.3, +34.9, +20.0 pp; gaps 20.0, 12.0; 81%, 86% kept; 36 = 35 + 1 | Table 2 counts; numbers.tex | verified |
| hit@1 +1.1, +1.2; audit 35 + 2 = 37, 6, 8 | 381/356 of 2,220; 659/630 of 2,437; 108−71, 67−61, 175−167 | verified |
| "a Hindi HMM, two English HMMs" | Table 7 lists four | wrong: "four HMMs" |
| "AAC-user utterances" | Acknowledgements; Ethics | wrong: synthetic |
| "synthesized in placeholder mode" | Section 3 | wrong: placeholder tone |
| "four-part acceptance rule" | Eq. (1): five conjuncts | unclear |

## 5. Questions to the authors
1. Which four HMMs were trained; is the Gutenberg HMM one of the "two English HMMs"?
2. May Table 3 say "synthetic AAC dialogues"?
3. Which build produced Fig. 3, whose badges read "IndicF5 Voice" and "Natural Realization" for a template output?
4. May Figs. 1, 2 and 4 be regenerated ("template fallback", colour legend)?
5. Do RQ1–RQ4 stay as labels although no question is stated?
