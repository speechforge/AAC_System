#!/usr/bin/env python3
"""Collect candidate STREAMS (attempt 1, and attempt 2 when a gate rejects attempt 1) from the archived (G0) and revised (G1) cascades
on identical payloads, with ONE shared Qwen2.5-0.5B-Instruct copy (same revision as the archived run; fp16 on the GPU).
  G0 = archived llm.py (archived_system/), payload turned into a context exactly as the archived app.py did.
  G1 = revised llm.py (working tree), payload normalised by pipeline.normalize_request (act and polarity as separate fields).
Payload modes: gold (explicit gold fields; the diagnostic upper bound for input interpretation) | orig (captured from the original client)
| rev (captured from the revised client).  Every generation call is cached by (messages, decoding, seed) in results/streams/cache_*.jsonl:
identical prompts of different jobs are generated once, and a re-run reproduces the stream exactly.
Sampling path (English / code-mixed LLM-1, temperature 0.1) is seeded: seed + 1000 * attempt.  Indic few-shot path is greedy (no seed).
Usage: python run_streams.py --split holdout --jobs G0:orig G0:gold G1:rev G1:gold --seeds 11 23 47 [--shard 0/2] [--limit N]"""
import argparse, hashlib, json, os, sys, time, random
import torch
from common import *

sys.path.insert(0, str(REPO / "backend"))
import aac_lexicon as L, pipeline as P, semantic as SEM
from llm import IndicLLM as LLM_REV
LLM_ARCH = load_module("llm_archived", ARCH_SYS / "backend/llm.py").IndicLLM
SEM_ARCH = load_module("semantic_archived", ARCH_SYS / "backend/semantic.py").SemanticValidator
OUT = V2 / "results/streams"; OUT.mkdir(parents=True, exist_ok=True)
ACT_MAP = dict(request="REQUEST", feeling="FEELING", feeling_request="FEELING_REQUEST", greeting="GREETING", ambiguous="UNKNOWN")


class Cache:
    def __init__(self, shard):
        self.mem, self.path = {}, OUT / f"cache_{os.environ.get('CACHE_TAG', 'main')}_{shard}.jsonl"
        for p in OUT.glob("cache_*.jsonl"):
            for l in p.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    r = json.loads(l); self.mem[r["k"]] = r["v"]
    def get(self, k): return self.mem.get(k)
    def put(self, k, v):
        self.mem[k] = v
        with open(self.path, "a", encoding="utf-8") as f: f.write(json.dumps(dict(k=k, v=v), ensure_ascii=False) + "\n")


def build_models(cache):
    base = LLM_REV()
    raw_call = base._call_llm
    state = dict(seed=None)
    def cached(messages, max_new_tokens=80, temperature=0.01):
        sampling = temperature > 0.05
        key = hashlib.sha256(json.dumps([messages, max_new_tokens, temperature, state["seed"] if sampling else None], ensure_ascii=False).encode()).hexdigest()
        hit = cache.get(key)
        if hit is not None:
            return hit["text"], dict(hit["metrics"], cached=True)
        text, m = raw_call(messages, max_new_tokens=max_new_tokens, temperature=temperature)
        cache.put(key, dict(text=text, metrics=m))
        return text, m
    base._call_llm = cached
    arch = object.__new__(LLM_ARCH)
    arch.device, arch.tokenizer, arch.model = base.device, base.tokenizer, base.model
    arch._call_llm = cached
    return base, arch, state


def legacy_context(payload):
    intent = (payload.get("intent") or "REQUEST")
    return {"intent": intent, "actor": payload.get("actor", "USER"), "entities": payload["entities"], "attributes": [], "relations": [],
            "temporal_state": None, "location": None, "people": [], "actions": [],
            "negation": bool(payload.get("negation")) or intent.upper() == "NEGATION" or "NOT" in intent.upper(), "speaker_role": "USER"}


def gold_payload(sc, gen):
    """Explicit gold fields: act and polarity from the independent gold annotation; 'No' removed from the symbols."""
    lang = sc["lang"]
    labs = [(el["typed"] if "typed" in el else L.BOARD[el["cid"]][lang]) for el in sc["seq"] if el.get("cid") not in ("NO", "WANT", "PLEASE", "YES", "ME")]
    ids = [(None if "typed" in el else el["cid"]) for el in sc["seq"] if el.get("cid") not in ("NO", "WANT", "PLEASE", "YES", "ME")]
    base = dict(entities=labs, negation=bool(sc["gold_neg"]), language=lang, code_mix=bool(sc.get("code_mix")), generation_mode="dual")
    act = ACT_MAP[sc["gold_act"]]
    if gen == "G0":
        return dict(base, intent=("STATEMENT" if act in ("FEELING",) else "REQUEST"))
    return dict(base, act=act, act_source="client", concept_ids=ids, intent=P.ACT_TO_INTENT[act])


