#!/usr/bin/env python3
"""Score the SAME saved archived outputs (scored.csv text column) with scorer v1 (archived, unmodified) and scorer v2, and report
the effect of the scorer change on every system/condition (primary 175 scenarios).  Also checks scorer v2 on the Phase-A scorer probes
(results/audit/A5_scorer_probes.csv, written before v2 existed).  Outputs: results/audit/B_scorer_effect.csv, B_scorer_effect_cases.csv, B_scorer_probes_v2.csv"""
import csv, collections, sys
from common import *
import score_v2 as S2
S1 = load_module("score_v1", ARCH / "score.py")
scs = {s["id"]: s for s in jl(ARCH / "fixtures/scenarios.jsonl")}
rows = list(csv.DictReader(open(ARCH / "results/scored.csv", encoding="utf-8")))
cnt = collections.defaultdict(lambda: [0, 0, 0, 0])   # n, v1, v2, changed
cases = []
for r in rows:
    if r["code_mix"] == "True" or r["overlap"] == "True":
        continue
    sc = scs[r["id"]]
    a, b = S1.score(sc, r["text"]), S2.score(sc, r["text"])
    k = (r["system"], r["cond"])
    cnt[k][0] += 1; cnt[k][1] += a["success"]; cnt[k][2] += b["success"]
    if a["success"] != b["success"]:
        cnt[k][3] += 1
        cases.append(dict(id=r["id"], system=r["system"], cond=r["cond"], text=r["text"], v1=a["success"], v2=b["success"],
                          v2_flags="|".join(k2 for k2 in ("polarity_ok", "act_ok", "unsupported", "offtask", "third_person", "script_ok") if (b[k2] != (k2 in ("polarity_ok", "act_ok", "script_ok"))))))
out = [dict(system=k[0], cond=k[1], n=v[0], success_v1=v[1], success_v2=v[2], n_changed=v[3]) for k, v in sorted(cnt.items())]
write_csv(V2 / "results/audit/B_scorer_effect.csv", out); write_csv(V2 / "results/audit/B_scorer_effect_cases.csv", cases)
for o in out: print(o)
# scorer v2 on the Phase-A probes
pr = list(csv.DictReader(open(V2 / "results/audit/A5_scorer_probes.csv", encoding="utf-8")))
bad = 0; res = []
for p in pr:
    sc = dict(lang=p["lang"], code_mix=False, content_concepts=[c for c in p["concepts"].split("+") if c], gold_neg=p["gold_neg"] == "True", gold_act=p["gold_act"])
    v1, v2 = p["scorer_success"] == "True", S2.score(sc, p["text"])["success"]
    exp = p["expected_success"] == "True"
    res.append(dict(question=p["question"], lang=p["lang"], text=p["text"], expected=exp, v1=v1, v2=v2, v1_ok=(v1 == exp), v2_ok=(v2 == exp)))
    bad += (v2 != exp)
write_csv(V2 / "results/audit/B_scorer_probes_v2.csv", res)
print(f"A5 probes: v1 agrees {sum(r['v1_ok'] for r in res)}/{len(res)}; v2 agrees {sum(r['v2_ok'] for r in res)}/{len(res)}")
for r in res:
    if not r["v2_ok"]: print("  v2 disagrees:", r["lang"], r["text"], "expected", r["expected"])
