#!/usr/bin/env python3
"""Matched one-pass Qwen comparator: same model revision, same chat template, same output language, same input information as the repaired
hybrid receives (act, polarity, concepts), decoding as the realiser path of that language (English: temperature 0.1 with the three seeds,
max_new_tokens 60; Indic: greedy, max_new_tokens 75).  It asks for ONE first-person sentence in the target language that preserves the message.
No gate, no fallback, no examples.  Inputs: mode 'rev' (fields taken from the payload captured from the revised client) or 'gold' (explicit gold fields).
Usage: python run_onepass.py --split holdout --modes rev gold --seeds 11 23 47"""
import argparse, sys, time
from common import *
import run_streams as RS
import aac_lexicon as L, pipeline as P

LANG_NAME = {"en": "English", "hi": "Hindi (Devanagari script)", "gu": "Gujarati (Gujarati script)", "mr": "Marathi (Devanagari script)"}
ACT_TEXT = {"REQUEST": "the speaker asks for or wants something (or does not want it, see polarity)",
            "FEELING": "the speaker says how they feel", "FEELING_REQUEST": "the speaker says how they feel and also asks for something",
            "GREETING": "the speaker greets someone", "QUESTION": "the speaker asks a question", "UNKNOWN": "not specified"}
SYSTEM = ("You are an assistive communication tool for a person who communicates with symbols. Write ONE first-person sentence in {lang} "
          "that expresses the message below. Keep every selected concept, keep whether it is wanted or not wanted, and keep who is speaking. "
          "Add nothing else. Output only the sentence.")


def fields(payload):
    c = P.normalize_request(payload)
    return c["act"], c["negation"], c["entities"]


def messages(lang, act, neg, ents):
    user = f"Message type: {ACT_TEXT[act]}\nPolarity: {'negated (the speaker does NOT want / is NOT)' if neg else 'affirmed'}\nSelected concepts: {', '.join(ents)}"
    return [dict(role="system", content=SYSTEM.format(lang=LANG_NAME[lang])), dict(role="user", content=user)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True); ap.add_argument("--modes", nargs="+", default=["rev", "gold"])
    ap.add_argument("--seeds", nargs="*", type=int, default=[11, 23, 47]); ap.add_argument("--shard", default="0/1"); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    si, sn = map(int, a.shard.split("/"))
    rows = [r for r in jl(V2 / "fixtures" / a.split / "scenarios.jsonl") if not r.get("code_mix") or a.split == "legacy"]
    if a.limit: rows = rows[:a.limit]
    caps = {r["id"]: r for r in jl(V2 / "results/payloads" / f"revised_{a.split}.jsonl")}
    cache = RS.Cache(f"op{si}of{sn}")
    base, _, state = RS.build_models(cache)
    out = RS.OUT / f"onepass_{a.split}_shard{si}of{sn}.jsonl"
    done = {(d["id"], d["mode"], d["seed"]) for d in jl(out)}
    jobs = [(r, m, sd) for r in rows for m in a.modes for sd in (a.seeds if r["lang"] == "en" else [None])]
    jobs = [j for i, j in enumerate(jobs) if i % sn == si]
    print(len(jobs), "one-pass jobs", flush=True)
    for n, (r, m, sd) in enumerate(jobs, 1):
        if (r["id"], m, sd) in done: continue
        payload = RS.gold_payload(r, "G1") if m == "gold" else (caps.get(r["id"]) or {}).get("payload")
        if not payload:
            append_jl(out, dict(id=r["id"], mode=m, seed=sd, error="no_payload")); continue
        payload = dict(payload, language=r["lang"])
        act, neg, ents = fields(payload)
        msgs = messages(r["lang"], act, neg, ents)
        state["seed"] = sd
        if sd is not None:
            import torch; torch.manual_seed(sd); torch.cuda.manual_seed_all(sd)
        mx, temp = (60, 0.1) if r["lang"] == "en" else (75, 0.01)
        t0 = time.time()
        try:
            text, met = base._call_llm(msgs, max_new_tokens=mx, temperature=temp); err = None
        except Exception as e:
            text, met, err = None, {}, repr(e)
        append_jl(out, dict(id=r["id"], lang=r["lang"], split=a.split, mode=m, seed=sd, act=act, negation=neg, entities=ents, text=text,
                            latency=met.get("latency"), wall=round(time.time() - t0, 3), error=err, cached=bool(met.get("cached"))))
        if n % 20 == 0: print(f"[{n}/{len(jobs)}]", flush=True)


if __name__ == "__main__":
    main()
