cd "$(dirname "$0")"
while pgrep -f "python exp_step5.py" >/dev/null; do sleep 15; done
for K in 10 20; do for l in mr gu hi; do PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True /home/linux/miniconda3/envs/taac_env/bin/python exp_step8_k.py $l $K > results/step8_${l}_K$K.log 2>&1; done; done
