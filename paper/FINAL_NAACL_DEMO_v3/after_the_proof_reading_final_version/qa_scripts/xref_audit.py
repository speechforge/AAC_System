#!/usr/bin/env python3
r"""Cross-reference audit: every figure, table and equation label must be cited in the text, every \ref must resolve,
and every \cite key must exist in the bibliography.  Usage: python3 xref_audit.py <latex_source_dir>"""
import re, sys, glob, pathlib
root = pathlib.Path(sys.argv[1])
files = [root / "main.tex"] + sorted((root / "sections").glob("*.tex")) + sorted((root / "generated").glob("*.tex"))
txt = {f.name: f.read_text(encoding="utf-8") for f in files}
labels = {}
for n, t in txt.items():
    for m in re.finditer(r"\\label\{((?:fig|tab|eq|sec|app):[^}]+)\}", t): labels[m.group(1)] = n
refs = {}
for n, t in txt.items():
    for m in re.finditer(r"\\(?:ref|eqref)\{([^}]+)\}", t): refs.setdefault(m.group(1), []).append(n)
bad = 0
for l, n in sorted(labels.items()):
    kind = l.split(":")[0]
    cited = l in refs
    flag = "" if cited else ("   <-- NOT CITED" if kind in ("fig", "tab", "eq") else "   (section label, optional)")
    if not cited and kind in ("fig", "tab", "eq"): bad += 1
    print(f"{l:22s} {n:22s} cited in: {sorted(set(refs.get(l, [])))}{flag}")
unres = sorted(r for r in refs if r not in labels)
print("unresolved \\ref:", unres)
bib = (root / "references.bib").read_text(encoding="utf-8")
keys = set(re.findall(r"@\w+\{([^,\s]+)\s*,", bib))
cited_keys = set()
for t in txt.values():
    for m in re.finditer(r"\\cite[a-z]*\*?(?:\[[^\]]*\])*\{([^}]+)\}", t):
        cited_keys.update(k.strip() for k in m.group(1).split(","))
print("cite keys missing from bib:", sorted(cited_keys - keys))
print("bib entries never cited   :", sorted(keys - cited_keys))
print("RESULT:", "OK" if (bad == 0 and not unres and not (cited_keys - keys)) else f"{bad} uncited float(s)/eq, {len(unres)} unresolved ref(s)")
