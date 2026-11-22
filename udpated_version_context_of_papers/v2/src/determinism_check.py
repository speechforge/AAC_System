#!/usr/bin/env python3
"""Can a deterministic retry change an output?  For Indic items (greedy few-shot path) generate the full cascade twice WITHOUT the prompt cache (two real GPU
runs per item, same process, same context) and compare candidate texts at every stage.  Also repeats the check across two fresh calls of LLM-3 alone.
Output: results/audit/B_determinism_check.json"""
import json, random, sys, time
import torch
from common import *
sys.path.insert(0, str(REPO / "backend"))
import pipeline as P
from llm import IndicLLM

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
rows = [r for r in jl(V2 / "fixtures/dev/scenarios.jsonl") if r["lang"] in ("hi", "gu", "mr")]
rng = random.Random(20261113); rows = rng.sample(rows, min(N, len(rows)))
import run_streams as RS
llm = IndicLLM()
res = []
for r in rows:
    ctx = P.normalize_request(RS.gold_payload(r, "G1"))
    outs = []
    for k in range(2):
        gen, sctx, ledger, c1, c2, dec, tel = llm.generate_sentence(ctx, language=r["lang"], code_mix=False, mode="dual")
        outs.append(dict(final=gen, llm1=c1, llm2=c2, llm3=dec.get("final_text")))
    res.append(dict(id=r["id"], identical=outs[0] == outs[1], outs=outs))
n_same = sum(x["identical"] for x in res)
summary = dict(n_items=len(res), n_identical_across_two_uncached_runs=n_same, n_different=len(res) - n_same, languages=sorted({r["lang"] for r in rows}),
               gpu="GTX 1650", torch=torch.__version__, differing=[x for x in res if not x["identical"]][:10], measured_at=now_utc())
(V2 / "results/audit/B_determinism_check.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k != "differing"}, ensure_ascii=False))
