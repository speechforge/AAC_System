#!/usr/bin/env python3
"""Extract the symbol-board vocabulary (concept id -> localized labels) from the app's own source.
Source: indic-generative-aac/frontend/index.html  (SYMBOL_DATABASE).  No network, no model."""
import re, json, hashlib, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[3]          # repo root
SRC = ROOT / "indic-generative-aac/frontend/index.html"
OUT = pathlib.Path(__file__).resolve().parent / "fixtures/board_vocab.json"
txt = SRC.read_text(encoding="utf-8")
start = txt.index("const SYMBOL_DATABASE = {")
end = txt.index("// ─── TOP 5 HIGH-PEAKED WORDS")
block = txt[start:end]
cat_re = re.compile(r"^\s{6}(\w+): \[", re.M)
sym_re = re.compile(r"\{ e: '([^']*)', k: '([^']+)', labels: \{ en: '([^']*)', hi: '([^']*)', gu: '([^']*)', mr: '([^']*)' \} \}")
cats = list(cat_re.finditer(block))
vocab = {}
for i, m in enumerate(cats):
    seg = block[m.end(): cats[i+1].start() if i+1 < len(cats) else len(block)]
    vocab[m.group(1)] = [dict(emoji=e, id=k, en=en, hi=hi, gu=gu, mr=mr) for e, k, en, hi, gu, mr in sym_re.findall(seg)]
meta = dict(source=str(SRC.relative_to(ROOT)), source_sha256=hashlib.sha256(SRC.read_bytes()).hexdigest(),
            n_categories=len(vocab), n_symbols=sum(len(v) for v in vocab.values()))
OUT.write_text(json.dumps(dict(meta=meta, vocab=vocab), ensure_ascii=False, indent=1), encoding="utf-8")
print(meta); print({k: len(v) for k, v in vocab.items()})
