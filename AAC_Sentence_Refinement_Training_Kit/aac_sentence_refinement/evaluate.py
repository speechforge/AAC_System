#!/usr/bin/env python3
"""Paired AAC evaluation; synthetic exact match is not a human utility score."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from aac_refiner import (AACInput, AACRefiner, LocalSeq2SeqBackend, NEGATORS,
                         RefinementResult, analyze, validate_candidate, words)


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    s = sorted(values)
    position = (len(s) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    return s[lo] + (s[hi] - s[lo]) * (position - lo)


def clustered_ci(rows: list[dict], key: str, seed: int, replicates: int = 2000) -> list[float] | None:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row[key] is not None:
            groups[row["group_id"]].append(float(row[key]))
    if not groups:
        return None
    # Resample whole selection groups, keeping every draft/polarity variant.
    summaries = [(sum(v), len(v)) for v in groups.values()]
    rng = random.Random(seed)
    estimates = []
    for _ in range(replicates):
        sample = rng.choices(summaries, k=len(summaries))
        estimates.append(sum(x[0] for x in sample) / sum(x[1] for x in sample))
    return [percentile(estimates, 0.025), percentile(estimates, 0.975)]


def summarize(rows: list[dict], seed: int) -> dict:
    out = dict(n=len(rows), groups=len({r["group_id"] for r in rows}))
    for key in ("exact_match", "validator_pass", "negation_error", "added_content", "raw_fallback"):
        eligible = [r[key] for r in rows if r[key] is not None]
        out[key] = dict(numerator=sum(eligible), denominator=len(eligible),
                        rate=sum(eligible) / len(eligible) if eligible else None,
                        ci95=clustered_ci(rows, key, seed))
    latencies = [r["elapsed_ms"] for r in rows]
    out["latency_ms"] = dict(mean=statistics.mean(latencies), p50=percentile(latencies, 0.5),
                             p95=percentile(latencies, 0.95), p99=percentile(latencies, 0.99),
                             max=max(latencies))
    out["routes"] = dict(Counter(r["route"] for r in rows))
    out["fallback_reasons"] = dict(Counter(reason for r in rows if r["raw_fallback"]
                                           for reason in r["violations"]))
    out["model_attempts"] = sum(bool(r["model_attempted"]) for r in rows)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--mode", choices=["raw", "rules", "model", "hybrid", "all"], default="rules")
    parser.add_argument("--model")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--out", type=Path, default=Path("evaluation"))
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--bootstrap-seed", type=int, default=42)
    args = parser.parse_args()
    with args.data.open(encoding="utf-8") as handle:
        data = [json.loads(line) for line in handle if line.strip()]
    if not data:
        raise ValueError("Evaluation data is empty")
    modes = ["raw", "rules", "model", "hybrid"] if args.mode == "all" else [args.mode]
    if set(modes) & {"model", "hybrid"} and not args.model:
        parser.error("--model is required for neural evaluation")
    args.out.mkdir(parents=True, exist_ok=True)
    startup = time.monotonic()
    backend = LocalSeq2SeqBackend(args.model, device=args.device) if args.model else None
    startup_ms = (time.monotonic() - startup) * 1000
    if backend and backend.startup_error:
        backend.close()
        raise RuntimeError("Model evaluation cannot proceed: " + backend.startup_error)
    all_rows = []
    try:
        for mode in modes:
            # Disable output cache: the metric is not dominated by repeated UI drafts.
            refiner = AACRefiner(backend if mode in {"model", "hybrid"} else None,
                                 rules_first=mode != "model", timeout_s=args.timeout, cache_size=0)
            for sample in data:
                payload = sample["payload"]
                item = AACInput.parse(payload)
                frame = analyze(item)
                if mode == "raw":
                    result = RefinementResult(item.raw_sentence, "raw", 0.0, [])
                else:
                    result = refiner.refine_detailed(payload)
                diagnostics = validate_candidate(result.text, item, frame)
                applicable = frame.blocked is None
                exact = result.text in sample.get("references", [sample["target"]])
                row = dict(
                    id=sample["id"], group_id=sample["group_id"], intent=sample.get("intent", "unknown"),
                    method=mode, payload=payload, reference=sample["target"], **asdict(result),
                    diagnostics=diagnostics, exact_match=bool(exact),
                    validator_pass=(not diagnostics) if applicable else None,
                    negation_error=(not bool(set(words(result.text)) & NEGATORS)) if frame.negated else None,
                    added_content=("added_content" in diagnostics) if applicable else None,
                    raw_fallback=result.route == "raw_fallback",
                )
                if result.candidate is not None:
                    row["candidate_exact_match"] = result.candidate in sample.get("references", [sample["target"]])
                    row["candidate_diagnostics"] = validate_candidate(result.candidate, item, frame)
                all_rows.append(row)
    finally:
        if backend:
            backend.close()
    grouped = {mode: [row for row in all_rows if row["method"] == mode] for mode in modes}
    report = dict(
        dataset=str(args.data.resolve()), dataset_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(),
        checkpoint=args.model, model_startup_and_warmup_ms=startup_ms if args.model else None,
        timeout_s=args.timeout, cache_enabled=False, bootstrap_seed=args.bootstrap_seed,
        observation_unit="one AAC payload/draft; paired across methods",
        bootstrap_unit="selection group, including all draft and polarity variants; 2000 resamples",
        rates_are_fractions=True,
        definitions={
            "exact_match": "exact string match against supplied references, all evaluation rows",
            "validator_pass": "heuristic/frame validation pass among supported frames; not human semantic accuracy",
            "negation_error": "selected-negation omission among all inputs containing a recognized selected negator",
            "added_content": "unselected-content diagnostic among supported frames; does not detect all semantic errors",
            "raw_fallback": "returned original raw_sentence after blocking, failure or rejection; all rows",
            "latency_ms": "warm synchronous wall time including parsing/IPC/validation; excludes initial model loading",
        },
        methods={mode: summarize(rows, args.bootstrap_seed) for mode, rows in grouped.items()},
        by_intent={mode: {intent: summarize([r for r in rows if r["intent"] == intent], args.bootstrap_seed)
                         for intent in sorted({r["intent"] for r in rows})}
                   for mode, rows in grouped.items()},
        limitations=[
            "Template-derived tests share grammar and vocabulary with the implementation.",
            "Group splitting prevents draft duplication leakage; it does not measure new-user or new-domain generalization.",
            "Exact match can penalize valid unlisted paraphrases; validator metrics are diagnostics.",
            "No clinical, conversational-rate, TTS, human-adequacy or real-world safety measurements are produced.",
        ],
    )
    # Paired group bootstrap of exact-match differences against raw drafts.
    report["paired_exact_match_difference_vs_raw"] = {}
    if "raw" in grouped:
        raw_by_id = {r["id"]: r for r in grouped["raw"]}
        for mode in modes:
            if mode == "raw":
                continue
            deltas = [dict(group_id=r["group_id"], delta=int(r["exact_match"]) -
                           int(raw_by_id[r["id"]]["exact_match"])) for r in grouped[mode]]
            report["paired_exact_match_difference_vs_raw"][mode] = dict(
                mean=sum(r["delta"] for r in deltas) / len(deltas),
                ci95=clustered_ci(deltas, "delta", args.bootstrap_seed), n_pairs=len(deltas))
    (args.out / "predictions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in all_rows), encoding="utf-8")
    (args.out / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (args.out / "metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["method", "metric", "numerator", "denominator", "rate", "ci95_low", "ci95_high"])
        for mode, metrics in report["methods"].items():
            for metric in ("exact_match", "validator_pass", "negation_error", "added_content", "raw_fallback"):
                value = metrics[metric]
                writer.writerow([mode, metric, value["numerator"], value["denominator"], value["rate"],
                                 *(value["ci95"] or [None, None])])
    figure_status = "not_created: matplotlib_unavailable"
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 3.6), layout="constrained")
        values = [report["methods"][m]["exact_match"]["rate"] * 100 for m in modes]
        ax.bar(modes, values, color="#2165b2")
        ax.set(ylabel="Reference exact match (%)", ylim=(0, 105), title="AAC regression evaluation")
        for i, value in enumerate(values):
            ax.text(i, value + 1, f"{value:.1f}", ha="center", fontsize=9)
        fig.savefig(args.out / "exact_match.png", dpi=180)
        fig.savefig(args.out / "exact_match.svg")
        plt.close(fig)
        figure_status = "exact_match.png; exact_match.svg"
    except ImportError:
        pass
    lines = ["# Verified evaluation context", "", "Generated from this evaluation invocation only.", "",
             f"- Input: `{args.data.resolve()}`", f"- Input SHA256: `{report['dataset_sha256']}`",
             f"- Checkpoint: `{args.model}`", f"- Seed for cluster bootstrap: {args.bootstrap_seed}",
             f"- Figures: {figure_status}", f"- Observation unit: {report['observation_unit']}",
             f"- Uncertainty: {report['bootstrap_unit']}", "",
             "| Method | Rows | Groups | Exact match | Raw fallback | p95 latency (ms) |",
             "|---|---:|---:|---:|---:|---:|"]
    for mode, metric in report["methods"].items():
        lines.append(f"| {mode} | {metric['n']} | {metric['groups']} | "
                     f"{metric['exact_match']['rate']:.4f} | {metric['raw_fallback']['rate']:.4f} | "
                     f"{metric['latency_ms']['p95']:.3f} |")
    lines += ["", "Metric definitions and exact numerators/denominators: `metrics.json` and `metrics.csv`.",
              "Per-payload outputs, rejections and raw model candidates: `predictions.jsonl`.", "",
              "## Negative findings and gaps", ""] + ["- " + x for x in report["limitations"]]
    (args.out / "FINAL_CONTEXT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report["methods"], indent=2))


if __name__ == "__main__":
    main()
