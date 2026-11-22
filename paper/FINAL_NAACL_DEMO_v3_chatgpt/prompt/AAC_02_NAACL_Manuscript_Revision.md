# Claude Code prompt 2 — Revise the Indic AAC Studio NAACL 2027 demo paper

Open the Indic AAC Studio repository and invoke "/ravindras-paper-writing-skill" for this task. Read its active "SKILL.md" and referenced guidance before editing. For a noninteractive session, resolve the same exact skill in the repository or the user's configured Claude skills directory and read it directly if the slash command is unavailable. Record the actual outcome in the revision notes. If the skill is unavailable, identify the checked locations and continue with the official venue template and the evidence-backed corrections below.

Read the manuscript's LaTeX, BibTeX, figures, current PDF, original project "CONTEXT.md", and the repository-root "FINAL_CONTEXT.md" from the experiment run. Resolve numbers and system behavior from the recorded experiment artifacts where the context is ambiguous. Keep the existing author list and affiliations unless an author supplied corrections. Use US English. Edit the actual source and return a compiled, review-ready PDF plus the editable sources.

## Conference and structure

- Check the current [NAACL 2027 System Demonstrations call](https://2027.naacl.org/calls/system_demonstration/) and the [official ACL template](https://github.com/acl-org/acl-style-files). The call specifies single-blind review with author names, a maximum of six main-content pages, a maximum of two appendix pages, a video of up to 2.5 minutes, and a working demo or downloadable package link. Verify allowances for supplementary sections and fully disclose material generative AI use in Acknowledgments as directed by the call.
- Open the abstract with the communication problem, then state the approach, the verified effect of gating, the comparison with the template, and demo availability. Keep the detailed language example in the introduction. Use one example to explain the need for grammatical realization, then state the scoped novelty. The central contribution is the application and evaluation of explicit concept, polarity, and act checks in an Indic symbol-to-speech workflow, including the consequences of its fallback policy.
- Distinguish related tasks and closest prior art. Cover Compansion's grammatical expansion, Karmakar and Sinha's symbol-to-text work including Bengali, Jellow's sentence-building and existing support for Gujarati, Hindi, and Marathi, and ConnecTone or SpeakFaster where they clarify the input/output distinction. Describe product claims as documented capabilities and ground the novelty in the exact gate and evaluation. Verify vendor edition/version, cite primary sources, and scope all priority claims.
- In System Design, show symbol selection and browser inference, the concept ledger, candidate realization, the validation checks, fallback, and speech routing. Distinguish live, optional, and evaluated components. Report language coverage for text generation, next-word prediction, and speech individually where they differ. Explain whether IndicF5 or a browser voice actually speaks each language. A visually compact architecture figure and one readable interaction figure should expose the decision path. Label replayed traces as recorded outputs and preserve their words, including failed outputs.
- In Evaluation, lead with the actual web path. Present explicit gold fields as a controlled diagnostic and label user-selected intent separately if measured. Compare the recorded ungated cascade, deployed output, and matched template. Use the one-prompt Qwen result as a diagnostic with exact settings. The old manuscript reports 65/175 to 97/175 with web input versus 118/175 for templates, and 71/175 to 132/175 with gold input versus 167/175 for templates. Use updated figures only when the context and trace files support them. Describe whole-policy effects accurately when gate, retry, and fallback jointly affect the result.
- Define scenario success and concept-instance retention with their own denominators. Explain the 184-to-175 exclusion and that the scorer is lexical. Align the off-task definition with legitimate user refusals, the formula with the implemented checks, and all absolute counts with their labels. If confirmed by the archived records, report that 37 of 108 accepted outputs failed full scoring and six of 67 template fallbacks failed with gold fields. Clarify the denominator for the client feeling-inference diagnostic, and check the English and Hindi hit@1 differences using unrounded counts. Keep a concise statement of material limitations near the relevant evidence.
- Use measured human judgments, runtime, or speech results only when backed by the named artifacts. Where the verified result is backend-local inference, write that claim with its scope. Distinguish the browser's CDN dependence from model execution. Disclose placeholder-mode measurements and the exact timing endpoints. Do not turn a regression-set target of 175/175, checker acceptance, or a perfect concept-retention count into a semantic, usability, or speech-quality guarantee. Keep missing dependencies and revision advice in the author notes.

## English and typography

- Keep the official Latin body font, point sizes, margins, captions, and reference style. On first mention in prose, use restrained emphasis at the same size, for example "\emph{Qwen2.5-0.5B-Instruct}". Then use the canonical names consistently, including "IndicF5", "Vocos", and "FLAN-T5-small" if that is the verified spelling for the cited resource. Use typewriter only for an exact code or repository identifier where appropriate. Distinguish "template baseline", "template fallback", "communicative act", and "polarity".
- Use the official Unicode example with XeLaTeX or LuaLaTeX for Indic text. Apply locally scoped OpenType fonts for Devanagari and Gujarati, with fonts available on Overleaf or supplied as properly licensed files when necessary. Use upright native-script text, clear language labels, and an italic English gloss. Use genuine typographic emphasis in the native script only where the selected font and a render check support it. Example preamble and body pattern, to be adapted to the existing project

~~~latex
% XeLaTeX or LuaLaTeX. Load fontspec once in the official ACL template.
\newfontfamily\aacdevfont[Script=Devanagari]{Noto Serif Devanagari}
\newfontfamily\aacgujfont[Script=Gujarati]{Noto Serif Gujarati}
\DeclareRobustCommand{\aacdev}[1]{{\aacdevfont #1}}
\DeclareRobustCommand{\aacguj}[1]{{\aacgujfont #1}}

\noindent\textbf{Hindi}\enspace \aacdev{मुझे पानी चाहिए।}\par
\noindent\textbf{Gujarati}\enspace \aacguj{મને પાણી જોઈએ છે.}\par
\noindent\textbf{Marathi}\enspace \aacdev{मला पाणी हवे आहे.}\par
All three express \emph{“I want water.”}
~~~

- In the submitted prose, write the example as a clear sentence or a compact labeled figure or table. Verify the strings "मुझे पानी चाहिए।", "મને પાણી જોઈએ છે.", and "मला पाणी हवे आहे." against source and rendered PDF. In a corrected prose illustration, use the board label \emph{Water} and describe a water request, since a single symbol can express different acts. In actual output traces, preserve the observed wording. Diagnose "चा हए" in the pasted extraction by checking both the Unicode in the LaTeX source and the typeset glyphs. Ask an author or a native reviewer to verify nuanced language claims such as person, register, and negation scope.
- Replace absolute claims such as “the model cannot change what was selected” with an implemented description of the acceptance checks and a benchmark-scoped result. Remove unnecessary rhetorical subheadings and duplicated motivation or availability text. Use "open-source" adjectivally and the proper names "English", "Hindi", "Gujarati", and "Marathi". Standardize precision and spell out percentage-point differences where needed to avoid confusion with relative percentages.

## References and access dates

- Verify title, author order, venue, year, volume, page range, location, and persistent identifier from the publisher or ACL Anthology. Use structured BibTeX fields and publication-specific entry types. Protect case-sensitive terms in titles. Where prose or a user-controlled style permits labels, use "vol. 30" and "pp. 5767–5777". The submission bibliography inherits the official style, including its labels.
- When a web access date is appropriate, use the exact display pattern "Last Accessed Date: September 3rd, 2026" with the actual verified date for that source. Format the suffix with "\textsuperscript{rd}" if the project uses raised ordinals. Place "\url" and the access-date text in a normal footnote or a template-supported bibliography field. For example, this is a format-only demonstration

~~~latex
\footnote{\url{https://example.org/resource}
  (Last Accessed Date: September 3\textsuperscript{rd}, 2026).}
~~~

## Build and handoff

Run the repository build, using its actual main file and XeLaTeX or LuaLaTeX if needed. Inspect every rendered page and the build log for overfull columns, unresolved citations, unembedded fonts, missing glyphs, damaged conjuncts, mismatched callouts, and page-limit compliance. Use "pdffonts" and "pdftotext" as supporting checks. Compare visually before treating two-column extraction artifacts as layout defects. Verify that figures and tables are readable at normal size and that links lead to the specified package and video.

Return the revised LaTeX, BibTeX, editable figure sources, and compiled PDF in their project locations, plus a short author-only change record with exact files, checks run, claims updated and their evidence, and dependencies still pending. If "FINAL_CONTEXT.md" is unavailable or an experiment did not run, finish the supported revision using verified evidence and identify the exact missing dependency in the change record.
