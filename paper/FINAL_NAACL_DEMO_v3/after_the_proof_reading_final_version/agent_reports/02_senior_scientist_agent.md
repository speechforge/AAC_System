# Agent 2: senior scientist audit (technical validity and evidence)

Every number was recomputed from the archived result files, audit files and code, not copied from the paper.

## 1. Verdict and score
**71/100: borderline; Weak Reject becomes Weak Accept if the abstract claims are rescoped.** No numeric error found: Tables 2-3, the family table, latencies, CIs and repair numbers all reproduce. The risks are over-claims in the abstract and Section 3, an unmatched baseline, near-tautological headline metrics, and analyses that existing data already supply. Rubric: fit 14/15, contribution 13/20, evidence 21/30, demo 10/15, writing 13/20.

## 2. What is missing (ranked)
**P0**
1. **Abstract and Section 1 say the gate confirms the "intended act"; Limitations say its intent test is English-only.** The act test is an English "I want" pattern for feeling intents plus a question cue, and it never fires when the client calls a feeling a request (27 of 32). Deployed wrong act: 54/175 (client), 17/175 (explicit). Section 1 says "four-part rule"; Equation 1 has five terms.
2. **"No polarity error" and "all 215 kept" are near-tautological and unscoped in the abstract and Conclusion.** The template echoes the labels, and the gate's negator test is the same presence predicate as the scorer's (not clause-scoped): the gate accepts "I am not a fruit. I do not eat fruits." and the scorer calls its polarity correct. Only RQ1 hedges.

**P1**
3. **Gate false-accept evidence is missing for the primary (client) condition.** Final cascade candidate against scorer v1: client, 116 accepted, 57 correct (49%); the gate admits 59 of 110 failing candidates (54%) and rejects 8 of 65 passing ones. Explicit: 108 accepted, 71 correct; admits 37 of 104 failing (36%). English accepted-correct is 2/16 (client) and 5/18 (explicit). RQ1 reports only 71/108.
4. **The pooled gate effect is English-driven.** Indic-only (HI+GU+MR; 129 items, 45 groups): +10.1 pp [4.8, 16.0] client, +25.6 [17.3, 34.4] explicit; English alone +41.3 [26.1, 56.5]. Gujarati client gain: +2.4 pp [0.0, 7.1] (21 vs 20 of 42). Template minus deployed, Indic-only: 7.8 pp [2.3, 14.2] client, 17.1 [10.1, 24.4] explicit. No per-language CI is printed though A7 holds them.
5. **Baseline fairness.** "Unconstrained Qwen" is zero-shot, labels only (no act, negation, ledger or examples); 132 of its 167 failures lack only an act marker (A4). The matched few-shot one-pass comparator already exists: stage 1 alone scores 63/175 (client) and 67/175 (explicit) against 65 and 71 for the full cascade; stages 2-3 add 2 and 4 scenarios, all English. For HI, GU and MR the cascade text equals the stage-1 text in 129/129 scenarios, yet the verifier call costs a median 4.6-4.7 s of a 6.6-10.0 s request.
6. **Scorer scope.** "First-person" is enforced only for English (pattern "the user"); Indic third person passes. Headline counts use scorer v1 (marker-list gaps in A3, A5); v2 also moves the pre-gate counts (65 to 63, 71 to 72), omitted from the paper. The abstract's "95%" template figure is a v1 artifact (v2: 175/175).
7. **Provenance and green marks.** The failure audit was classified by an AI assistant (A3 file), not "the authors"; RQ3 calls the Gujarati negated-feeling templates "valid" unhedged (A3: phrasing for anger, love, fear "may be unnatural"). Table 5 marks green some Hindi strings that look ungrammatical or semantically off to this auditor (not a native-speaker judgment): "फ़ोन करना गया है, मुझे डॉक्टर चाहिए।", "मुझे पीना दूध चाहिए।", and "फल नहीं है, नहीं चाहिए।" (asserts absence).
8. **Speech routing.** The default client sends `indic_female` (a Punjabi reference clip) with every request, English included; without the gated weights the server returns a tone that the client plays, so browser speech is never reached. "Browser speech serves as the fallback" needs that scope.

**P2**
9. Pooled CIs come from the audit's grouped bootstrap (seed 20261113), not the frozen scenario bootstrap (seed 20261111): say so.
10. "3 of 276": the rule marks 7 negated (4 are the NO symbol), so 3 of 272.
11. Figure 1 colours encode stage (gate boxes red even for the accepted row, wrong cascade text green); Tables 4-6 encode verdict, and red also marks polarity inversion and rejected text beyond the legend. Figure 4 omits "web-client input", and its Marathi spoken sentence differs from Figure 1 row 2 (explicit).
12. Table 3's rounded columns give +1.2 (EN) and +1.1 (HI), against the text's +1.1 and +1.2.
13. Repair: "matched one-pass 8/175" is a different run from Table 2's 8/175; "client and explicit 175/175" coincide by construction; "four defects" has three labelled items. Hinglish "client" rows are API payloads (the UI cannot code-mix).
14. The explicit feeling intent changed FEELING to STATEMENT after a 54-request pilot (archived FINAL_CONTEXT 7); undisclosed.
15. "Four-language demo with predictors": only EN and HI have one, trained on synthetic gpt-4o-mini dialogues (Hindi machine-translated); Table 3 says "AAC-user utterances".
16. Three scored "accepted model" rows are template sentences made inside the verifier (EN SAD, client and explicit; EN NO+HAPPY, explicit).
17. Acknowledgements call all numbers "regenerated"; CIs, repair counts and latencies are typed (all verified): say "checked".

