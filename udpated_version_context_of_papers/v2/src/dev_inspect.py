#!/usr/bin/env python3
"""DEV-ONLY inspection used for tuning: list gate false accepts / rejections against scorer v2 and failing hybrid outputs on the development split."""
import csv, collections, sys
from common import *
import score_v2 as S2, replay as R
sc = {r["id"]: r for r in jl(V2 / "fixtures/dev/scenarios.jsonl")}
streams = R.load_streams("dev"); LLM0, SEM0 = R._arch(); V1 = R.SEM.SemanticValidator(None)
n = 0
for (i, gen, mode, sd), r in sorted(streams.items(), key=lambda x: x[0][0]):
    s = sc[i]
    if s["expected_outcome"] != "sentence" or not r.get("attempts"): continue
    pay = dict(r["payload"], language=s["lang"]); ctx1 = R.P.normalize_request(pay)
    at = r["attempts"][0]
    if at.get("text") is None: continue
    ok = S2.score(R.scorer_sc(s), at["text"]); acc, d = V1.validate(ctx1, {}, at["text"], s["lang"])
    if acc != ok["success"]:
        n += 1
        print("FA" if acc else "FR", i, "|", at["text"], "| gate:", d["violations_detected"], "| scorer:", {k: v for k, v in ok.items() if k in ("retention", "polarity_ok", "act_ok", "unsupported", "unsupported_hits", "third_person", "offtask", "script_ok")})
print("disagreements:", n)
