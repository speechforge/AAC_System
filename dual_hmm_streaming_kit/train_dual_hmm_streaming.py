#!/usr/bin/env python3
"""
train_dual_hmm_streaming.py
Continuous Streaming Training Pipeline for Dual HMM Suite:
- HMM-1: Next-Word Recommendation System
- HMM-2: Syntactic Un-jumbling / Permutation Decoder

Streams datasets chunk-by-chunk in ~1GB / 500K sentence slices:
- Chunk 1..3: agentlans/high-quality-english-sentences (~1.53M sentences across 3 chunks)
- Chunk 4:    vpermilp/tatoeba-sentences (English subset, ~500K sentences)
- Chunk 5:    sentence-transformers/parallel-sentences-tatoeba (English, ~500K sentences)
- Chunk 6..N: monology/pile-uncopyrighted (The Pile streaming slices, ~500K sentences each)

Memory Optimized: Shares underlying bigram/trigram transition stores between
HMM-1 and HMM-2, eliminating 12 GB of duplicate RAM overhead and preventing OOM.
"""

import os
import sys
import time
import json
import pickle
import re
import math
import gc
from datetime import datetime
from collections import Counter
from tqdm import tqdm

import torch
from datasets import load_dataset

from models_def import AACNextWordHMM, AACUnjumbleHMM
from test_suite import get_next_word_test_cases, get_unjumble_test_cases

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
METRICS_FILE = os.path.join(LOGS_DIR, "training_metrics.json")
LIVE_STATUS_FILE = os.path.join(LOGS_DIR, "live_status.json")
BACKEND_HMM_PATH = "/home/linux/Documents/AACsystem/AAC_System-jaydeep/indic-generative-aac/backend/hmm_model.pkl"

WORD_RE = re.compile(r"[a-z']+")

def tokenize(text):
    """Fast regex tokenization."""
    if not text or not isinstance(text, str):
        return []
    words = WORD_RE.findall(text.lower())
    if 2 <= len(words) <= 45:
        return words
    return []

def evaluate_models(next_hmm, unjumble_hmm):
    """Evaluate Next-Word Prediction and Syntactic Unjumbling on clinical test cases."""
    # 1. Next Word Evaluation
    nw_cases = get_next_word_test_cases()
    top1_correct = 0
    top3_correct = 0
    top5_correct = 0
    top10_correct = 0
    total_nw = len(nw_cases)

    for prefix, target in nw_cases:
        preds = next_hmm.predict_next(prefix, top_k=10)
        words_pred = [p["word"] for p in preds]
        if words_pred:
            if target == words_pred[0]:
                top1_correct += 1
            if target in words_pred[:3]:
                top3_correct += 1
            if target in words_pred[:5]:
                top5_correct += 1
            if target in words_pred[:10]:
                top10_correct += 1

    top1_acc = round((top1_correct / total_nw) * 100, 2) if total_nw else 0.0
    top3_acc = round((top3_correct / total_nw) * 100, 2) if total_nw else 0.0
    top5_acc = round((top5_correct / total_nw) * 100, 2) if total_nw else 0.0
    top10_acc = round((top10_correct / total_nw) * 100, 2) if total_nw else 0.0

    # 2. Unjumble Evaluation
    uj_cases = get_unjumble_test_cases()
    exact_matches = 0
    kendall_tau_sum = 0.0
    total_uj = len(uj_cases)

    for jumbled, canonical in uj_cases:
        unjumbled, _ = unjumble_hmm.unjumble(jumbled)
        if unjumbled == canonical:
            exact_matches += 1

        # Calculate Kendall Tau rank correlation
        try:
            can_pos = {w: i for i, w in enumerate(canonical)}
            ranks = [can_pos.get(w, i) for i, w in enumerate(unjumbled)]
            concordant = 0
            discordant = 0
            m = len(ranks)
            for i in range(m):
                for j in range(i + 1, m):
                    if ranks[i] < ranks[j]:
                        concordant += 1
                    elif ranks[i] > ranks[j]:
                        discordant += 1
            denom = (m * (m - 1)) / 2 if m > 1 else 1
            tau = (concordant - discordant) / denom
            kendall_tau_sum += max(0.0, tau)
        except Exception:
            pass

    uj_exact_pct = round((exact_matches / total_uj) * 100, 2) if total_uj else 0.0
    avg_kendall_tau = round((kendall_tau_sum / total_uj), 3) if total_uj else 0.0

    return {
        "nextword_top1_acc": top1_acc,
        "nextword_top3_acc": top3_acc,
        "nextword_top5_acc": top5_acc,
        "nextword_top10_acc": top10_acc,
        "unjumble_exact_match_pct": uj_exact_pct,
        "unjumble_kendall_tau": avg_kendall_tau
    }

