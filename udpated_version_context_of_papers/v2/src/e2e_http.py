#!/usr/bin/env python3
"""End-to-end run of the revised hybrid through the live web backend (POST /generate on :8000) with the payloads captured from the real revised client.
Also used for the latency table (wall time of the HTTP call; TTS is a placeholder tone) and to check that the offline replay of saved streams equals the live path.
Modes: run (default) | compare.   Usage: python e2e_http.py run --split holdout [--seeds 11 23 47] ; python e2e_http.py compare --split holdout"""
import argparse, json, os, sys, time, urllib.request
from common import *

URL = os.environ.get("AAC_URL", "http://localhost:8000") + "/generate"     # set AAC_URL=http://10.100.59.86:8000 for the PC server
TAG = os.environ.get("E2E_TAG", "")


def post(p, timeout=600):
    req = urllib.request.Request(URL, data=json.dumps(p, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read()); err = None
    except Exception as e:
        r, err = None, repr(e)
    return r, err, time.perf_counter() - t


def run(split, seeds, policy="hybrid", tag=""):
    rows = [r for r in jl(V2 / "fixtures" / split / "scenarios.jsonl") if not r.get("code_mix")]
    caps = {r["id"]: r for r in jl(V2 / "results/payloads" / f"revised_{split}.jsonl")}
    out = V2 / "results/e2e" / f"{split}_{policy}{tag or TAG}.jsonl"; out.parent.mkdir(parents=True, exist_ok=True)
    done = {(d["id"], d["seed"]) for d in jl(out)}
    for n, r in enumerate(rows, 1):
        c = caps.get(r["id"])
        if not c or not c.get("payload"): continue
        for sd in (seeds if r["lang"] == "en" else [None]):
            if (r["id"], sd) in done: continue
            p = dict(c["payload"], policy=policy)
            if sd is not None: p["seed"] = sd
            resp, err, wall = post(p)
            rec = dict(id=r["id"], lang=r["lang"], seed=sd, policy=policy, wall_s=round(wall, 3), error=err, ts=time.time())
            if resp:
                rec.update(text=resp.get("text"), outcome=resp.get("outcome"), route=resp.get("route"), act=resp.get("act"), negation=resp.get("negation"),
                           audio_kind=resp.get("audio_kind"), metrics=resp.get("metrics"), gate=resp.get("gate"))
            append_jl(out, rec)
        if n % 10 == 0: print(f"[{n}/{len(rows)}]", flush=True)
    print("done", out)


def compare(split):
    import analyze_v2 as A
    rows = A.build_rows(split)
    rep = {(r["id"], r["seed"]): r for r in rows if r["system"] == "revised_hybrid" and r["mode"] == "rev"}
    live = jl(V2 / "results/e2e" / f"{split}_hybrid{TAG}.jsonl")
    same = diff = missing = 0; ex = []
    for d in live:
        k = (d["id"], d["seed"]); r = rep.get(k)
        if r is None or d.get("error"): missing += 1; continue
        ok = (d.get("text") or "") == (r["text"] or "") and d.get("outcome") == r["outcome"]
        same += ok; diff += (not ok)
        if not ok and len(ex) < 12: ex.append(dict(id=d["id"], seed=d["seed"], live=(d.get("text"), d.get("outcome")), replay=(r["text"], r["outcome"])))
    res = dict(split=split, n_live=len(live), identical_text_and_outcome=same, different=diff, missing_or_error=missing, examples=ex)
    (V2 / "results/audit" / f"B_replay_vs_live_{split}{TAG}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8"); print(json.dumps(res, ensure_ascii=False)[:600])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "compare"]); ap.add_argument("--split", required=True)
    ap.add_argument("--seeds", nargs="*", type=int, default=[11, 23, 47]); ap.add_argument("--policy", default="hybrid"); a = ap.parse_args()
    run(a.split, a.seeds, a.policy) if a.cmd == "run" else compare(a.split)
