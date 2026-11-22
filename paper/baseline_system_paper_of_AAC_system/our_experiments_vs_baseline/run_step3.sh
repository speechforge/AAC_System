cd "$(dirname "$0")"
for l in mr gu; do PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /home/linux/miniconda3/envs/taac_env/bin/python exp_step3.py $l > results/step3_$l.log 2>&1; done
