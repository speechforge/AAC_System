#!/usr/bin/env python3
r"""Independent recount of Table 2 (success by system, condition and language; retention; error counts) from the archived scored outputs,
compared with the numbers printed in generated/tab_results.tex.  Usage: python3 numbers_check.py <scored.csv> <tab_results.tex>"""
import csv, re, sys, collections
scored, tab = sys.argv[1], sys.argv[2]
rows = [r for r in csv.DictReader(open(scored, encoding="utf-8")) if r["code_mix"] != "True" and r["overlap"] != "True"]
inst = lambda r: 2 if r["type"] in ("T5_action_object", "T6_help_person") else 1      # required concept instances per scenario
B = lambda s: s == "True"
def cell(system, cond):
    sel = [r for r in rows if r["system"] == system and r["cond"] == cond]
    per = {l: [r for r in sel if r["lang"] == l] for l in ("en", "hi", "gu", "mr")}
    succ = {l: f"{sum(B(r['success']) for r in v)}/{len(v)}" for l, v in per.items()}
    allv = sum(B(r["success"]) for r in sel)
    kept = round(sum(float(r["retention"]) * inst(r) for r in sel)); need = sum(inst(r) for r in sel)
    c = collections.Counter()
    for r in sel:
        c["pol"] += not B(r["polarity_ok"]); c["wrong"] += B(r["act_wrong"]); c["noact"] += B(r["act_missing"])
        c["added"] += B(r["unsupported"]); c["off"] += B(r["offtask"])
    return succ, f"{allv}/{len(sel)}", f"{kept}/{need}", c
t = open(tab, encoding="utf-8").read()
def row(label):
    for ln in t.splitlines():
        if label in ln: return [re.sub(r"\\textbf\{|\}|\\rowcolor\{rowtint\}|\\\\", "", x).strip() for x in ln.split("&")]
want = [("Unconstrained", "naive_qwen", "ui"), ("Ungated cascade", "llm3_pre", "ui"), ("Indic AAC Studio", "deployed", "ui"), ("Template baseline", "template_only", "ui")]
ok = True
def check(label, system, cond, printed):
    global ok
    succ, allv, kept, c = cell(system, cond)
    mine = [succ["en"], succ["hi"], succ["gu"], succ["mr"], allv, kept, str(c["pol"]), str(c["wrong"]), str(c["noact"]), str(c["added"]), str(c["off"])]
    same = mine == printed[1:12]
    ok &= same
    print(("OK   " if same else "DIFF ") + f"{label:22s} {cond:3s} recount={mine}" + ("" if same else f"\n                      printed ={printed[1:12]}"))
lines = t.splitlines()
# client block rows come first, explicit block second
cl = [l for l in lines if re.search(r"Unconstrained|Ungated cascade|\(deployed\)|Template baseline", l)]
def parse(l): return [re.sub(r"\\textbf\{|\}|\\rowcolor\{rowtint\}|\\\\", "", x).strip() for x in l.split("&")]
def system_of(label):
    return ("naive_qwen" if "Unconstrained" in label else "llm3_pre" if ("Ungated" in label or "before gate" in label) else "deployed" if "deployed" in label else "template_only")
for cond, block in (("ui", cl[:4]), ("st", cl[4:])):
    for l in block:
        p = parse(l); check(("deployed (system)" if "deployed" in p[0] else p[0]), system_of(p[0]), cond, p)
# literal join (stated in the caption, no table row)
succ, allv, kept, c = cell("literal_join", "any"); print("literal join:", allv, kept, dict(c))
print("RESULT:", "all Table 2 rows reproduce from scored.csv" if ok else "MISMATCH")