def save_master_backend_hmm(next_hmm, unjumble_hmm, out_path=BACKEND_HMM_PATH):
    """
    Save master hmm_model.pkl compatible with existing FastAPI backend,
    injecting both next-word prediction tables and the unjumble model.
    Omits hapax 4-grams to keep backend serialization fast (<1s) and memory footprint lean.
    """
    data = {
        'bigrams': unjumble_hmm.word_bigrams,
        'trigrams': unjumble_hmm.word_trigrams,
        'start_priors': unjumble_hmm.start_priors,
        'end_priors': unjumble_hmm.end_priors,
        'unigrams': unjumble_hmm.word_unigrams,
        'sentence_count': unjumble_hmm.sentence_count,
        'vocab_size': len(unjumble_hmm.word_unigrams),
        'unjumble_model': unjumble_hmm
    }
    tmp_path = out_path + ".tmp"
    with open(tmp_path, 'wb') as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp_path, out_path)
    print(f"[*] Updated FastAPI backend master HMM model at: {out_path}")

def update_live_status(chunk_id, dataset_name, chunk_sents, total_sents, total_toks,
                       vocab_sz, bi_sz, tri_sz, four_sz, eval_m, elapsed, pct, status="TRAINING"):
    # Build ASCII progress bar
    bar_len = 30
    filled = int(round(bar_len * (pct / 100.0)))
    bar = "█" * filled + "░" * (bar_len - filled)
    tqdm_str = f"[{bar}] {pct:5.1f}% | {chunk_sents:,} sents | {total_sents:,} total"

    live_data = {
        "status": status,
        "last_heartbeat": datetime.now().isoformat(),
        "current_chunk_id": chunk_id,
        "current_dataset": dataset_name,
        "chunk_sentences": chunk_sents,
        "cumulative_sentences": total_sents,
        "cumulative_tokens": total_toks,
        "estimated_gb_ingested": round(total_toks * 6.5 / (1024**3), 3),
        "vocab_size": vocab_sz,
        "bigram_states": bi_sz,
        "trigram_states": tri_sz,
        "fourgram_states": four_sz,
        "eval_metrics": eval_m,
        "tqdm_bar": tqdm_str,
        "elapsed_seconds": round(elapsed, 1)
    }
    try:
        with open(LIVE_STATUS_FILE, "w") as f:
            json.dump(live_data, f, indent=2)
    except Exception:
        pass

def stream_chunk_sentences(dataset_iterator, max_sentences=500000, skip_sentences=0):
    """
    Generator yielding batches of tokenized sentences.
    Batches buffered up to 25,000 sentences for high throughput.
    """
    count = 0
    skipped = 0
    batch = []

    for item in dataset_iterator:
        text = ""
        if isinstance(item, str):
            text = item
        elif isinstance(item, dict):
            if "translation" in item and isinstance(item["translation"], dict):
                text = item["translation"].get("en", "")
            elif "sentence" in item:
                text = item["sentence"]
            elif "text" in item:
                text = item["text"]
            elif "content" in item:
                text = item["content"]

        if text:
            lines = re.split(r"(?<=[.!?\n])\s+", text)
            for line in lines:
                tokens = tokenize(line)
                if tokens:
                    if skipped < skip_sentences:
                        skipped += 1
                        continue
                    batch.append(tokens)
                    count += 1
                    if len(batch) >= 25000:
                        yield batch
                        batch = []
                    if count >= max_sentences:
                        if batch:
                            yield batch
                        return
    if batch:
        yield batch

