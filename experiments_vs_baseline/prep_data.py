"""Build deterministic train/dev/test splits (by conversation) for EN and HI AAC datasets."""
import glob, json, hashlib, re, os, random, collections
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(os.path.dirname(__file__), "data"); os.makedirs(OUT, exist_ok=True)

def conv_id(conv):
    # original/augmented/transformed files share the same conversations -> same id (first caregiver turn)
    return hashlib.md5(conv[0]["utterance"].strip().lower().encode()).hexdigest() if conv else None

def load(lang):
    d = "english_AAC_Dataset" if lang == "en" else "hindi_AAC_Dataset"
    convs = {}
    for f in sorted(glob.glob(f"{ROOT}/{d}/*.jsonl")):
        if "openai_batch" in f or "metadata" in f: continue
        for line in open(f, encoding="utf-8"):
            if not line.strip(): continue
            try: c = json.loads(line).get("conversation", [])
            except Exception: continue
            if not c: continue
            key = hashlib.md5(c[0].get("utterance", "").encode()).hexdigest()
            for t in c:
                txt = t.get("utterance_intended") or t.get("utterance", "")
                convs.setdefault(key, set()).add((("aac" if t.get("is_aac_user") else "care"), txt.strip()))
    return convs

def split_of(key):
    h = int(key[:8], 16) % 100
    return "test" if h < 20 else "dev" if h < 30 else "train"

stats = {}
for lang in ("en", "hi"):
    convs = load(lang)
    buckets = collections.defaultdict(lambda: collections.defaultdict(set))
    for key, turns in convs.items():
        sp = split_of(key)
        for role, txt in turns:
            if txt: buckets[sp][role].add(txt)
    # remove train sentences that also appear verbatim in test/dev (leak guard)
    heldout = {t for sp in ("test", "dev") for r in buckets[sp] for t in buckets[sp][r]}
    for r in list(buckets["train"]): buckets["train"][r] -= heldout
    for sp in buckets:
        for role in buckets[sp]:
            L = sorted(buckets[sp][role])
            json.dump(L, open(f"{OUT}/{lang}_{sp}_{role}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
            stats[f"{lang}_{sp}_{role}"] = len(L)
    stats[f"{lang}_conversations"] = len(convs)
print(json.dumps(stats, indent=1))
