"""Step 2a: tokenizer fertility (tokens per word, lower = better) of candidate base LMs on our train text."""
import json
from lib import *
from transformers import AutoTokenizer
names = ["facebook/opt-125m", "Qwen/Qwen2.5-0.5B-Instruct", "bigscience/bloom-560m", "facebook/xglm-564M", "google/mt5-small", "google/byt5-small"]
out = {}
for n in names:
    try: tok = AutoTokenizer.from_pretrained(n)
    except Exception as e: print(n, "FAILED", str(e)[:80]); continue
    out[n] = {}
    for l in ("en", "hi", "mr", "gu"):
        ss = sents(l, "train")[:500]; nw = sum(len(s.split()) for s in ss); nt = sum(len(tok(s, add_special_tokens=False)["input_ids"]) for s in ss)
        out[n][l] = nt / nw
    print(n, {k: round(v, 2) for k, v in out[n].items()}, flush=True)
json.dump(out, open("results/step2_fertility.json", "w"), indent=1)
