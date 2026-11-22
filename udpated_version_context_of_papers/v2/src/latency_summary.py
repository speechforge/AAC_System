#!/usr/bin/env python3
"""Latency cost per method (seconds).  Sources: live HTTP runs on the PC (results/e2e/holdout_hybrid_pc.jsonl, TITAN Xp, includes validation and placeholder TTS), the browser-to-speech
check on the local GTX 1650 (results/audit/B_speech_path.json), generation calls in the PC streams (LLM stage sums, warm, uncached originals) and one-pass calls, and the CPU time of the repaired
template.  Output: results/tables/T7_latency_holdout.csv"""
import json, statistics, sys, time, collections
from common import *
sys.path.insert(0, str(REPO / "backend"))
import pipeline as P, run_streams as RS

def stats(v):
    v = sorted(v); return dict(n=len(v), median_s=round(statistics.median(v), 3), p95_s=round(v[int(0.95 * (len(v) - 1))], 3)) if v else dict(n=0)
rows = []
e2e = [r for r in jl(V2 / "results/e2e/holdout_hybrid_pc.jsonl") if not r.get("error") and r.get("outcome")]
for lang in LANGS + [None]:
    sel = [r for r in e2e if (lang is None or r["lang"] == lang)]
    for route in (None, "model_first", "template_after_rejection", "clarification"):
        v = [r["wall_s"] for r in sel if route is None or r.get("route") == route]
        if v: rows.append(dict(method="revised hybrid, live HTTP /generate", hardware="PC TITAN Xp", lang=lang or "ALL", route=route or "all", **stats(v)))
sp = json.loads((V2 / "results/audit/B_speech_path.json").read_text(encoding="utf-8"))
for lang in LANGS + [None]:
    v = [r["t_first_playback_ms"] / 1000 for r in sp["runs"] if not r["cold"] and r["t_first_playback_ms"] is not None and (lang is None or r["lang"] == lang)]
    if v: rows.append(dict(method="revised hybrid, click to first playback (browser)", hardware="local GTX 1650", lang=lang or "ALL", route="all", **stats(v)))
for gen, name in (("G1", "revised cascade, first attempt (LLM-1+2+3, no gate)"), ("G0", "archived cascade, first attempt")):
    v = []
    for p in (V2 / "results/streams").glob("holdout_remote_*.jsonl"):
        for r in jl(p):
            if r.get("gen") == gen and r.get("attempts"):
                a = r["attempts"][0]
                if a.get("latency") and not a.get("error"): v.append((r["lang"], a["latency"]))
    for lang in LANGS + [None]:
        vv = [x for l, x in v if lang is None or l == lang]
        if vv: rows.append(dict(method=name + " (original uncached GPU calls only: cached repeats excluded where latency is 0)", hardware="PC TITAN Xp", lang=lang or "ALL", route="stage sum", **stats([x for x in vv if x > 0]), note="measured while five jobs shared the PC GPU: inflated; use the live HTTP rows for the latency cost"))
op = [r for r in jl(V2 / "results/streams/onepass_holdout_shard0of1.jsonl") if r.get("latency")]
for lang in LANGS + [None]:
    vv = [r["latency"] for r in op if lang is None or r["lang"] == lang and not r.get("cached")]
    if vv: rows.append(dict(method="matched one-pass prompt (single call)", hardware="PC TITAN Xp", lang=lang or "ALL", route="single call", **stats(vv)))
# repaired template: CPU time of normalise + compose + gate
V1 = RS.SEM.SemanticValidator(None); sc = [r for r in jl(V2 / "fixtures/holdout/scenarios.jsonl")]
t = []
for r in sc:
    pay = dict(RS.gold_payload(r, "G1"), language=r["lang"]); t0 = time.perf_counter()
    ctx = P.normalize_request(pay); P.decide(ctx, r["lang"], lambda k: None, V1, type("L", (), {"realize_template": lambda s, c, l: RS.LLM_REV.realize_template(None, c, l)})(), policy="template_only")
    t.append(time.perf_counter() - t0)
tm = sorted(x * 1000 for x in t)
rows.append(dict(method="repaired template alone (normalise + compose + gate)", hardware="CPU (local)", lang="ALL", route="no model", n=len(tm), median_s=round(statistics.median(tm), 3), p95_s=round(tm[int(0.95 * (len(tm) - 1))], 3), note="median_s / p95_s columns hold MILLISECONDS for this row"))
write_csv(V2 / "results/tables/T7_latency_holdout.csv", rows, ["method", "hardware", "lang", "route", "n", "median_s", "p95_s", "note"]); print(len(rows), "rows")
for r in rows:
    if r["lang"] == "ALL": print(r["method"][:70], r["hardware"], r["route"], r.get("n"), r.get("median_s"), r.get("p95_s"))
