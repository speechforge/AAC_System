#!/usr/bin/env bash
# Runs ON the PC (TITAN Xp 12 GB).  Five parallel workers, then the legacy regression and one-pass jobs.  Output files carry the tag 'remote'.
cd /home/linux/Documents/aac_system_november_11/AAC_System_merged/udpated_version_context_of_papers/v2/src
. ~/aac_v2_env/venv/bin/activate
export HF_HUB_OFFLINE=1
L=../logs/remote; mkdir -p $L
python freeze.py --check > $L/freeze_check_remote.txt 2>&1
( CACHE_TAG=r1 python run_streams.py --split holdout --jobs G0:orig --seeds 11 23 47 --tag remote_g0orig > $L/w1.log 2>&1 && CACHE_TAG=r6 python run_streams.py --split legacy --jobs G1:rev --seeds 11 --tag remote_g1rev > $L/w6.log 2>&1 ) &
( CACHE_TAG=r2 python run_streams.py --split holdout --jobs G0:gold --seeds 11 23 47 --tag remote_g0gold > $L/w2.log 2>&1 && CACHE_TAG=r7 python run_streams.py --split legacy --jobs G1:gold --seeds 11 --tag remote_g1gold > $L/w7.log 2>&1 ) &
( CACHE_TAG=r3 python run_streams.py --split holdout --jobs G1:rev --seeds 11 23 47 --tag remote_g1rev > $L/w3.log 2>&1 && CACHE_TAG=r8 python run_onepass.py --split legacy --modes rev gold --seeds 11 > $L/w8.log 2>&1 ) &
( CACHE_TAG=r4 python run_streams.py --split holdout --jobs G1:gold G1:cross --seeds 11 23 47 --tag remote_g1gold > $L/w4.log 2>&1 ) &
( CACHE_TAG=r5 python run_onepass.py --split holdout --modes rev gold --seeds 11 23 47 > $L/w5.log 2>&1 ) &
wait
echo ALL_REMOTE_JOBS_DONE > $L/DONE