## 3. Concrete edits (old -> new; net lines)
- Abstract: "the gate raises success" -> "the gate and its template fallback raise success"; "confirms the selected concepts, polarity, and intended act" -> "finds the selected concepts, a matching negation, and no unrequested content"; "with no polarity error" -> "with no missing or spurious negator" (0).
- Abstract: "A suffix-trie predictor exceeds trigram backoff by 1.1 hit@1 points in English and 1.2 in Hindi." -> "The gate still admits 59 of the 110 failing cascade outputs under client payloads." (0; predictor result stays in Section 4).
- Intro: "a four-part acceptance rule" -> "a five-test acceptance rule"; "predictors trained on AAC dialogues" -> "English and Hindi predictors trained on synthetic AAC dialogues" (0).
- Section 3: "the verifier returns a verdict and a minimal rewrite, which is advisory" -> "the verifier's verdict is unused, and its rewrite changes English candidates but never an Indic one" (0). "browser speech ... serves as the fallback" -> "browser speech voices the literal labels, and generated text only if the server returns no audio" (0).
- Section 4: "(ii) the same Qwen with one unconstrained prompt" -> "(ii) ... one zero-shot prompt (labels only)" (0). Protocol: "is a first-person sentence in the target script" -> "... (third person is detected only by the English phrase 'the user')" (+1; cut "from the same response as the deployed output").
- RQ1, after the +18.3 sentence: "(HI, GU, MR alone: +10.1, 4.8 to 16.0). The cascade's first stage alone scores 63/175 and 67/175; later stages add four scenarios, all English. Under client payloads 57/116 accepted and 40/59 fallbacks are correct." (+2; offset by shortening the Table 2 caption's literal-join sentence to "A literal join succeeds on 0/175 (no act marker).").
- RQ2: "marks 3 of 276 single-symbol selections" -> "wrongly marks 3 of 272 non-negated single-symbol selections" (0). RQ3: "The valid template sentence" -> "The template sentence, well formed to us but not native-checked,"; Appendix B "(the authors' classification" -> "(AI-assisted classification" (0).
- Repair: "matched one-pass Qwen prompt: 8/175" -> "a new one-pass prompt with the repaired fields: 8/175"; "the same cascade without gate and fallback by" -> "the same cascade without gate and fallback (88/175, in-sample) by" (0). Table 4 caption (legend reused by Tables 5-6): "green: successful sentence" -> "green: passes the scorer"; Figure 4 caption: add "web-client input" (0).

## 4. Claims checked
| Claim | Evidence | Status | Correction |
|---|---|---|---|
| Table 2 (7 rows, 6 diagnostics), literal join, 215 instances (135 + 40 scenarios), family table (36 cells), Hinglish 0/8, 4/8, 5/8, 6/8, 8/8 | scored.csv | verified | none |
| RQ1-RQ2 counts: 81%/86% kept; 36 = 35 dropped + 1 spurious; 108/71, 67/61; 62%; wrong act 54 vs 17; 55% to 75% | scored.csv | verified | add client counts |
| Paired CIs (+18.3, +34.9, +20.0, -20.0, -12.0) | A7; own grouped bootstrap, 46 groups, 10,000 | verified | post hoc |
| 27 of 32; 3 of 276 | A6; client rule re-applied to 69 symbols x 4 | verified | denominator 272 |
| Eight template failures are Gujarati negated feelings; three quoted strings | scored.csv | verified | "valid" unverifiable |
| Table 3 (all cells), 381/356, 659/630, +1.1, +1.2, overlaps, OOV | prediction.json, hmm_eval.json, A8 | verified | note rounding |
| Latency 6.05, 9.75, 7.45, 6.51 s; 12.04-18.76 s | raw_pipeline.jsonl (294 records) | verified | none |
| 9.9 s, 20.8 s, 31 runs; 44 s CPU; Flan-T5 378/384, 379/384, 0/172, 31.8 ms; HMM weights, beam 64 | B_speech_path, D_clean_env, refiner_repro, models_def.py | verified | none |
| Failure audit 12/10/9/4 + 2; 6 and 8 gaps | A3 | verified | AI classifier |
| Nine exclusions | prompt builder re-run, both conditions | verified | none |
| 59/184 (27 + 32), 0 repaired; 97 to 95, 132 to 138, 167 to 175; 49.7 [42.3, 57.1] (87/0); 8/175 | payload captures, T1/T2 legacy | verified | P2 13 |
| Figures 1, 4, Tables 4-6: every recorded string, route, flag | scored.csv, raw_pipeline.jsonl, repaired frontend | verified | colours (P2 11) |
| Ledger 21 words; 12/9/9 examples; T 0.1, greedy Indic; two attempts; fallback unvalidated; intent rules | archived llm.py, app.py, semantic.py, index.html | verified | none |
| Verifier "advisory"; "four-part"; "confirms intended act" | same | wrong | edits above |
| IndicF5 card: 11 Indian languages, no English, 1,417 h; browser chains | model card; index.html | verified | Hindi also falls back to en-IN |

## 5. Questions to the authors
1. Who classified the 51 failure rows and wrote the glosses and templates, and has a Gujarati or Marathi speaker read Tables 4-5?
2. Why keep scorer v1 in Table 2 once v2 exists; can v2 columns sit beside it?
3. Was the grouped bootstrap chosen after the freeze?
4. Will the release drop the verifier and the retry for greedy Indic output (identical text, extra 4.6 s)?
5. Which voice does the default client use for English, and will it fall back to browser speech when the weights are absent?