def run_streaming_pipeline():
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

    cuda_avail = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_avail else "CPU"
    print("=" * 80)
    print("DUAL HMM STREAMING TRAINING SYSTEM (Memory-Optimized Shared Storage)")
    print(f"Start Time: {datetime.now().isoformat()}")
    print(f"Hardware Acceleration: {device_name} ({'CUDA:0' if cuda_avail else 'Host CPU'})")
    print("=" * 80)

    # Initialize models
    unjumble_hmm = AACUnjumbleHMM()
    next_hmm = AACNextWordHMM()

    latest_next_path = os.path.join(MODELS_DIR, "hmm1_nextword_latest.pkl")
    latest_uj_path = os.path.join(MODELS_DIR, "hmm2_unjumble_latest.pkl")

    # Check completed chunks from history
    completed_chunks = set()
    metrics_history = []
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, "r") as f:
                metrics_history = json.load(f)
            for m in metrics_history:
                completed_chunks.add(m.get("chunk_id"))
            print(f"[*] Found {len(completed_chunks)} previously completed chunks: {sorted(completed_chunks)}")
        except Exception:
            metrics_history = []

    # Resume from checkpoint
    if os.path.exists(latest_uj_path):
        try:
            print("[*] Resuming models from latest checkpoints...")
            with open(latest_uj_path, "rb") as f:
                unjumble_hmm = pickle.load(f)
            print(f"[*] Loaded HMM-2 Unjumble Model: {unjumble_hmm.sentence_count:,} sentences, {len(unjumble_hmm.word_unigrams):,} vocab.")
        except Exception as e:
            print(f"[!] Warning: Could not resume unjumble checkpoint: {e}")

    # Bind next_hmm shared tables to eliminate duplicate memory
    next_hmm.bind_shared_store(unjumble_hmm)
    
    # Check if lean nextword checkpoint exists to recover high-order fourgrams
    if os.path.exists(latest_next_path):
        try:
            with open(latest_next_path, "rb") as f:
                saved_nw = pickle.load(f)
            if isinstance(saved_nw, dict) and "fourgrams" in saved_nw:
                next_hmm.fourgrams = saved_nw["fourgrams"]
                print(f"[*] Restored {len(next_hmm.fourgrams):,} 4-gram states from checkpoint.")
            elif isinstance(saved_nw, AACNextWordHMM):
                next_hmm.fourgrams = saved_nw.fourgrams
                print(f"[*] Restored {len(next_hmm.fourgrams):,} 4-gram states from HMM-1 checkpoint.")
        except Exception as e_nxt:
            print(f"[*] Note: High-order 4-grams initialized fresh ({e_nxt})")

    # Initial memory compaction
    gc.collect()
    print(f"[*] System State: Sentences: {unjumble_hmm.sentence_count:,} | Vocab: {len(unjumble_hmm.word_unigrams):,} | Bigrams: {len(unjumble_hmm.word_bigrams):,} | Trigrams: {len(unjumble_hmm.word_trigrams):,}")

    # Initial baseline eval
    eval_m = evaluate_models(next_hmm, unjumble_hmm)
    print(f"[*] Baseline Validation: NextWord Top-1={eval_m['nextword_top1_acc']}%, Top-3={eval_m['nextword_top3_acc']}% | Unjumble Match={eval_m['unjumble_exact_match_pct']}%, Tau={eval_m['unjumble_kendall_tau']}")

    # Build sequence of 1GB / 500K sentence slices
    # Chunk 1..3: agentlans high quality English (0 to 1.5M)
    # Chunk 4:    vpermilp/tatoeba-sentences (500K)
    # Chunk 5:    sentence-transformers/parallel-sentences-tatoeba (500K)
    # Chunk 6..505: The Pile continuous streaming (Slices 1 to 500, covering 250,000,000 sentences!)
    chunk_definitions = [
        {
            "chunk_id": 1,
            "dataset_name": "agentlans/high-quality-english-sentences",
            "desc": "High-Quality Clean English Sentences (Slice 1/3)",
            "config": None,
            "split": "train",
            "filter_eng": False,
            "skip": 0,
            "max_sentences": 500000
        },
        {
            "chunk_id": 2,
            "dataset_name": "agentlans/high-quality-english-sentences",
            "desc": "High-Quality Clean English Sentences (Slice 2/3)",
            "config": None,
            "split": "train",
            "filter_eng": False,
            "skip": 500000,
            "max_sentences": 500000
        },
        {
            "chunk_id": 3,
            "dataset_name": "agentlans/high-quality-english-sentences",
            "desc": "High-Quality Clean English Sentences (Slice 3/3)",
            "config": None,
            "split": "train",
            "filter_eng": False,
            "skip": 1000000,
            "max_sentences": 500000
        },
        {
            "chunk_id": 4,
            "dataset_name": "vpermilp/tatoeba-sentences",
            "desc": "Tatoeba Conversational English Sentences",
            "config": None,
            "split": "train",
            "filter_eng": True,
            "skip": 0,
            "max_sentences": 500000
        },
        {
            "chunk_id": 5,
            "dataset_name": "sentence-transformers/parallel-sentences-tatoeba",
            "desc": "Parallel Tatoeba English Corpus",
            "config": "en-hi",
            "split": "train",
            "filter_eng": False,
            "skip": 0,
            "max_sentences": 500000
        }
    ]

    # Continuous Pile chunks (Slices 1 to 500, each ~1GB / 500K sentences)
    for pile_slice in range(1, 501):
        chunk_definitions.append({
            "chunk_id": 5 + pile_slice,
            "dataset_name": "monology/pile-uncopyrighted",
            "desc": f"The Pile Diverse Large-Scale Corpus (Slice {pile_slice}/500)",
            "config": None,
            "split": "train",
            "filter_eng": False,
            "skip": (pile_slice - 1) * 30000,
            "max_sentences": 500000
        })

    for c_def in chunk_definitions:
        chunk_id = c_def["chunk_id"]
        ds_name = c_def["dataset_name"]
        desc = c_def["desc"]
        max_s = c_def["max_sentences"]
        skip_s = c_def.get("skip", 0)

        if chunk_id in completed_chunks:
            continue

        print("\n" + "=" * 80)
        print(f"STARTING CHUNK #{chunk_id}: {desc}")
        print(f"Source: {ds_name} | Target Slice: {max_s:,} sentences (skip: {skip_s:,})")
        print("=" * 80)

        t_chunk_start = time.time()
        processed_chunk_sentences = 0
        processed_chunk_tokens = 0

        update_live_status(
            chunk_id=chunk_id, dataset_name=ds_name, chunk_sents=0,
            total_sents=unjumble_hmm.sentence_count, total_toks=sum(unjumble_hmm.word_unigrams.values()),
            vocab_sz=len(unjumble_hmm.word_unigrams), bi_sz=len(unjumble_hmm.word_bigrams),
            tri_sz=len(unjumble_hmm.word_trigrams), four_sz=len(next_hmm.fourgrams),
            eval_m=eval_m, elapsed=0.0, pct=0.0, status="STREAMING_CHUNK"
        )

        try:
            if c_def["config"]:
                ds = load_dataset(ds_name, c_def["config"], split=c_def["split"], streaming=True)
            else:
                ds = load_dataset(ds_name, split=c_def["split"], streaming=True)

            if c_def.get("filter_eng"):
                ds_iter = (item for item in ds if item.get("lang") == "eng")
            else:
                ds_iter = iter(ds)

            pbar = tqdm(total=max_s, desc=f"Chunk {chunk_id} [{ds_name.split('/')[-1][:18]}]", unit="sents")

            for batch in stream_chunk_sentences(ds_iter, max_sentences=max_s, skip_sentences=skip_s):
                batch_tokens = 0
                for s in batch:
                    # Updates unigrams, bigrams, trigrams, start/end priors, and POS transitions
                    unjumble_hmm.update_sentence(s)
                    # Updates fourgrams only
                    next_hmm.update_fourgrams_only(s)
                    batch_tokens += len(s)

                processed_chunk_sentences += len(batch)
                processed_chunk_tokens += batch_tokens
                pbar.update(len(batch))
                pbar.set_postfix({
                    "vocab": f"{len(unjumble_hmm.word_unigrams):,}",
                    "bi": f"{len(unjumble_hmm.word_bigrams):,}",
                    "tri": f"{len(unjumble_hmm.word_trigrams):,}"
                })

                # Update live status every 25K sentences
                if processed_chunk_sentences % 25000 == 0:
                    pct = round((processed_chunk_sentences / max_s) * 100, 1)
                    elapsed = time.time() - t_chunk_start
                    total_tokens_now = sum(unjumble_hmm.word_unigrams.values())
                    update_live_status(
                        chunk_id=chunk_id, dataset_name=ds_name, chunk_sents=processed_chunk_sentences,
                        total_sents=unjumble_hmm.sentence_count, total_toks=total_tokens_now,
                        vocab_sz=len(unjumble_hmm.word_unigrams), bi_sz=len(unjumble_hmm.word_bigrams),
                        tri_sz=len(unjumble_hmm.word_trigrams), four_sz=len(next_hmm.fourgrams),
                        eval_m=eval_m, elapsed=elapsed, pct=pct, status="STREAMING_CHUNK"
                    )

                if processed_chunk_sentences >= max_s:
                    break

            pbar.close()

        except Exception as e:
            print(f"[!] Error in Chunk {chunk_id} ({ds_name}): {e}")
            import traceback
            traceback.print_exc()

        t_chunk_elapsed = round(time.time() - t_chunk_start, 2)
        throughput = round(processed_chunk_sentences / max(0.001, t_chunk_elapsed), 1)
        total_tokens_now = sum(unjumble_hmm.word_unigrams.values())

        print(f"\n[Chunk {chunk_id} Ingested] {processed_chunk_sentences:,} sentences ({processed_chunk_tokens:,} tokens) in {t_chunk_elapsed}s ({throughput} sent/s)")

        # Sync next_hmm token counters
        next_hmm.sentence_count = unjumble_hmm.sentence_count
        next_hmm.total_tokens = total_tokens_now
        next_hmm.vocabulary = set(unjumble_hmm.word_unigrams.keys())

        # Prune rare transitions frequently to ensure constant memory footprint (<18GB)
        if chunk_id % 2 == 0 or len(next_hmm.fourgrams) > 10000000 or len(unjumble_hmm.word_trigrams) > 10000000:
            print("[*] Running periodic memory compaction and pruning rare transitions...")
            unjumble_hmm.prune_rare_transitions(min_count=2)
            next_hmm.prune_rare_transitions(min_count=2)
            gc.collect()

        # Run Validation Benchmarks
        print("[*] Running Clinical AAC Validation Benchmarks...")
        t_eval_start = time.time()
        eval_m = evaluate_models(next_hmm, unjumble_hmm)
        t_eval_elapsed = round(time.time() - t_eval_start, 2)

        print(f"  -> Next-Word Top-1 Acc:  {eval_m['nextword_top1_acc']}%")
        print(f"  -> Next-Word Top-3 Acc:  {eval_m['nextword_top3_acc']}%")
        print(f"  -> Next-Word Top-5 Acc:  {eval_m['nextword_top5_acc']}%")
        print(f"  -> Next-Word Top-10 Acc: {eval_m['nextword_top10_acc']}%")
        print(f"  -> Unjumble Exact Match: {eval_m['unjumble_exact_match_pct']}%")
        print(f"  -> Unjumble Kendall-Tau: {eval_m['unjumble_kendall_tau']}")

        # Save Checkpoint metrics
        chunk_checkpoint = {
            "chunk_id": chunk_id,
            "timestamp": datetime.now().isoformat(),
            "dataset_name": ds_name,
            "description": desc,
            "chunk_sentences": processed_chunk_sentences,
            "total_sentences": unjumble_hmm.sentence_count,
            "total_tokens": total_tokens_now,
            "vocab_size": len(unjumble_hmm.word_unigrams),
            "bigram_states": len(unjumble_hmm.word_bigrams),
            "trigram_states": len(unjumble_hmm.word_trigrams),
            "fourgram_states": len(next_hmm.fourgrams),
            "elapsed_seconds": t_chunk_elapsed,
            "throughput_sps": throughput,
            "eval_metrics": eval_m
        }
        metrics_history.append(chunk_checkpoint)
        completed_chunks.add(chunk_id)
        with open(METRICS_FILE, "w") as f:
            json.dump(metrics_history, f, indent=2)

        # Update Live Status
        update_live_status(
            chunk_id=chunk_id, dataset_name=ds_name, chunk_sents=processed_chunk_sentences,
            total_sents=unjumble_hmm.sentence_count, total_toks=total_tokens_now,
            vocab_sz=len(unjumble_hmm.word_unigrams), bi_sz=len(unjumble_hmm.word_bigrams),
            tri_sz=len(unjumble_hmm.word_trigrams), four_sz=len(next_hmm.fourgrams),
            eval_m=eval_m, elapsed=t_chunk_elapsed, pct=100.0, status=f"CHUNK_{chunk_id}_COMPLETE"
        )

        # Serialize HMM Checkpoints safely with memory guard
        print("[*] Serializing HMM Checkpoints...")
        gc.collect()

        # 1. HMM-2 (Syntactic Unjumble + Master N-grams)
        with open(latest_uj_path + ".tmp", "wb") as f:
            pickle.dump(unjumble_hmm, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(latest_uj_path + ".tmp", latest_uj_path)
        gc.collect()

        # 2. HMM-1 (Lightweight Next-Word Config & Fourgrams)
        with open(latest_next_path + ".tmp", "wb") as f:
            pickle.dump({
                "fourgrams": next_hmm.fourgrams,
                "lambda1": next_hmm.lambda1,
                "lambda2": next_hmm.lambda2,
                "lambda3": next_hmm.lambda3,
                "lambda4": next_hmm.lambda4,
                "sentence_count": next_hmm.sentence_count,
                "total_tokens": next_hmm.total_tokens
            }, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(latest_next_path + ".tmp", latest_next_path)
        gc.collect()

        # 3. Master Backend Model (saved periodically to conserve RAM during heavy runs)
        if chunk_id % 5 == 0:
            save_master_backend_hmm(next_hmm, unjumble_hmm)
            gc.collect()

        print(f"[✓] Chunk {chunk_id} Complete! Cumulative sentences: {unjumble_hmm.sentence_count:,}\n")

if __name__ == "__main__":
    run_streaming_pipeline()
