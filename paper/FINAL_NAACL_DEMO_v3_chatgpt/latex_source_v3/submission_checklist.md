# Submission checklist: ACL family (ACL, EMNLP, NAACL, EACL, AACL, ARR)

_Kit: acl-style-files pinned commit; read the current call. Pages: {'content': 'long 8 / short 4 (review); +1 camera-ready', 'refs': 'unlimited', 'appendix': 'allowed, outside the limit, same anonymity rules'}. Automatic checks are evidence, not proof; confirm against the current call._

Required: limitations, ethics (when relevant), responsible NLP checklist (submission system)

- [x] **verified** (blocking): All claims in the abstract and introduction are supported by evidence (claim-evidence map has no open row) _(no open claim rows)_
- [ ] **NOT MET** (blocking): References complete and verified; all citations resolve _(ERROR: 'francis2024connectone' is not verified (status: single-source) (02_related.tex:9))_
- [ ] **NOT MET** (blocking): A Limitations section exists and states honest scope _(paper/sections/07_limitations.tex missing)_
- [x] **verified**: Every figure and table has a self-contained caption _(0 captions for 0 floats)_
- [ ] **NOT MET**: Error bars, confidence intervals, or tests are reported, with the number of runs and how the uncertainty is computed _(the files to check are missing or empty)_
- [ ] **NOT MET**: Hyperparameters and their selection are documented _(the files to check are missing or empty)_
- [ ] **NOT MET**: Compute resources are stated (hardware, time per run, total) _(the files to check are missing or empty)_
- [ ] **NOT MET** (blocking): Licenses of used and released assets are stated _(license_statement.tex missing; run credits_license.py)_
- [ ] **NOT MET**: Ethics and broader-impact considerations are addressed (or a one-sentence justification) _(paper/sections/08_ethics.tex missing)_
- [ ] **not applicable**: Human-subjects approval or exemption and consent are documented _(declared not applicable (human_subjects.involved is false in project_meta.json))_
- [ ] **author to confirm**: Baselines are appropriate, recent, and fairly tuned _(author must confirm)_
- [ ] **author to confirm**: The PDF compiles without errors and all figures render _(no TeX here; compile on Overleaf and confirm)_
- [ ] **NOT MET** (blocking): Review version is anonymous (no names, acknowledgments, grant numbers, identifying links) _(project_meta.json anonymous and the \camerareadytrue switch disagree)_
- [ ] **author to confirm**: The correct template (venue and year) is used; margins and font sizes are untouched _(author must confirm)_
- [ ] **author to confirm**: Main content is within the page limit for the current call _(author must confirm)_
- [ ] **author to confirm**: Supplementary material is organised and self-consistent with the paper _(author must confirm)_
- [ ] **NOT MET** (blocking): Limitations section present (mandatory; does not count toward the page limit) _(paper/sections/07_limitations.tex missing)_
- [ ] **NOT MET**: Ethical considerations addressed when relevant _(paper/sections/08_ethics.tex missing)_
- [ ] **NOT MET**: Responsible NLP: bias, fairness, dual-use, and privacy considered _(the files to check are missing or empty)_
- [ ] **author to confirm**: If applicable: language diversity addressed, non-English languages included, translation quality verified _(author must confirm)_
- [ ] **NOT MET**: If applicable: annotator details, agreement metrics, and compensation documented _(the files to check are missing or empty)_
- [ ] **author to confirm**: Disclosure of AI writing assistance follows the current policy _(author must confirm)_
- [ ] **author to confirm**: Responsible NLP checklist completed in the submission system (not in the PDF) _(author must confirm)_
