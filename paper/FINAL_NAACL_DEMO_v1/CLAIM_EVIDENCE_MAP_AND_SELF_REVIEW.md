# Indic AAC Studio — NAACL 2027 demo paper: claim–evidence map, self-review, action items

This file is editorial material for the authors. None of it belongs in the manuscript.

Paper: `main.pdf` (9 pages: body 6, Ethics/Acknowledgements/References through page 7, appendix 2).
Numbers in the text come from `generated/*.tex`, which `make_tables.py` regenerates from `eval/results/*.json`.
Independent check: every cell of Table 2 (all systems, both payload conditions, 175 primary scenarios) was recomputed from `scored.csv` and matches.

## 1. Claim–evidence map

| # | Claim (where) | Evidence | Status |
|---|---|---|---|
| 1 | Gate raises success 71/175 (41%) → 132/175 (75%) with explicit intent/negation; 65/175 (37%) → 97/175 (55%) with client-inferred fields (Abstract, Intro, RQ1) | Table 2; recount of `scored.csv` (`llm3_pre` vs `deployed`, conds `st`/`ui`) | supported |
| 2 | Deployed output keeps all 215 required concepts (Abstract, RQ1) | Table 2 "Kept" column; holds partly by construction, because the template echoes the labels | supported (stated as such in RQ3) |
| 3 | Pre-gate cascade makes 36/175 polarity errors with explicit fields (35 dropped, 1 spurious); the gate removes all (0/175) (Abstract, Intro, RQ1) | Table 2; `summary.json` polarity_drop/spur | supported |
| 4 | An unconstrained prompt of the same Qwen model succeeds on 8/175 (5%) (Abstract, Intro) | Table 2 "Unconstrained Qwen" | supported for one prompt and one 0.5B model; the paper says "one unconstrained prompt" |
| 5 | A template alone reaches 167/175 (95%) explicit, 118/175 (67%) client, and is ahead of the pipeline except Hindi/client (RQ3, Abstract, Conclusion) | Table 2; per-language paired differences in `summary.json` | supported; disclosed as the system's floor |
| 6 | Gate admits model text for 108/175 (62%) of explicit requests; 71/108 accepted outputs fully correct; 61/67 fallbacks correct (RQ1) | `extra.tex` (XGateAccS, XGateOkS, XFbOkS) from `scored.csv` `fallback`/`validated` | supported |
| 7 | Remaining errors are mostly intent: 54/175 wrong-act under client payloads → 17/175 explicit; client marks 27/32 feeling selections as requests; 3/276 single-symbol selections falsely negated (RQ2) | Table 2; `ui_audit.json` | supported |
| 8 | Suffix-trie predictor beats trigram backoff by +1.1 pp (EN) and +1.2 pp (HI) hit@1, CIs [+0.5, +1.8] and [+0.5, +1.9] (Abstract, RQ4, Table 3) | `prediction.json`, paired bootstrap over source conversations | supported; effect is small and the paper states it as such |
| 9 | Latency medians 6.05/9.75/7.45/6.51 s accepted, 12.04–18.76 s fallbacks, GTX 1650 4 GB, 283 unique requests (RQ4 runtime) | `summary.json` latency block (per-language n = 69+70+72+72 = 283), `env.json` | supported (speech synthesis excluded, stated) |
| 10 | Offline run: ready in 10.2 s, first request 13.94 s; only outbound attempt was Google Input Tools fallback (RQ4 runtime) | `offline_check.json`, `offline_summary.json` | supported |
| 11 | Trained components and settings (Table 5, Appendix C): flan-T5-small 76,961,152 parameters, 960 updates, 378/384 exact match, 172 negated payloads with no negation error; HMM sizes; trie 15,505 sentences, depth 181 | `refiner_repro.json`, `hmm_eval.json`, `env.json`, `FINAL_CONTEXT.md` | supported |
| 12 | Four-language demo: 69 symbols, 9 categories, EN/HI/GU/MR, Quick Express, My Words, voice cloning, Un-Jumble, accessibility dock (Section 3) | Screenshots in Fig. 2/App. Fig. 3b, workflow trace, UI audit | supported |
| 13 | Related-work table: Cboard (46 languages, HI/GU/MR not named), Jellow (24 languages incl. HI/MR/GU, Google TTS), Avaz, Francis et al., ConnecTone, Mohan et al., SpeakFaster | Vendor pages and papers read on 2026-11-12; "n.s." marks what a source does not state | supported; scoped to the sources read |
| 14 | "None of these sources documents a deterministic check on model-generated Indian-language sentences" (Related Work) | Same sources | supported only as a scoped statement; the paper makes no claim about undocumented products |
| 15 | 26.8 million persons with disabilities, 2.21% (Census 2011) (Intro) | Cited via a Governance Now article summarizing the Census 2011 figure | supported by a secondary source; swap in the primary Census/DEPwD table if you have it |
| 16 | Code released under Apache-2.0; reviewer package and screencast at the repository URL (Section 5, Abstract) | Release statement only | **needs action** (see items 1–3 below) |
| 17 | Gujarati example output "મને પાણી ના જોઈએ છે." as an accepted informal negation (Fig. 2b, Trace B) | Real screenshot; gate check passes | supported; the gloss labels it informal negation |

