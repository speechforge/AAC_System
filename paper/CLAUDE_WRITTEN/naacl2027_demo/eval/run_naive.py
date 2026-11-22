#!/usr/bin/env python3
"""Baseline B2 -- single-pass prompted Qwen2.5-0.5B-Instruct WITHOUT the proposed constraints:
same weights, dtype, greedy decoding and token budget as the deployed LLM-1, but no concept ledger, no forbidden list,
no few-shot examples, no verifier/refiner, no validator, no fallback.  Input = the symbol labels exactly as selected on the board.
Loads its own copy of the model via the application's IndicLLM class, so decoding code is identical.
Run only when the server is idle (GPU contention would not change outputs, only wall time)."""
import json, sys, pathlib, time
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "indic-generative-aac/backend"))
from llm import IndicLLM
LANG = {"en": "English", "hi": "Hindi (Devanagari script)", "gu": "Gujarati (Gujarati script)", "mr": "Marathi (Devanagari script)"}
SYSTEM = "You are an assistive communication tool. Turn the selected symbols into one short, natural sentence in {lang}. Output only the sentence."
OUT = HERE / "results/raw_naive.jsonl"
llm = IndicLLM()
scs = [json.loads(l) for l in (HERE / "fixtures/scenarios.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
done = {json.loads(l)["id"] for l in OUT.read_text(encoding="utf-8").splitlines()} if OUT.exists() else set()
with OUT.open("a", encoding="utf-8") as f:
    for i, sc in enumerate(scs, 1):
        if sc["id"] in done: continue
        lang = "Hinglish (Hindi in Devanagari mixed with English words)" if sc["code_mix"] else LANG[sc["lang"]]
        msgs = [{"role": "system", "content": SYSTEM.format(lang=lang)}, {"role": "user", "content": "Selected symbols: " + ", ".join(sc["labels"])}]
        t = time.perf_counter(); text, m = llm._call_llm(msgs, max_new_tokens=75, temperature=0.01)
        f.write(json.dumps(dict(id=sc["id"], text=text, tokens_out=m["tokens_out"], latency_s=m["latency"], wall_s=round(time.perf_counter() - t, 3)), ensure_ascii=False) + "\n"); f.flush()
        if i % 20 == 0: print(f"[{i}/{len(scs)}]", flush=True)
print("done")
