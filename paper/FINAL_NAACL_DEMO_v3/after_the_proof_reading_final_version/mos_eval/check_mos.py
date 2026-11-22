#!/usr/bin/env python3
"""Independent recount of the MOS table: every number in generated/tab_mos.tex must equal the mean (or standard deviation) recomputed from
mos_scores.csv, the stand-in clips must be exactly the 175 deployed sentences of scored.csv, and every wav must exist and be non-empty.
Usage: check_mos.py [path/to/tab_mos.tex]"""
import pathlib, re, sys
import numpy as np, pandas as pd, soundfile as sf

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
tex = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else HERE.parent / "latex_source_v3/generated/tab_mos.tex").read_text()
d = pd.read_csv(HERE / "mos_scores.csv", keep_default_na=False)
sc = pd.read_csv(ROOT / "paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results/scored.csv")
sc = sc[(sc.system == "deployed") & (sc.cond == "ui") & (~sc.overlap) & (~sc.code_mix)]
bad = []
st = d[d.group == "standin"]
if sorted(st["id"]) != sorted(sc["id"]): bad.append("stand-in ids differ from the 175 deployed scenarios")
txt = sc.set_index("id").text.to_dict()
if any(txt[i] != t for i, t in zip(st["id"], st["text"])): bad.append("stand-in text differs from scored.csv")
for f in d.file:
    info = sf.info(HERE / "audio" / f)
    if info.frames < 1000: bad.append("clip too short: " + f)
if d[["utmos", "nisqa_mos"]].isna().any().any(): bad.append("missing score")
rows = {m: re.findall(r"[-\d.]+(?: \([\d.]+\))?", re.sub(r"\\bad\{([^}]*)\}", r"\1", line.split("&", 1)[1])) for m, line in
        ((m, l) for l in tex.splitlines() for m in ("utmos", "nisqa") if l.replace("\\rowcolor{rowtint}", "").startswith("\\" + m))}
def cell(g, col, sd): return f"{g[col].mean():.2f}" + (f" ({g[col].std():.2f})" if sd else "")
groups = [d[d.group == "placeholder"], d[(d.group == "reference") & (d.lang == "en")], d[(d.group == "reference") & (d.lang == "mr")], d[d.id == "PAN_F_HAPPY_00001"]] + [st[st.lang == l] for l in ("en", "hi", "gu", "mr")]
for m, col in (("utmos", "utmos"), ("nisqa", "nisqa_mos")):
    want = [cell(g, col, i >= 4) for i, g in enumerate(groups)]
    got = rows[m][:8]
    if want != got: bad.append(f"{m}: table {got} != recount {want}")
print("MOS table recount:", "OK (8 columns x 2 metrics match; 175 stand-in sentences = deployed scenarios; %d clips)" % len(d) if not bad else "PROBLEMS " + "; ".join(bad))
sys.exit(1 if bad else 0)