def attempt(gen_obj, ctx, lang, code_mix, seed, k, state, is_rev):
    state["seed"] = (seed + 1000 * k) if seed is not None else None
    if seed is not None:
        torch.manual_seed(state["seed"]); torch.cuda.manual_seed_all(state["seed"])
    t0 = time.time()
    try:
        gen, sctx, ledger, c1, c2, dec, tel = gen_obj.generate_sentence(ctx, language=lang, code_mix=code_mix, mode="dual")
        return dict(k=k, text=gen, llm1=c1, llm2=c2, llm3_text=dec.get("final_text"), llm3_decision=dec.get("decision"), edit_type=dec.get("edit_type"),
                    latency=tel.get("latencies", {}).get("pipeline_llm_total"), ledger=ledger, wall=round(time.time() - t0, 3))
    except Exception as e:
        return dict(k=k, text=None, error=repr(e), wall=round(time.time() - t0, 3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True); ap.add_argument("--jobs", nargs="+", required=True)
    ap.add_argument("--seeds", nargs="*", type=int, default=[11]); ap.add_argument("--cross-seed", type=int, default=11)
    ap.add_argument("--shard", default="0/1"); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--tag", default="")
    ap.add_argument("--det-sample", type=float, default=0.10)
    a = ap.parse_args()
    si, sn = map(int, a.shard.split("/"))
    rows = [r for r in jl(V2 / "fixtures" / a.split / "scenarios.jsonl") if not r.get("code_mix") or a.split == "legacy"]
    if a.limit: rows = rows[:a.limit]
    caps = {m: {r["id"]: r for r in jl(V2 / "results/payloads" / f"{('original' if m == 'orig' else 'revised')}_{a.split}.jsonl")} for m in ("orig", "rev")}
    jobs = []
    for r in rows:
        for j in a.jobs:
            gen, mode = j.split(":")
            seeds = (a.seeds if mode != "cross" else [a.cross_seed]) if (r["lang"] == "en" or r.get("code_mix")) else [None]
            for sd in seeds:
                jobs.append((r, gen, mode, sd))
    jobs = [j for i, j in enumerate(jobs) if i % sn == si]
    cache = Cache(f"{si}of{sn}")
    base, arch, state = build_models(cache)
    V1, V0 = SEM.SemanticValidator(None), SEM_ARCH(None)
    out_path = OUT / f"{a.split}{('_' + a.tag) if a.tag else ''}_shard{si}of{sn}.jsonl"
    done = {(d["id"], d["gen"], d["mode"], d["seed"]) for d in jl(out_path)}
    rng = random.Random(20261113 + si)
    print(f"{len(jobs)} jobs in shard {si}/{sn}; {len(done)} already done; cache {len(cache.mem)} entries", flush=True)
    t_start = time.time()
    for n, (r, gen, mode, sd) in enumerate(jobs, 1):
        key = (r["id"], gen, mode, sd)
        if key in done: continue
        lang, cm = r["lang"], bool(r.get("code_mix"))
        if mode == "gold": payload = gold_payload(r, gen)
        elif cm and mode in ("orig", "cross"): payload = r.get("archived_payload_ui")
        else:
            c = caps["orig" if mode in ("orig", "cross") else "rev"].get(r["id"]) if not cm else {"payload": payload}
            if c is None or not c.get("payload"):
                append_jl(out_path, dict(id=r["id"], gen=gen, mode=mode, seed=sd, error="no_payload")); continue
            payload = c["payload"]
        payload = dict(payload, language=lang, code_mix=cm)
        ctx0 = legacy_context(payload); ctx1 = P.normalize_request(payload)
        gobj, ctx, is_rev = (base, ctx1, True) if gen == "G1" else (arch, ctx0, False)
        if ctx1["act"] == "UNKNOWN" and gen == "G1":                       # clarification path: no generation
            append_jl(out_path, dict(id=r["id"], lang=lang, split=a.split, gen=gen, mode=mode, seed=sd, payload=payload, attempts=[], note="clarification_no_generation")); continue
        atts = [attempt(gobj, ctx, lang, cm, sd, 0, state, is_rev)]
        rej = lambda at: (at.get("text") is None) or (not V0.validate(ctx0, at.get("ledger") or {"forbidden": []}, at["text"], lang)[0]) or (not V1.validate(ctx1, {}, at["text"], lang)[0])
        if rej(atts[0]) or (sd is None and lang != "en" and rng.random() < a.det_sample):
            atts.append(attempt(gobj, ctx, lang, cm, sd, 1, state, is_rev))
        append_jl(out_path, dict(id=r["id"], lang=lang, split=a.split, gen=gen, mode=mode, seed=sd, payload=payload, attempts=atts))
        if n % 10 == 0:
            el = time.time() - t_start
            print(f"[{n}/{len(jobs)}] {el/60:.1f} min elapsed, cache {len(cache.mem)}", flush=True)
    print("done", out_path)


if __name__ == "__main__":
    main()
