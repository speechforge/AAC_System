#!/usr/bin/env bash
# Offload GPU jobs to PC_Nisarg (TITAN Xp 12 GB).  Usage: SSHPASS='<password>' ./remote_sync_and_run.sh sync|env|run "<command run in v2/src on the PC>"|pull
# The same absolute tree (/home/linux/Documents/aac_system_november_11/AAC_System_merged) is recreated on the PC so every path in common.py resolves unchanged.
# Provenance rule: files produced remotely carry the tag 'remote' in their file name; hardware differs from the local GTX 1650, so results are never mixed inside one paired comparison without saying so.
set -euo pipefail
HOST=linux@10.100.59.86
ROOT=/home/linux/Documents/aac_system_november_11/AAC_System_merged
SSH="sshpass -e ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o ConnectTimeout=10 $HOST"
RSYNC="sshpass -e rsync -az --info=stats1 -e 'ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no'"
case "${1:-}" in
  sync)
    $SSH "mkdir -p $ROOT/paper/CLAUDE_WRITTEN/naacl2027_demo $ROOT/udpated_version_context_of_papers/v2 $ROOT/indic-generative-aac"
    eval $RSYNC --exclude='__pycache__' $ROOT/indic-generative-aac/backend $HOST:$ROOT/indic-generative-aac/
    eval $RSYNC $ROOT/english_AAC_Dataset $ROOT/hindi_AAC_Dataset $HOST:$ROOT/ || true
    eval $RSYNC --exclude='__pycache__' --exclude='results/streams' --exclude='results/scored' $ROOT/udpated_version_context_of_papers/v2/ $HOST:$ROOT/udpated_version_context_of_papers/v2/
    eval $RSYNC --exclude='__pycache__' --exclude='results' --exclude='bib_raw' --exclude='logs' $ROOT/paper/CLAUDE_WRITTEN/naacl2027_demo/eval $HOST:$ROOT/paper/CLAUDE_WRITTEN/naacl2027_demo/
    eval $RSYNC ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B-Instruct $HOST:/home/linux/.cache/huggingface/hub/
    ;;
  env)  $SSH "python3 --version; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; python3 -c 'import torch,transformers;print(torch.__version__,transformers.__version__,torch.cuda.is_available())'" ;;
  run)  $SSH "cd $ROOT/udpated_version_context_of_papers/v2/src && $2" ;;
  pull) eval $RSYNC --include='*remote*' --include='*/' --exclude='*' $HOST:$ROOT/udpated_version_context_of_papers/v2/results/ $ROOT/udpated_version_context_of_papers/v2/results/ ;;
  *) echo "usage: sync|env|run|pull"; exit 1;;
esac
