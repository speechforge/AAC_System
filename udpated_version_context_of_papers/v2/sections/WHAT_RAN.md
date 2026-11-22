## 4. What ran (and what did not)

| Item | Status | Where / artifact |
|---|---|---|
| A. reproduce and audit the archived run | **done** (CPU) | `results/audit/A1..A8`, section 5 |
| B. repairs (client, protocol, gate, templates, realiser prefix, scorer v2) | **done**, frozen | `patches/`, `config/freeze_manifest.json`, section 6 |
| Dev split, gate probes, tuning | **done** | `fixtures/dev/`, `results/tables/*_dev.csv` (tuned: not evidence) |
| Pre-registered holdout (120 items = 30 groups x 4 languages), overlap checks | **done**, DRAFT labels | `fixtures/holdout/`, `results/checks/fixture_checks_holdout.json` |
| Real-browser payload capture, original and revised client | **done** (dev 84, legacy 184, holdout 120 per client; Hinglish not clickable, uses archived API payloads) | `results/payloads/` |
| Systems on the holdout: archived deployed, matched one-pass, ungated cascade (first and last), repaired template, repaired hybrid, gate-only change, interface cross | **done** | `results/streams/`, `results/scored/holdout_scored.csv`, `results/tables/` |
| Three prespecified seeds (11, 23, 47), English sampling path | **done** (Indic path is greedy: seeds not applicable) | streams |
| Regression of the original 175 on the repaired system | **done** (one seed, 11) | `results/tables/*_legacy.csv` |
| Live HTTP path vs offline replay | **done** (PC server), 180/180 identical | `results/audit/B_replay_vs_live_holdout_pc.json` |
| User-selectable intent control | **implemented and run on the 8 ambiguous items** (16 requests) | `results/e2e/ambiguity_user_choice_pc.jsonl` |
| Determinism of retry; cross-hardware reproducibility | **done** | `B_determinism_check.json`, `B_crosshardware_repro.json` |
| Blind native-rater packet | **built, ratings PENDING** | `reviewer_packet/` |
| Native-speaker check of the gold annotation | **PENDING** | `fixtures/*/native_gold_check_<lang>.csv` |
| Browser-to-speech path on the GTX 1650 (32 UI runs) | **done**; real speech **not** verifiable (no IndicF5 weights, 0 browser voices in headless Chrome) | `results/audit/B_speech_path.json` |
| Demo captures (success, rejection + fallback, clarification, server unreachable) | **done** | `reviewer_packet/demo_captures/*.png` |
| Clean-environment install test | **done on CPU** with the shared Hugging Face cache (see limits) | `results/audit/D_clean_env_test.json` |
| Hosted demo and screencast links | **none exist / not accessible** | section 10 |
| Two-pass GPU work split | all holdout, legacy and one-pass GPU jobs ran on the PC's TITAN Xp; the PC's first freeze check failed only because the client file had not been synced yet and passed after syncing (all frozen files byte-identical); the legacy explicit-gold stream was **not run separately**: on all 184 legacy and 120 holdout selections the repaired client's payload and the explicit-gold payload normalise to **identical contexts**, so the gold rows of the repaired system are the same stream (`legacy_derived_g1gold_from_g1rev`; on the holdout both were run and are identical). | `logs/EXPERIMENT_LOG.md`, `logs/remote/` |
