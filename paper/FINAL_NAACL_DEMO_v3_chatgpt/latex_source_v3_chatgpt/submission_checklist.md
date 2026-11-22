# Submission checklist: Generic / preprint

_Kit: n/a. Pages: {'content': 'n/a'}. Automatic checks are evidence, not proof; confirm against the current call._

Required: limitations

- [x] **verified** (blocking): All claims in the abstract and introduction are supported by evidence (claim-evidence map has no open row) _(no open claim rows)_
- [ ] **NOT MET** (blocking): References complete and verified; all citations resolve _(ERROR: 'karmakar-sinha-2024-aiding' is not verified (status: single-source) (02_related.tex:4))_
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
- [x] **verified** (blocking): Review version is anonymous (no names, acknowledgments, grant numbers, identifying links) _(anonymous mode and review build)_
- [ ] **author to confirm**: The correct template (venue and year) is used; margins and font sizes are untouched _(author must confirm)_
- [ ] **author to confirm**: Main content is within the page limit for the current call _(author must confirm)_
- [ ] **author to confirm**: Supplementary material is organised and self-consistent with the paper _(author must confirm)_
