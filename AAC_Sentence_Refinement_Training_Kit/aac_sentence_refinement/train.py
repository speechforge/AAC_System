#!/usr/bin/env python3
"""Single-GPU seq2seq fine-tuning with token-weighted loss and epoch checkpoints.

Default: CUDA + FP32. No FlashAttention, BF16, quantization, or external trackers
are required. Set --device cpu explicitly for a small functional smoke test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    if not rows:
        raise ValueError(f"Empty training/evaluation file: {path}")
    for index, row in enumerate(rows):
        if not all(isinstance(row.get(k), str) and row[k] for k in ("source", "target", "group_id")):
            raise ValueError(f"Invalid source/target/group_id at {path}:{index + 1}")
    return rows


def check_split(train: list[dict], valid: list[dict]) -> None:
    for key in ("source", "target", "group_id"):
        overlap = {r[key] for r in train} & {r[key] for r in valid}
        if overlap:
            raise ValueError(f"Training/validation leakage in {key}: {len(overlap)} values")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-file", type=Path, required=True)
    parser.add_argument("--valid-file", type=Path, required=True)
    parser.add_argument("--model", default="google/flan-t5-small")
    parser.add_argument("--revision", default="main")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--precision", default="fp32", choices=["fp32", "bf16", "fp16"])
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--max-steps", type=int, default=0, help="0 uses epochs; positive overrides epochs")
    parser.add_argument("--lr", type=float, default=0.0001)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-source-tokens", type=int, default=256)
    parser.add_argument("--max-target-tokens", type=int, default=64)
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--resume", type=Path, help="This script's completed-epoch checkpoint directory")
    args = parser.parse_args()
    if min(args.batch_size, args.grad_accum, args.epochs) < 1 or args.max_steps < 0:
        parser.error("batch-size, grad-accum and epochs must be positive; max-steps must be nonnegative")
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, get_linear_schedule_with_warmup
    from huggingface_hub import HfApi

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if args.device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is unavailable; run preflight.py. CPU must be selected explicitly.")
        torch.cuda.manual_seed_all(args.seed)
        # Verify a real kernel; an incompatible Pascal wheel can report CUDA but fail here.
        torch.ones(8, 8, device="cuda").matmul(torch.ones(8, 8, device="cuda"))
        torch.cuda.synchronize()
        torch.backends.cudnn.benchmark = False
    if args.precision != "fp32" and args.device != "cuda":
        raise ValueError("Mixed precision is enabled only for CUDA in this script")
    if args.precision == "bf16" and not torch.cuda.is_bf16_supported():
        raise ValueError("This GPU does not support BF16. Use --precision fp32.")
    if args.precision == "fp16" and torch.cuda.get_device_capability()[0] < 7:
        raise ValueError("Use FP32 on Pascal GPUs; the initial T5 pilot avoids Pascal FP16 training.")
    train_rows, valid_rows = load_rows(args.train_file), load_rows(args.valid_file)
    check_split(train_rows, valid_rows)
    args.output.mkdir(parents=True, exist_ok=True)
    if (args.output / "run_config.json").exists() and not args.resume:
        raise FileExistsError("Output already contains a run. Choose another output or use --resume.")
    model_source = str(args.resume) if args.resume else args.model
    local_model = Path(model_source).is_dir()
    sha = None if local_model else HfApi().model_info(model_source, revision=args.revision).sha
    load_kwargs: dict[str, Any] = {"trust_remote_code": False}
    if sha:
        load_kwargs["revision"] = sha
    tokenizer = AutoTokenizer.from_pretrained(model_source, **load_kwargs)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_source, torch_dtype=torch.float32, use_safetensors=True, **load_kwargs
    ).to(args.device)
    model.config.use_cache = False
    if args.gradient_checkpointing:
        model.gradient_checkpointing_enable()

    def encode(rows: list[dict]) -> list[dict]:
        encoded = []
        for row in rows:
            source = tokenizer(row["source"], truncation=False)
            target = tokenizer(text_target=row["target"], truncation=False)["input_ids"]
            if len(source["input_ids"]) > args.max_source_tokens or len(target) > args.max_target_tokens:
                raise ValueError(f"Example {row.get('id')} exceeds a token limit; do not silently truncate semantics.")
            encoded.append({**source, "labels": target})
        return encoded
    train_data, valid_data = encode(train_rows), encode(valid_rows)

    def collate(batch: list[dict]) -> dict:
        model_input = tokenizer.pad(
            [{k: v for k, v in row.items() if k != "labels"} for row in batch],
            padding=True, return_tensors="pt",
        )
        labels = torch.full((len(batch), max(len(row["labels"]) for row in batch)), -100, dtype=torch.long)
        for i, row in enumerate(batch):
            labels[i, :len(row["labels"])] = torch.tensor(row["labels"], dtype=torch.long)
        return {**model_input, "labels": labels}

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    batches_per_epoch = math.ceil(len(train_data) / args.batch_size)
    updates_per_epoch = math.ceil(batches_per_epoch / args.grad_accum)
    total_updates = args.max_steps or updates_per_epoch * args.epochs
    epochs = math.ceil(total_updates / updates_per_epoch)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(total_updates * 0.05), total_updates)
    scaler = torch.amp.GradScaler("cuda", enabled=args.precision == "fp16")
    run_config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    run_config.update(
        train_sha256=file_hash(args.train_file), valid_sha256=file_hash(args.valid_file),
        resolved_model_revision=sha,
        local_model_sha256=file_hash(Path(model_source) / "model.safetensors")
        if local_model and (Path(model_source) / "model.safetensors").exists() else None,
        torch=torch.__version__, gpu=torch.cuda.get_device_name() if args.device == "cuda" else None,
        train_rows=len(train_data), valid_rows=len(valid_data),
        train_groups=len({r["group_id"] for r in train_rows}),
        valid_groups=len({r["group_id"] for r in valid_rows}), total_updates=total_updates,
        parameter_count=sum(p.numel() for p in model.parameters()),
        effective_batch_size=args.batch_size * args.grad_accum,
        objective="mean cross-entropy per nonpadding target token within each optimizer update",
        determinism="seeded; exact cross-device/driver bitwise reproducibility is not claimed",
    )
    print(json.dumps(run_config, indent=2), flush=True)
    start_epoch, step, best_loss = 0, 0, float("inf")
    if args.resume:
        # Only read this script's own trusted local training-state checkpoints.
        state = torch.load(args.resume / "training_state.pt", map_location="cpu", weights_only=False)
        for key in ("train_sha256", "valid_sha256", "seed", "total_updates", "batch_size", "grad_accum",
                    "lr", "weight_decay", "precision", "max_source_tokens", "max_target_tokens",
                    "gradient_checkpointing"):
            if state["run_config"][key] != run_config[key]:
                raise ValueError(f"Resume configuration/data mismatch: {key}")
        if not state["completed_epoch"]:
            raise ValueError("A partial-epoch checkpoint is for inference only; exact mid-epoch resume is not implemented.")
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        scaler.load_state_dict(state["scaler"])
        start_epoch, step, best_loss = state["next_epoch"], state["step"], state["best_loss"]
        random.setstate(state["python_rng"])
        torch.set_rng_state(state["torch_rng"])
        if args.device == "cuda":
            torch.cuda.set_rng_state_all(state["cuda_rng"])
    else:
        (args.output / "run_config.json").write_text(json.dumps(run_config, indent=2) + "\n")

    def autocast_context():
        if args.precision == "fp32":
            return nullcontext()
        return torch.autocast("cuda", dtype=torch.bfloat16 if args.precision == "bf16" else torch.float16)

    def validate() -> float:
        model.eval()
        total, tokens = 0.0, 0
        with torch.inference_mode():
            for batch in DataLoader(valid_data, batch_size=args.batch_size, collate_fn=collate):
                count = int((batch["labels"] != -100).sum())
                batch = {k: v.to(args.device) for k, v in batch.items()}
                with autocast_context():
                    loss = model(**batch).loss
                if not torch.isfinite(loss):
                    raise FloatingPointError("Nonfinite validation loss; retry the experiment in FP32.")
                total += loss.item() * count
                tokens += count
        return total / tokens

    def save_checkpoint(name: str, next_epoch: int, completed_epoch: bool) -> None:
        folder = args.output / name
        folder.mkdir(exist_ok=True)
        model.save_pretrained(folder, safe_serialization=True)
        tokenizer.save_pretrained(folder)
        torch.save(dict(
            optimizer=optimizer.state_dict(), scheduler=scheduler.state_dict(), scaler=scaler.state_dict(),
            next_epoch=next_epoch, completed_epoch=completed_epoch, step=step, best_loss=best_loss,
            python_rng=random.getstate(), torch_rng=torch.get_rng_state(),
            cuda_rng=torch.cuda.get_rng_state_all() if args.device == "cuda" else [], run_config=run_config,
        ), folder / "training_state.pt")

    started = time.monotonic()
    if args.device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    for epoch in range(start_epoch, epochs):
        generator = torch.Generator().manual_seed(args.seed + epoch)
        loader = DataLoader(train_data, batch_size=args.batch_size, shuffle=True,
                            generator=generator, collate_fn=collate, num_workers=0)
        iterator = iter(loader)
        model.train()
        total_loss, total_tokens, seen_batches = 0.0, 0, 0
        while seen_batches < len(loader) and step < total_updates:
            group = []
            for _ in range(min(args.grad_accum, len(loader) - seen_batches)):
                group.append(next(iterator))
                seen_batches += 1
            group_tokens = sum(int((b["labels"] != -100).sum()) for b in group)
            optimizer.zero_grad(set_to_none=True)
            for batch in group:
                n_tokens = int((batch["labels"] != -100).sum())
                batch = {k: v.to(args.device) for k, v in batch.items()}
                with autocast_context():
                    loss = model(**batch).loss
                    scaled_loss = loss * (n_tokens / group_tokens)
                if not torch.isfinite(loss):
                    raise FloatingPointError("Nonfinite training loss; use FP32 and inspect the offending example.")
                scaler.scale(scaled_loss).backward()
                total_loss += loss.item() * n_tokens
                total_tokens += n_tokens
            scaler.unscale_(optimizer)
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            step += 1
            if step == 1 or step % 50 == 0:
                print(json.dumps(dict(epoch=epoch + 1, step=step, train_loss=total_loss / total_tokens,
                                      grad_norm=float(norm))), flush=True)
        val_loss = validate()
        improved = val_loss < best_loss
        if improved:
            best_loss = val_loss
        complete = seen_batches == len(loader)
        save_checkpoint("last", epoch + 1, complete)
        if improved:
            save_checkpoint("best", epoch + 1, complete)
        record = dict(epoch=epoch + 1, step=step, train_loss=total_loss / total_tokens,
                      validation_loss=val_loss, best_validation_loss=best_loss,
                      completed_epoch=complete, elapsed_s=time.monotonic() - started)
        with (args.output / "history.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        print(json.dumps(record), flush=True)
    summary = dict(completed_steps=step, best_validation_loss=best_loss,
                   elapsed_this_invocation_s=time.monotonic() - started,
                   peak_allocated_vram_gib=torch.cuda.max_memory_allocated() / 2**30
                   if args.device == "cuda" else None, output=str(args.output.resolve()))
    (args.output / "training_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
