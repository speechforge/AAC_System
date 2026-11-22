#!/bin/bash
# Starts each language's native-text training as soon as the GPU has >= 4500 MiB free AND its prepared data exists (so up to two jobs overlap if memory allows).
cd "$(dirname "$0")"; PY=/home/linux/miniconda3/envs/taac_env/bin/python
free() { nvidia-smi --query-gpu=memory.total,memory.used --format=csv,noheader,nounits | awk -F, '{print $1-$2}'; }
for l in mr gu; do
  until [ -s data_native/${l}_native_info.json ] && [ "$(free)" -ge 4500 ]; do sleep 20; done
  echo "$(date +%T) starting $l (free $(free) MiB)" >> results/native_launcher.log
  nohup $PY exp_native_lm.py $l > results/native_$l.log 2>&1 &
  sleep 120
done
wait
