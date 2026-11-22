#!/usr/bin/env python3
"""Reproduce the flan-T5-small refiner's reported test metrics from its RAW per-payload predictions
(AAC_Sentence_Refinement_Training_Kit/.../runs/seed_42_gpu_max/eval_*/predictions.jsonl) and compare with the kit's own metrics.csv."""
import json, csv, pathlib, collections, numpy as np
HERE = pathlib.Path(__file__).resolve().parent
K = HERE.parents[2] / "AAC_Sentence_Refinement_Training_Kit/aac_sentence_refinement"
RUNS = K / "runs/seed_42_gpu_max"
rng = np.random.default_rng(20261111)
out = {}
for arm in ("aac_only", "fluency_then_aac"):
    rows = [json.loads(l) for l in (RUNS / f"eval_{arm}/predictions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ref = {(r["method"], r["metric"]): r for r in csv.DictReader(open(RUNS / f"eval_{arm}/metrics.csv"))}
    by = collections.defaultdict(list)
    for r in rows: by[r["method"]].append(r)
    out[arm] = {}
    for m, rs in by.items():
        n = len(rs); em = sum(bool(r["exact_match"]) for r in rs); vp = sum(bool(r["validator_pass"]) for r in rs)
        neg = [r for r in rs if r["negation_error"] is not None]; ne = sum(bool(r["negation_error"]) for r in neg)
        groups = sorted({r["group_id"] for r in rs}); gi = {g: i for i, g in enumerate(groups)}
        v = np.array([float(r["exact_match"]) for r in rs]); gidx = np.array([gi[r["group_id"]] for r in rs])
        sums = np.bincount(gidx, weights=v, minlength=len(groups)); cnt = np.bincount(gidx, minlength=len(groups)).astype(float)
        d = rng.integers(0, len(groups), size=(10000, len(groups))); bs = sums[d].sum(1) / cnt[d].sum(1)
        lat = [r["elapsed_ms"] for r in rs if r.get("model_attempted")]
        out[arm][m] = dict(n=n, groups=len(groups), exact_match=em, validator_pass=vp, negation_errors=f"{ne}/{len(neg)}", added_content=sum(bool(r["added_content"]) for r in rs),
                           raw_fallback=sum(bool(r["raw_fallback"]) for r in rs), em_ci95_group_bootstrap=[round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                           median_latency_ms_model_calls=(round(float(np.median(lat)), 1) if lat else None), n_model_calls=len(lat),
                           matches_kit_metrics_csv=(int(ref[(m, "exact_match")]["numerator"]) == em and int(ref[(m, "exact_match")]["denominator"]) == n))
reg = {}
for arm in ("aac_only", "fluency_then_aac"):
    rs = [json.loads(l) for l in (RUNS / f"regression_{arm}/predictions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    reg[arm] = {m: f"{sum(bool(r['exact_match']) for r in rs if r['method']==m)}/{sum(1 for r in rs if r['method']==m)}" for m in sorted({r['method'] for r in rs})}
out["regression_8cases_exact_match"] = reg
out["training_data_provenance"] = "provenance=synthetic_template_v1 (kit prepare_data.py); references are produced by the same template families as the rule path, so the rule/hybrid scores are 100% by construction"
(HERE / "results/refiner_repro.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps({a: {m: (v['exact_match'], v['n'], v['matches_kit_metrics_csv'], v['median_latency_ms_model_calls']) for m, v in d.items()} for a, d in out.items() if a in ('aac_only', 'fluency_then_aac')}))
print(json.dumps(reg))
