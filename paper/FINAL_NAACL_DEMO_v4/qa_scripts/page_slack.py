#!/usr/bin/env python3
r"""Report where the main content ends and how much room is left: page of the Conclusion's last line, free height below it.
Usage: python3 page_slack.py <pdf> [page_of_conclusion_end]"""
import subprocess, re, sys
pdf = sys.argv[1]; page = sys.argv[2] if len(sys.argv) > 2 else "6"
x = subprocess.run(["pdftotext", "-bbox-layout", "-f", page, "-l", page, pdf, "-"], capture_output=True, text=True).stdout
m = re.search(r'<page width="([\d.]+)" height="([\d.]+)"', x); W, H = float(m.group(1)), float(m.group(2))
ys = {"left": [], "right": []}
for xm, ym, xM, yM, body in re.findall(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', x, flags=re.S):
    t = " ".join(re.findall(r">([^<]+)</word>", body))
    if re.fullmatch(r"\d{1,2}", t.strip()): continue
    ys["left" if float(xm) < W / 2 - 5 else "right"].append((float(yM), t))
for k, v in ys.items():
    if v: print(k, "column: last text line bottom y=%.1f of %.1f |" % max(v)[:1] + (H,)[0:0] if False else k, "last line y=%.1f |" % max(v)[0], max(v)[1][:60])
print("text block bottom is y=775.2 when a column is full (A4, ACL margins)")
