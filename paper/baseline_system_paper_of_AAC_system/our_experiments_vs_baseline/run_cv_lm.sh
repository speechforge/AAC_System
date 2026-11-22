#!/bin/bash
cd "$(dirname "$0")"
PY=/home/linux/miniconda3/envs/taac_env/bin/python
( $PY exp_cv_lm.py en > results/cv_lm_en.log 2>&1 ; $PY exp_cv_lm.py mr > results/cv_lm_mr.log 2>&1 ) &
( $PY exp_cv_lm.py hi > results/cv_lm_hi.log 2>&1 ; $PY exp_cv_lm.py gu > results/cv_lm_gu.log 2>&1 ) &
wait
