#!/bin/bash
# reruns the cross-validation for hi and gu ONE AT A TIME (shared GPU). (v2: no pgrep wait - the old wait loop matched its own shell wrappers and never started.)
cd "$(dirname "$0")"; PY=/home/linux/miniconda3/envs/taac_env/bin/python
for l in hi gu; do $PY exp_cv_lm.py $l > results/cv_lm_$l.log 2>&1; done
