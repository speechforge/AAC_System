#!/usr/bin/env bash
# Evaluation command and analysis command for the v2 experiments (Indic AAC Studio).  Run from this directory.
# Hardware used: NVIDIA GTX 1650 4 GB, Python 3.13.13, torch 2.11.0+cu130, transformers 5.14.1 (see config/ and FINAL_CONTEXT.md).
# Steps marked GPU load one Qwen2.5-0.5B-Instruct copy (do not run two GPU steps at once on a 4 GB card unless you shard as shown).
set -euo pipefail
cd "$(dirname "$0")/src"

# ---- Phase A (CPU): reproduce and audit the archived run
python3 audit_archived.py && python3 audit_scorer.py && python3 audit_classify.py && python3 predict_audit.py

# ---- Phase B: fixtures, scorer, gate probes (CPU)
python3 build_fixtures.py legacy && python3 build_fixtures.py dev
python3 make_gate_probes.py && python3 eval_gate_probes.py && python3 rescore_archived.py
python3 check_fixtures.py dev && python3 check_fixtures.py legacy
python3 browser_capture.py --client original --split dev   && python3 browser_capture.py --client revised --split dev      # real browser, no GPU
python3 browser_capture.py --client original --split legacy && python3 browser_capture.py --client revised --split legacy
python3 run_streams.py --split dev --jobs G1:gold --seeds 11                                                                  # GPU
python3 determinism_check.py 40                                                                                                # GPU
python3 analyze_v2.py --split dev                                                                                              # tuning on dev only
# ---- FREEZE: after tuning, before the holdout exists
test -f ../config/freeze_manifest.json || python3 freeze.py
python3 build_fixtures.py holdout && python3 check_fixtures.py holdout
python3 browser_capture.py --client original --split holdout && python3 browser_capture.py --client revised --split holdout

# ---- Phase C: streams (GPU).  What was actually run: all holdout / legacy / one-pass GPU jobs on the PC (TITAN Xp 12 GB, venv with torch 2.11.0+cu126, transformers 5.14.1):
#      remote/remote_sync_and_run.sh sync ; remote/remote_jobs.sh   (five workers; file names carry the tag 'remote')
#      equivalent local command (GTX 1650, about 3 h):
python3 run_streams.py --split holdout --jobs G0:orig G0:gold G1:rev G1:gold G1:cross --seeds 11 23 47
python3 run_streams.py --split legacy --jobs G1:rev --seeds 11          # explicit-gold rows of the repaired system are the same stream (identical contexts; see FINAL_CONTEXT 4)
python3 run_onepass.py --split holdout --modes rev gold --seeds 11 23 47
python3 run_onepass.py --split legacy --modes rev gold --seeds 11
# live path: start `python ../../indic-generative-aac/backend/app.py` (PC: PORT=8011), then
AAC_URL=http://localhost:8000 E2E_TAG=_pc python3 e2e_http.py run --split holdout && AAC_URL=x E2E_TAG=_pc python3 e2e_http.py compare --split holdout
python3 crosshw_compare.py                                                                                                    # needs local_gtx1650/ partial rows

# ---- analysis command (CPU)
for S in holdout legacy; do python3 analyze_v2.py --split $S; python3 check_all.py --split $S --run-commands; done
python3 latency_summary.py && python3 make_figure.py --split holdout
python3 build_reviewer_packet.py --split holdout --mode rev && python3 build_gold_check_sheets.py && python3 analyze_ratings.py
python3 speech_and_demo_check.py --repeats 2                                                                                  # live local server + Chrome (GTX 1650)
python3 render_tables.py                                                                                                       # writes ../FINAL_CONTEXT.md from FINAL_CONTEXT.template.md and sections/
