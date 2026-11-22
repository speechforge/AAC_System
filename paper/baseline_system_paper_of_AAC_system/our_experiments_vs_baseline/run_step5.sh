cd "$(dirname "$0")"
while pgrep -f "python exp_step3.py" >/dev/null; do sleep 15; done
for l in mr gu hi en; do PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /home/linux/miniconda3/envs/taac_env/bin/python exp_step5.py $l > results/step5_$l.log 2>&1; done
