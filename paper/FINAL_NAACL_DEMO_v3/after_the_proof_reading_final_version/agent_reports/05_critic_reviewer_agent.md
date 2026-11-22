# Agent 5: critic review of the v3 draft (Indic AAC Studio, NAACL 2027 System Demonstrations)

Adversarial demo-track reviewer; Table 2 recomputed from `scored.csv`; no manuscript file touched.

## 1. Verdict and score

**Summary.** A four-language web symbol board. A prompted 0.5B Qwen cascade proposes a sentence; a rule-based gate passes it or substitutes a template built from the user's labels. On 175 frozen scenarios, gate plus template beats the ungated cascade (client 65 to 97, explicit 71 to 132) with 215/215 concepts and no scorer-detected polarity error, yet a template alone scores higher (118, 167). A repaired build is only a 175/175 regression target; no speech was produced.

**Strengths.** Candid (template floor, scorer defects, regression-not-test); paired design with bootstrap CIs, every Table 2 count reproducible; under-served languages.

| Criterion | Pts | Justification |
|---|---|---|
| Problem and track fit | 13/15 | Safety-critical Indic AAC; but no speech, no AAC stakeholder input. |
| Technical contribution | 12/20 | Sound ledger-gate-floor idea; evaluated gate is 127 lines of lexical rules, English-centred act cues. |
| Experimental evidence | 17/30 | Honest, paired; same-team lexical scorer, weak baselines, no human check; system loses to its own floor. |
| Demo and reproducibility | 8/15 | Link 404, no licence, silent video, placeholder tone, 6-19 s latency. |
| Writing and presentation | 16/20 | Careful, concise; label drift, unreadable Figure 3, residual absolutes. |
| **Total** | **66/100** | **Weak Reject, confidence 4/5** |

**What would change my recommendation (cheapest first).** (1) Public repository with LICENSE, tags for both builds, fixed README, video link. (2) Section 3 edits. (3) Recaptured Figure 3; forest plot of existing CIs. (4) Pilot native-speaker check of template-versus-hybrid pairs (packet exists); audible video. (5) A larger open model and few-shot one-pass baseline behind the same gate. (6) Clinician review.

## 2. What is missing

**Five most damaging weaknesses (P0), with cheapest honest fix and page cost.**

1. **W1 Demo not accessible.** Repository URL returns 404 (CFP: no link, desk rejection); no LICENSE exists (Apache-2.0 unverifiable); repaired build uncommitted; video claimed "at \demourl" (CFP: YouTube link or supplementary MP4; silent allowed). README names a private conda environment and omits `python-multipart` (their clean test added it); there English "Water" returned the template after 44 s on CPU, with a placeholder tone. GPU latency of 6-19 s is never weighed. *Fix:* publish, tag, correct README, upload video; 0 lines.
2. **W2 The generated sentence's value is unmeasured.** Paired by scenario (recomputed), the deployed output beats the template in 1/175 (client; a template-form gap) and 0/175 (explicit), and loses in 22 and 35: the gate gain is entirely the template. The 8/175 baseline fails mainly on a missing act marker and keeps more concepts (199/215) than the cascade (175/215). One 0.5B model, no existing-tool comparison; the CFP rejects off-the-shelf assembly lacking substantive contribution, domain-grounded design or rigorous evaluation. *Fix:* paired counts (+1 line), baseline caveat (+0.5), reframe as safeguard plus audit.
3. **W3 The yardstick is weak.** The scorer is code-independent only (same team, same negator-presence test as the gate), so 215/215 and zero polarity errors are near-tautological; the template is built from the labels. Success credits ill-formed output: Table 5 marks as passed "I want Call Doctor." and Hindi "फ़ोन करना गया है, मुझे डॉक्टर चाहिए।" *Fix:* Table 5 caveat (+1 appendix line), "coded separately" wording, v2 gaps (+1).
4. **W4 Evaluated is not demonstrated.** Tables 2-4 describe the archived build; reviewers run the repaired one, scored 175/175 on the scenarios that informed its repairs. Figure 3 shows the superseded interface (chip "IndicF5 Voice" though no IndicF5 audio existed; no Message-type control) under "The running build", with UI text of 2-3 pt. *Fix:* recapture from the repaired build, cropped to canvas and output card; name the build (-4 to +0.5 lines).
5. **W5 Absolutes and selective reporting.** Abstract: "only if a deterministic gate confirms ... intended act", yet the act test is English "I want" plus question cues and the forbidden and time lists are English-only (`semantic.py`): two of five checks are effectively inactive for Hindi, Gujarati and Marathi, and 12 of 37 accepted failures are a negated want for a negated feeling. Also "contract", "preserves", "removed all polarity errors" and the README's "zero-hallucination". Gate precision appears for explicit fields only (71/108, 61/67), not the primary condition (57/116 = 49%; 40/59). Of the pooled +18.3 points, English supplies 19 of 32 gained scenarios, Gujarati 1 (CI 0 to 7). Cascade polarity errors are 2 (client) versus 36 (explicit): explicit payloads also drop the "No" entity. *Fix:* edits 1-5 (net +1.8).

**Other P1.** *Labels:* Figure 1 mixes client (rows 1, 3) and explicit (row 2) but flags only row 2; unlabeled Figure 4 (client) shows Marathi "मला नाही पाणी हवे आहे." where Figure 1 shows "मला पाणी नको आहे."; Section 5's "client and explicit inputs" is the repaired client, which sends gold fields. *Scorer v2:* "adds the valid constructions ... 97 to 95" cannot lower a count; v2 also scopes negation (5 gained, 7 lost), Appendix B defines v1 only, and template gaps become 13.1 and 21.1 points. *AI disclosure* is where the CFP requires but omits gold annotations, lexicons, figure scripts, reference checks and who wrote the original snapshots.

