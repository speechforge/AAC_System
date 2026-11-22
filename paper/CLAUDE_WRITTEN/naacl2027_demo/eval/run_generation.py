#!/usr/bin/env python3
"""Send every unique frozen payload to the LIVE backend's POST /generate (the application entry point).
Resumable: appends to results/raw_pipeline.jsonl and skips payloads already recorded.
Usage: python run_generation.py [--limit N]"""
import json, sys, time, hashlib, pathlib, urllib.request, urllib.error
HERE = pathlib.Path(__file__).resolve().parent
CFG = json.loads((HERE / "config.json").read_text())
OUT = HERE / "results/raw_pipeline.jsonl"

def key(p): return hashlib.sha256(json.dumps(p, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]

def post(p):
    req = urllib.request.Request(CFG["endpoint"] + "/generate", data=json.dumps(p, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=CFG["request_timeout_s"]).read()); err = None
    except Exception as e:  # timeouts / HTTP errors are kept and counted as failures
        r, err = None, repr(e)
    return r, err, time.perf_counter() - t

def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    scs = [json.loads(l) for l in (HERE / CFG["scenarios"]).read_text(encoding="utf-8").splitlines() if l.strip()]
    uniq = {}
    for sc in scs:
        for cond in ("ui", "structured"):
            p = sc["payload_" + cond]; uniq.setdefault(key(p), p)
    done = set()
    if OUT.exists():
        done = {json.loads(l)["key"] for l in OUT.read_text(encoding="utf-8").splitlines() if l.strip()}
    todo = [(k, p) for k, p in uniq.items() if k not in done][:limit]
    print(f"{len(scs)} scenarios -> {len(uniq)} unique payloads; {len(done)} done; {len(todo)} to run", flush=True)
    with OUT.open("a", encoding="utf-8") as f:
        for i, (k, p) in enumerate(todo, 1):
            r, err, wall = post(p)
            rec = dict(key=k, payload=p, wall_s=round(wall, 3), error=err, ts=time.time())
            if r is not None:
                d = r.get("llm3_decision") or {}
                rec["response"] = dict(
                    text=r.get("text"), validated=r.get("validated"), fallback_used=r.get("fallback_used"),
                    semantic_score=r.get("semantic_score"), validation_data=r.get("validation_data"),
                    candidate_llm1=r.get("candidate_llm1"), candidate_llm2=r.get("candidate_llm2"),
                    llm3_decision=d.get("decision"), llm3_final_text=d.get("final_text"), llm3_edit_type=d.get("edit_type"),
                    metrics=r.get("metrics"), audio_b64_len=len(r.get("audio_b64") or ""), mode=r.get("mode"))
            f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
            if i % 10 == 0 or i == len(todo):
                print(f"[{i}/{len(todo)}] last wall={wall:.1f}s err={err}", flush=True)

if __name__ == "__main__":
    main()
