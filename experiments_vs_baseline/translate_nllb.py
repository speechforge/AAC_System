"""Machine-translate the English splits to Marathi/Gujarati with cached NLLB-200 (no native gu/mr AAC corpus exists)."""
import json, glob, os, torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
name = "facebook/nllb-200-distilled-600M"
tok = AutoTokenizer.from_pretrained(name, src_lang="eng_Latn", local_files_only=True)
m = AutoModelForSeq2SeqLM.from_pretrained(name, torch_dtype=torch.float16, local_files_only=True).cuda().eval()
for code, tag in (("mar_Deva", "mr"), ("guj_Gujr", "gu")):
    for f in sorted(glob.glob(f"{D}/en_*_*.json")):
        out = f.replace("/en_", f"/{tag}_")
        if os.path.exists(out): continue
        src = json.load(open(f, encoding="utf-8")); res = []
        for i in range(0, len(src), 16):
            b = tok(src[i:i+16], return_tensors="pt", padding=True, truncation=True, max_length=96).to("cuda")
            with torch.no_grad():
                g = m.generate(**b, forced_bos_token_id=tok.convert_tokens_to_ids(code), num_beams=4, max_new_tokens=96)
            res += tok.batch_decode(g, skip_special_tokens=True)
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0); print(out, len(res), flush=True)