**P2: float audit.** Limits respected: Conclusion ends p. 6 at y=703 of 775 (about 5 lines spare), appendix exactly pp. 9-10. `xref_audit` OK (12 floats and Equation 1 cited); `native_text_check` 30/30 recoverable, no "चा हए"; no clipping (Figure 2 arrow labels cut box borders); Table 5's 24 cells match `scored.csv`; Table 4-6 and Figure 4 captions match their colours, marks and tags. Figure text is 6-7.5 pt (down to 5.9). Blue, green and red have luma 75-78/255, so colours vanish in grayscale (Table 4 red "I want" versus blue "Angry"); marks label cells only. Figure 1 colours stages (green cascade output even when wrong, red "Accepted" gate), contrary to the verdict palette of Figure 4 and Tables 4-6; Figures 1-2 give no key. Numbering clashes: Figure 2 boxes 1-4, Figure 3 callouts 1-5 (4 = generate), Figure 1 columns 1-4. Table 4 is cited before Table 3, Appendix Table 7 before Table 1; Figure 3 is cited p. 2, placed p. 4. **Data plot:** none; a forest plot of paired differences by language and condition (28 per-language paired-CI macros in `numbers.tex` are unused) fits Figure 3's slot.

## 3. Concrete edits (by file; net body lines)

1. `04_eval.tex` RQ3: after "ties it only in Hindi under client payloads" add "; paired by scenario, the deployed output succeeds where the template fails in 1/175 (client) and 0/175 (explicit) and fails where it succeeds in 22 and 35". **+1**
2. `04_eval.tex` RQ1: "template fallbacks in \XFbOkS{}" to "... \XFbOkS{} (client: \XGateOkU{} and \XFbOkU{})". **+0.5**
3. `04_eval.tex` Protocol: "written independently of the gate" to "coded separately from the gate (same team)". **0**
4. `00_abstract.tex`: "a deterministic gate confirms the selected concepts, polarity, and intended act" to "a lexical gate finds the selected concepts and negation and passes a limited act check"; "integrated but was not evaluated" to "untested (gated weights absent; no speech was produced)". **0**
5. `05_limits.tex`: "the gate kept every selected concept and removed all polarity errors" to "the gate and template floor kept every selected concept and left no scorer-detected polarity error". **+0.3**
6. `05_repair.tex`: "adds the valid constructions that version 1 missed" to "adds valid constructions and scopes negation to the clause (client: 5 gained, 7 lost)", ending "...; the gaps to the template become 13.1 and 21.1 points"; "with client and explicit inputs" to "(the repaired client sends gold fields, so the inputs coincide)". **+1.5**
7. `main.tex` Figure 1: "(row~2, explicit negation field)" to "(rows~1, 3 client payload; row~2 explicit negation field)"; appendix Figure 4: "(recorded outputs)" to "(recorded outputs, client payload)". **+0.3**
8. `tab_pred.tex`: "on AAC-user utterances" to "on synthetic AAC-style dialogues". **0**
9. `07_appendix.tex` Table 5 caption: add "\okmark{} means the lexical scorer passes the output, not that it is fluent (e.g., ``I want Call Doctor.'')". **+1 appendix line (about 2 spare)**
10. `06_ack.tex` (unlimited): add the omitted AI uses listed in P1.
11. `03_system.tex` offsets: delete ", and an accessibility dock adjusts size, contrast, and speech speed", adding "and" before "Un-Jumble" (**-0.7**); "two HMMs trained on streamed text ... ran without" to "two optional HMMs (Appendix Table~\ref{tab:models}) were absent from the evaluated build" (**-1**). Body net about +1.9 against 5 spare lines.
12. Floats: recapture Figure 3 as in W4; move `\input{generated/tab_pred}` after the RQ4 paragraph so first citations follow table order.

## 4. Claims checked

| Claim | Evidence | Status and correction |
|---|---|---|
| Table 2 counts and flags; 215/215; no polarity error | `scored.csv`, audit A1 | verified; 215/215 near-tautological, say "scorer-detected" |
| 36/175 polarity errors (explicit) | `raw_pipeline.jsonl` | verified; client has 2; payloads differ beyond the fields |
| Accepted 71/108, fallbacks 61/67 | `scored.csv` | verified (explicit only); primary 57/116, 40/59 |
| v2 "adds valid constructions", 97 to 95 | `B_scorer_effect_cases.csv` | misleading: 5 gained, 7 lost |
| Eight template failures are Gujarati negated feelings | audit A3 | verified; scorer gaps |
| hit@1 +1.1 EN, +1.2 HI | audit A8 | verified (+1.126, +1.190); rounded table gives 1.2, 1.1; repeat-filtered +0.97, +1.02 unreported |
| Gate "confirms intended act" | `semantic.py` | overstated for HI, GU, MR (feeling test English-only) |
| Client payloads "as the web client builds them" | `build_scenarios.py` | re-implemented; unverified against page |
| Apache-2.0; video at URL | URL 404; no LICENSE | unverifiable |

## 5. Questions to the authors

1. The model path wins 1 and 0 paired scenarios and loses 22 and 35; what blind human result would justify 6-19 s per sentence?
2. Why do cascade polarity errors rise from 2 to 36 under explicit fields; what else changes in that payload?
3. Were client payloads re-implemented (`ui_infer`) or captured; do captured payloads match for 184/184?
4. In the repaired build, what share of spoken sentences on the 175 regression scenarios is model output, per language?
5. Who with AAC or native-speaker expertise shaped board, templates and acts; which code did the authors write unaided?