## 2. Five-dimension self-review (skeptical-reviewer pass)

**Contribution.** Q: Is this an API wrapper around Qwen and IndicF5? A: The paper states what is new: the ledger and four-part gate with retry and template floor, the API that carries intent and polarity, trained predictors and HMMs, and a frozen paired protocol, plus a four-locale demo. Residual risk: a reviewer may weigh the lexical gate as modest; the evaluation shows what it changes (36 → 0 polarity errors, 100% concept retention) rather than claiming fluency gains.

**Writing clarity.** Q: Can a reader follow request → ledger → cascade → gate → template → speech? A: Fig. 1, the walkthrough, Eq. (1), and Fig. 2 callouts follow one path; terms (ledger, gate, template floor, client vs explicit payload) are defined once and used consistently. Hindi, Gujarati, and Marathi examples carry English glosses.

**Experimental strength.** Q: Are the baselines fair? A: Literal join, unconstrained Qwen, pre-gate cascade (same response as the deployed output, so gate and fallback are isolated), deployed, and template-only run on one frozen set with paired bootstrap CIs. The template-only result (95%) is reported up front because it beats the pipeline on a lexical criterion; it is framed as the system's floor. Residual risk: one small model and one unconstrained prompt.

**Evaluation completeness.** Q: Does the evaluation answer the demo-track questions? A: RQ1–RQ4 cover faithfulness, error origins, template comparison, prediction; runtime, offline operation, and degradation are reported. Scope limits (lexical scorer, single samples for English/code-mixed, no user study, no screen-reader testing) appear once in Section 5 and in the abstract's wording; none changes the interpretation of the reported numbers.

**Method design soundness.** Q: Does the gate guarantee correctness? A: No, and the paper says so: it checks concepts, polarity, and limited intent cues. The fallback template is returned without re-validation (stated), and the client's intent inference produces most wrong-act errors (RQ2), which points to the engineering fixes in the Conclusion.

## 3. Baselines carried over from the two earlier versions

The five systems in Table 2 are the frozen protocol of the Claude-written version. The product comparison (Table 1) was rebuilt from vendor pages: the two earlier drafts disagreed about Jellow and Avaz, and Table 1 follows the vendor pages read on 2026-11-12. Claims that could not be verified (Census speech-impairment counts, speaker counts, SpeakFaster percentages, Vertanen language coverage) were dropped rather than kept.

## 4. Action items for you (outside the manuscript)

1. **Repository URL.** `\demourl` points to `github.com/speechforge/AAC_System`, which returned 404 when checked. Make it public (anonymized for review if required) or change the macro in `main.tex`.
2. **License.** Add the Apache-2.0 `LICENSE` file or change the license sentence; confirm you may redistribute the synthetic dialogues and voice prompts.
3. **Authors.** Only the first author and affiliation are filled in (from your profile). Add co-authors, order, and affiliations.
4. **Screencast.** The existing screencast is 2:03, silent, and captioned. The call prefers narration; record an audible one before submission.
5. **AI-use disclosure.** The Acknowledgements name Claude and ChatGPT/Codex; confirm the wording matches what you want to disclose.
6. **Submission format.** `main.tex` uses `[preprint]` (author names shown). Check the OpenReview instructions for `[review]` vs `[preprint]`.
7. **References.** Karmakar & Sinha (2024): the second author comes from the ChatGPT-version bib; check it against the ICON proceedings. Census figures are cited through a news article (claim 15).
8. **New result.** The explicit-fields run (36 → 0 polarity errors, 41% → 75% success) is new relative to both earlier drafts and is the headline; the client-payload numbers (37% → 55%) are reported beside it.
9. **Template-only baseline.** It beats the pipeline on the lexical composite. The paper states this in the abstract, RQ3, and the Conclusion; expect reviewers to ask what model phrasing adds, and plan a native-speaker rating study.
10. **Figures.** Diagram labels were made neutral (no "absent/mock" wording); the UI screenshots are the originals.
