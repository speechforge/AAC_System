"""Step 10a (CPU, parallel): stream NATIVE Marathi/Gujarati text (Sangraha 'verified' + IndicCorpV2, both open without login), split into sentences,
keep short AAC-sized ones (3-12 words, script-pure, de-duplicated), drop anything identical to our AAC dev/test sentences, and split by sentence hash
into train / native-dev / native-test (held out, used only for out-of-domain perplexity).   python prep_native.py <lang> [n_sangraha_docs] [n_indiccorp_lines]"""
import sys, re, json, hashlib, time, multiprocessing as mp
from datasets import load_dataset
from lib import sents, words_of, SCRIPT
lang = sys.argv[1]; ND = int(sys.argv[2]) if len(sys.argv) > 2 else 30000; NL = int(sys.argv[3]) if len(sys.argv) > 3 else 400000
code = {"mr": ("mar", "mar_Deva"), "gu": ("guj", "guj_Gujr")}[lang]
SPLIT = re.compile(r"(?<=[.!?।॥])\s+|\n+")
pure = re.compile(SCRIPT[lang])
def clean(chunk):
    out = []
    for text in chunk:
        for s in SPLIT.split(text):
            s = s.strip()
            if not s: continue
            toks = s.split()
            if not (3 <= len(toks) <= 12): continue
            ws = words_of(s, lang)
            if len(ws) < 0.9 * len(toks) or len(ws) < 3: continue        # >10% of tokens contain no native-script letters (latin, digits, symbols)
            if re.search(r"[A-Za-z]", s): continue
            out.append(" ".join(ws))
    return out
def chunks(it, n, size=500):
    buf = []
    for i, r in enumerate(it):
        if i >= n: break
        buf.append(r["text"])
        if len(buf) == size: yield buf; buf = []
    if buf: yield buf
t0 = time.time(); allS = []; stats = {}
with mp.Pool(4) as pool:
    for name, ds, n in (("sangraha_verified", load_dataset("ai4bharat/sangraha", data_dir=f"verified/{code[0]}", split="train", streaming=True), ND),
                        ("indiccorp_v2", load_dataset("ai4bharat/IndicCorpV2", "indiccorp_v2", split=code[1], streaming=True), NL)):
        got = 0
        for res in pool.imap(clean, chunks(ds, n), chunksize=1): allS += res; got += len(res)
        stats[name] = {"items_read": n, "sentences_kept": got}; print(lang, name, stats[name], round(time.time() - t0), "s", flush=True)
seen = set(); uniq = []
for s in allS:
    if s not in seen: seen.add(s); uniq.append(s)
aac_eval = set(sents(lang, "dev") + sents(lang, "test")); n_before = len(uniq); uniq = [s for s in uniq if s not in aac_eval]
h = lambda s: int(hashlib.md5(s.encode()).hexdigest(), 16) % 50
parts = {"train": [s for s in uniq if h(s) >= 2], "dev": [s for s in uniq if h(s) == 1], "test": [s for s in uniq if h(s) == 0]}
for k, v in parts.items(): open(f"data_native/{lang}_native_{k}.txt", "w", encoding="utf-8").write("\n".join(v) + "\n")
info = {"lang": lang, "sources": stats, "after_split_dedupe": len(allS), "unique": n_before, "overlap_with_aac_dev_test_removed": n_before - len(uniq),
        "sizes": {k: len(v) for k, v in parts.items()}, "seconds": time.time() - t0,
        "note": "web/news text, NOT conversational AAC; first items of each stream (not a random sample of the corpus)"}
json.dump(info, open(f"data_native/{lang}_native_info.json", "w"), indent=1); print(info)
