#!/usr/bin/env python3
r"""Check that every Hindi/Marathi/Gujarati string typeset with \hi{} or \gu{} is recoverable, in the same order, from the PDF text
(the 'चा हए' extraction damage), and that the three water sentences are exact.  Usage: python3 native_text_check.py <latex_source_dir> <pdf>"""
import re, sys, glob, subprocess, unicodedata, pathlib
root = pathlib.Path(sys.argv[1]); pdf = sys.argv[2]
tex = "".join(f.read_text(encoding="utf-8") + "\n" for f in [root / "main.tex", *sorted((root / "sections").glob("*.tex")), *sorted((root / "generated").glob("*.tex"))])
def spans(cmd):
    out, i = [], 0
    while True:
        j = tex.find("\\" + cmd + "{", i)
        if j < 0: break
        k = j + len(cmd) + 2; d = 1; s = k
        while d and k < len(tex):
            d += (tex[k] == "{") - (tex[k] == "}"); k += 1
        out.append(tex[s:k - 1]); i = k
    return out
def clean(t):
    t = re.sub(r"\\(sel|kept|bad)\{", "{", t); t = re.sub(r"[{}]", "", t); t = re.sub(r"\\[a-zA-Z]+", "", t)
    return re.sub(r"\s+", " ", t).strip()
native = sorted({clean(t) for t in spans("hi") + spans("gu") if re.search(r"[\u0900-\u0AFF]", t)})
raw = subprocess.run(["pdftotext", "-raw", pdf, "-"], capture_output=True, text=True).stdout
flat = re.sub(r"\s+", "", unicodedata.normalize("NFC", raw))
miss = [n for n in native if re.sub(r"\s+", "", unicodedata.normalize("NFC", n)) not in flat]
print(f"native strings in source: {len(native)}; not recoverable from PDF text: {len(miss)}")
for m in miss: print("  MISSING:", m)
for key in ["मुझे पानी चाहिए।", "મને પાણી જોઈએ છે.", "मला पाणी हवे आहे."]:
    print(key, "->", "exact in PDF text" if re.sub(r"\s+", "", key) in flat else "NOT FOUND")
print('damaged form "चा हए" present in PDF text:', "चा हए" in raw)
