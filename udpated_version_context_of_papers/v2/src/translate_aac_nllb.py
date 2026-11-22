#!/usr/bin/env python3
"""Machine-translate the English AAC dialogues (3 batches x transformed/augmented, 600 source conversations) into Gujarati and Marathi with
NLLB-200 (facebook/nllb-200-distilled-600M, beam 4, fp16), mirroring how the Hindi dialogues were produced (machine translation of the English ones).
Only the fields the next-word predictor reads are translated: each turn's `utterance` and `utterance_intended`.  Structure, speakers and the
AAC-user flag are copied from the English row so the source-conversation split of the evaluation is identical across languages.
Output: gujarati_AAC_Dataset/ and marathi_AAC_Dataset/ (repository root), files batch_output_<loc>_<batch>_{transformed,augmented}.jsonl, plus
results/audit/E_nllb_translation_log.json (model, decoding, counts, samples).  Run on the PC (GPU)."""
import json, pathlib, sys, time
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

ROOT = pathlib.Path("/home/linux/Documents/aac_system_november_11/AAC_System_merged")
BATCHES = ["20250513_215220", "20250514_123555", "20250515_080705"]
TARGETS = {"gu": ("guj_Gujr", "gujarati_AAC_Dataset", "gu-IN"), "mr": ("mar_Deva", "marathi_AAC_Dataset", "mr-IN")}
NAME = "facebook/nllb-200-distilled-600M"

src = {}
for b in BATCHES:
    for kind in ("transformed", "augmented"):
        rows = [json.loads(l) for l in (ROOT / "english_AAC_Dataset" / f"batch_output_en-US_{b}_{kind}.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        src[(b, kind)] = rows
strings = sorted({t.get(k) for rows in src.values() for r in rows for t in r["conversation"] for k in ("utterance", "utterance_intended") if t.get(k)})
print(len(strings), "unique English strings", flush=True)
tok = AutoTokenizer.from_pretrained(NAME, src_lang="eng_Latn")
model = AutoModelForSeq2SeqLM.from_pretrained(NAME, torch_dtype=torch.float16).cuda().eval()
log = dict(model=NAME, decoding="beam 4, max_new_tokens 64, fp16", n_unique_strings=len(strings), languages={})
for lg, (code, dname, loc) in TARGETS.items():
    t0 = time.time(); tr = {}
    order = sorted(strings, key=len)
    for i in range(0, len(order), 48):
        batch = order[i:i + 48]
        enc = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=96).to("cuda")
        with torch.no_grad():
            out = model.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids(code), num_beams=4, max_new_tokens=64)
        for s, o in zip(batch, tok.batch_decode(out, skip_special_tokens=True)):
            tr[s] = o.strip()
        if (i // 48) % 20 == 0: print(lg, i, "/", len(order), f"{time.time()-t0:.0f}s", flush=True)
    d = ROOT / dname; d.mkdir(exist_ok=True)
    for (b, kind), rows in src.items():
        out_rows = []
        for r in rows:
            nr = dict(r); conv = []
            for t in r["conversation"]:
                nt = {k: v for k, v in t.items() if not k.startswith("noisy") and k not in ("minimally_corrected", "fully_corrected")}
                for k in ("utterance", "utterance_intended"):
                    if t.get(k): nt[k] = tr[t[k]]
                conv.append(nt)
            nr["conversation"] = conv; nr.pop("scene", None); out_rows.append(nr)
        (d / f"batch_output_{loc}_{b}_{kind}.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in out_rows) + "\n", encoding="utf-8")
    ex = [(s, tr[s]) for s in strings[::600][:6]]
    log["languages"][lg] = dict(seconds=round(time.time() - t0), samples=ex)
    print(lg, "done", log["languages"][lg]["seconds"], "s", ex[:3], flush=True)
(ROOT / "udpated_version_context_of_papers/v2/results/audit/E_nllb_translation_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
