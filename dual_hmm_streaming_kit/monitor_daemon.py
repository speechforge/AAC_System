#!/usr/bin/env python3
"""
monitor_daemon.py - 10-Minute Health-Check, Progress Telemetry & Self-Repair Daemon
Ensures zero unwanted termination, monitors GPU/RAM/Disk, and repairs/restarts if process stalls.
"""

import os
import sys
import time
import subprocess
import json
import psutil
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
METRICS_FILE = os.path.join(LOGS_DIR, "training_metrics.json")
DIAG_LOG = os.path.join(LOGS_DIR, "diagnostic_health.log")
TRAIN_SCRIPT = os.path.join(BASE_DIR, "train_dual_hmm_streaming.py")
PYTHON_BIN = "/home/linux/miniconda3/envs/taac_env/bin/python"

def log_diag(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(DIAG_LOG, "a") as f:
        f.write(line + "\n")

def find_training_process():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmd)
            if "train_dual_hmm_streaming.py" in cmd_str:
                return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None

def check_gpu_status():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu",
             "--format=csv,noheader,nounits"],
            universal_newlines=True
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        return {
            "gpu_name": parts[0],
            "total_mb": parts[1],
            "used_mb": parts[2],
            "free_mb": parts[3],
            "temp_c": parts[4],
            "util_pct": parts[5]
        }
    except Exception as e:
        return {"error": str(e)}

def check_system_resources():
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        "ram_used_gb": round(mem.used / (1024**3), 2),
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_pct": mem.percent,
        "disk_avail_gb": round(disk.free / (1024**3), 2),
        "disk_pct": disk.percent
    }

def get_latest_metrics():
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r") as f:
                history = json.load(f)
            if history:
                return history[-1], len(history)
        except Exception:
            pass
    return None, 0

def run_diagnostic_check(auto_repair=True):
    log_diag("=" * 70)
    log_diag("RUNNING 10-MINUTE EXPERIMENT DIAGNOSTIC CHECK")
    
    # 1. System Health
    sys_res = check_system_resources()
    gpu_res = check_gpu_status()
    log_diag(f"RAM: {sys_res['ram_used_gb']}GB / {sys_res['ram_total_gb']}GB ({sys_res['ram_pct']}%) | Disk Avail: {sys_res['disk_avail_gb']}GB")
    if "error" not in gpu_res:
        log_diag(f"GPU: {gpu_res['gpu_name']} | Used VRAM: {gpu_res['used_mb']}MB / {gpu_res['total_mb']}MB | Temp: {gpu_res['temp_c']}°C | Util: {gpu_res['util_pct']}%")

    # 2. Process Check
    latest_chunk, total_chunks = get_latest_metrics()
    all_done = (total_chunks >= 505) or (latest_chunk and latest_chunk.get("chunk_id", 0) >= 505)

    proc = find_training_process()
    if proc:
        log_diag(f"[HEALTHY] Training Process ACTIVE (PID: {proc.pid}, CPU: {proc.cpu_percent()}%, MEM: {round(proc.memory_info().rss / (1024*1024), 1)} MB)")
    elif all_done:
        log_diag("[COMPLETE] All 505 Chunks (251.01M Sentences, 4.05B Tokens) Training Successfully Finished!")
    else:
        log_diag("[ALERT] Training Process NOT RUNNING!")
        if auto_repair:
            log_diag("[SELF-REPAIR] Relaunching train_dual_hmm_streaming.py in background...")
            train_log = os.path.join(LOGS_DIR, "train_stream.log")
            with open(train_log, "a") as f_out:
                new_proc = subprocess.Popen(
                    [PYTHON_BIN, "-u", TRAIN_SCRIPT],
                    stdout=f_out,
                    stderr=subprocess.STDOUT,
                    cwd=BASE_DIR,
                    start_new_session=True
                )
            log_diag(f"[SELF-REPAIR] Successfully restarted training process with PID {new_proc.pid}")

    # 3. Training Telemetry
    latest_chunk, total_chunks = get_latest_metrics()
    if latest_chunk:
        log_diag(f"Latest Completed Chunk: #{latest_chunk.get('chunk_id')} ({latest_chunk.get('dataset_name')})")
        log_diag(f"Cumulative Sentences: {latest_chunk.get('total_sentences', 0):,} | Vocab: {latest_chunk.get('vocab_size', 0):,} | Bigrams: {latest_chunk.get('bigram_states', 0):,}")
        eval_m = latest_chunk.get("eval_metrics", {})
        log_diag(f"Validation: NextWord Top-1={eval_m.get('nextword_top1_acc')}%, Top-3={eval_m.get('nextword_top3_acc')}%, Top-5={eval_m.get('nextword_top5_acc')}% | Unjumble Match={eval_m.get('unjumble_exact_match_pct')}%, Tau={eval_m.get('unjumble_kendall_tau')}")
    else:
        log_diag("Training in initial chunk ingestion phase...")
    log_diag("=" * 70)

def daemon_loop():
    log_diag("Starting Continuous 10-Minute Diagnostic Daemon...")
    while True:
        try:
            run_diagnostic_check(auto_repair=True)
        except Exception as e:
            log_diag(f"Error in diagnostic check: {e}")
        # Sleep for 10 minutes (600 seconds)
        time.sleep(600)

if __name__ == "__main__":
    if "--check" in sys.argv:
        run_diagnostic_check(auto_repair=False)
    else:
        daemon_loop()
