# FINAL_CONTEXT: Indic AAC Studio, evaluation and repair (v2 experiments)

Written 2026-11-13 (IST) after the experiments of `AAC_01_Experiments_and_FINAL_CONTEXT.md`.

Written for the paper author. Tables are rendered by `src/render_tables.py` from `results/tables/*.csv` and `results/audit/*`; no table number is typed by hand. Narrative numbers were checked against the same files.

**Labels used throughout.** *Archived* = the system and outputs of the earlier evaluation (commit `fe4e185`, scorer v1). *Revised* = the repaired working tree after the freeze. *Exploratory* = Hinglish and every post-hoc probe. **All holdout fixtures are DRAFT (native-speaker checks pending). Holdout scores below are preliminary and must stay out of the paper until two native speakers per language have confirmed the gold annotation (section 10, gap 1).** 175/175 is an engineering target, not a result; every count below is measured.

## 1. Source revision, environment, dirty state

| Item | Value |
|---|---|
| Repository | `AAC_System_merged`, branch `merged`, HEAD `fe4e185763a181674534656dbf95e30709cf83ff` |
| Dirty state at write time | modified tracked: `backend/app.py`, `llm.py`, `semantic.py`, `tts.py`, `frontend/index.html`; new untracked backend files `aac_lexicon.py`, `templates.py`, `pipeline.py`, `board_concepts.json`; untracked docs `CONTEXT.md`, `NAACL_PAPER_BUNDLE.md`, `paper/`, `udpated_version_context_of_papers/` |
| Patch of the repair | `patches/revised_system_tracked_files.patch` (+ `patches/new_files/`); archived originals in `archived_system/` (hashes `config/archived_system_sha256.txt`) |
| Freeze | `config/freeze_manifest.json` (SHA-256 of every rule, prompt, decoding, scorer and runner file; written 2026-11-13 before the holdout existed, re-written once for Addendum 1 with identical system-file hashes; first manifest `config/freeze_manifest_v1_superseded.json`). `python src/freeze.py --check` returned FREEZE OK locally and on the PC. |
| Model | `Qwen/Qwen2.5-0.5B-Instruct`, revision `7ae557604adf67be50417f59c2c2f167def9a775`, `model.safetensors` SHA-256 prefix `fdf756fa7fcb...` (identical on both machines), fp16 on GPU |
| Local machine | NVIDIA GTX 1650 4 GB (driver 595.99.02), Python 3.13.13, torch 2.11.0+cu130, transformers 5.14.1 |
| PC (alias PC_Nisarg, 10.100.59.86) | NVIDIA TITAN Xp 12 GB (driver 580.178.04), 16 cores, Python 3.12.3, venv `~/aac_v2_env`: torch 2.11.0+cu126 (CUDA 13 wheels do not support Pascal), transformers 5.14.1 |
| SSH | Port 22 was refused until sshd was installed on the PC; the new host key was confirmed by the user, the stale `known_hosts` entry was replaced, then GPU jobs moved to the PC (the user asked to spare the local 4 GB GPU). |

**Where each part ran.** Phase A: local CPU. Browser captures and speech/latency check: local (Chrome; the speech check uses the local GTX 1650 server because that is the demo configuration). Development streams and determinism check: local GTX 1650. Holdout streams, legacy regression streams and one-pass comparator: **PC TITAN Xp** (file names contain `remote`). Local partial holdout rows (GTX 1650) are kept in `results/streams/local_gtx1650/` and compared with the PC rows in section 7.4. Live-path end-to-end run: PC server.

## 2. Paths and conventions

```
udpated_version_context_of_papers/v2/
  FINAL_CONTEXT.md            this file (template: FINAL_CONTEXT.template.md)
  run_all.sh                  evaluation + analysis commands (section 3)
  src/                        all scripts (audit_*, build_fixtures, browser_capture, run_streams, run_onepass, replay, analyze_v2, score_v2, ...)
  config/                     freeze manifests, archived hashes
  fixtures/{legacy,dev,holdout}/scenarios.jsonl   fixture manifests (+ PREREGISTRATION.md, native_gold_check_<lang>.csv, README_DRAFT.md, build_log*.json)
  results/audit/              Phase A evidence (A1..A8) and Phase B/D checks (B_*, D_*)
  results/payloads/           requests captured from the REAL browser client (original and revised)
  results/streams/            candidate streams (trace files); cache_*.jsonl = prompt-level generation cache
  results/scored/             one row per scenario, language, input mode, system, seed, stage (scorer v2)
  results/tables/             T1..T7 paired tables;  results/figures/  figure + source CSV + script copy
  results/checks/             fixture and integrity checks;  results/e2e/ live-path runs
  reviewer_packet/            blind native-rater packet, demo captures
  logs/EXPERIMENT_LOG.md      time-stamped audit trail;  remote/ PC job scripts
```
Scenario schema: `id, group, family, lang, seq, labels, concept_ids, content_concepts, customs, more, gold_act, gold_neg, expected_outcome, template_covered, intended_en, status`. One **group** is one underlying message rendered in four languages; bootstrap resamples groups.

## 3. Exact commands

`run_all.sh` lists the full sequence. Evaluation (GPU, one command per job type, all keyed and resumable): `python src/run_streams.py --split holdout --jobs G0:orig G0:gold G1:rev G1:gold G1:cross --seeds 11 23 47`, `python src/run_onepass.py --split holdout --modes rev gold --seeds 11 23 47`, `python src/run_streams.py --split legacy --jobs G1:rev G1:gold --seeds 11`. Analysis (CPU): `python src/analyze_v2.py --split holdout`, `python src/check_all.py --split holdout --run-commands`, `python src/make_figure.py --split holdout`. Remote execution: `remote/remote_sync_and_run.sh`, `remote/remote_jobs.sh`.

<!--SECTION:WHAT_RAN-->

<!--SECTION:PHASE_A-->

<!--SECTION:PHASE_B-->

<!--SECTION:PHASE_C-->

<!--SECTION:PHASE_D-->

<!--SECTION:NEGATIVE-->

<!--SECTION:GAPS-->
