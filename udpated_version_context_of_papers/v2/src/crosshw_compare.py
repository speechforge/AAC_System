#!/usr/bin/env python3
"""Cross-hardware reproducibility: the holdout rows first generated on the local GTX 1650 (results/streams/local_gtx1650/, torch 2.11.0+cu130, transformers 5.14.1)
are compared with the same keys generated on the PC's TITAN Xp (torch 2.11.0+cu126, transformers 5.14.1).  Same model weights (sha256), same prompts, same decoding, same seeds.
Reports, per stage, how many candidate texts are identical.  Output: results/audit/B_crosshardware_repro.json"""
import collections, glob, json
from common import *

loc = {}
for p in sorted(glob.glob(str(V2 / "results/streams/local_gtx1650/holdout*.jsonl"))):
    for r in jl(p):
        if r.get("attempts") is not None and "gen" in r: loc[(r["id"], r["gen"], r["mode"], r["seed"])] = r
rem = {}
for p in sorted(glob.glob(str(V2 / "results/streams/holdout*remote*.jsonl"))):
    for r in jl(p):
        if r.get("attempts") is not None and "gen" in r: rem[(r["id"], r["gen"], r["mode"], r["seed"])] = r
cnt = collections.Counter(); diffs = []; by_lang = collections.defaultdict(collections.Counter)
for k, l in loc.items():
    r = rem.get(k)
    if not r or not l["attempts"] or not r["attempts"]: cnt["missing_remote"] += 1; continue
    for stage in ("llm1", "llm2", "llm3_text", "text"):
        a, b = l["attempts"][0].get(stage), r["attempts"][0].get(stage)
        cnt[f"{stage}_same" if a == b else f"{stage}_diff"] += 1
        by_lang[l["lang"]][f"{stage}_same" if a == b else f"{stage}_diff"] += 1
    if l["attempts"][0].get("text") != r["attempts"][0].get("text"):
        diffs.append(dict(key=list(k), local=l["attempts"][0].get("text"), remote=r["attempts"][0].get("text")))
n = sum(1 for k in loc if k in rem and loc[k]["attempts"] and rem[k]["attempts"])
res = dict(n_local_rows=len(loc), n_compared=n, counts=dict(cnt), by_language={k: dict(v) for k, v in by_lang.items()}, differing_final_candidates=diffs[:25], measured_at=now_utc(),
           note="attempt-1 candidates compared; greedy Indic path and seeded English sampling path")
(V2 / "results/audit/B_crosshardware_repro.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "differing_final_candidates"}, ensure_ascii=False))
