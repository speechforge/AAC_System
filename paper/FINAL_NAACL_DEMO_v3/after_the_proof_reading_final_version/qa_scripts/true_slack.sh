#!/usr/bin/env bash
# True spare space at the end of the main content and of the appendix: build a scratch copy with ragged-bottom columns (the template is flush-bottom,
# which hides slack because it stretches glue) and report how many text lines are free below the last line of the Conclusion (page 6) and the appendix (last page).
# Usage: true_slack.sh <latex_source_dir>
set -euo pipefail
SRC="$(cd "$1" && pwd)"; TMP="$(mktemp -d)"; cp -r "$SRC"/. "$TMP"/
export TECTONIC="${TECTONIC:-/usr/lib/chatgpt/resources/plugins/openai-bundled/plugins/latex/bin/tectonic}"
sed -i 's/\\begin{document}/\\begin{document}\\raggedbottom/' "$TMP/main.tex"
( cd "$TMP" && ./build.sh >/dev/null 2>&1 )
python3 - "$TMP/main.pdf" <<'PY'
import subprocess, re, sys
pdf = sys.argv[1]
n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
def last_y(pg):
    x = subprocess.run(["pdftotext", "-bbox-layout", "-f", str(pg), "-l", str(pg), pdf, "-"], capture_output=True, text=True).stdout
    W = float(re.search(r'<page width="([\d.]+)"', x).group(1)); cols = {"left": [], "right": []}
    for xm, ym, xM, yM, body in re.findall(r'<line xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</line>', x, flags=re.S):
        t = " ".join(re.findall(r">([^<]+)</word>", body))
        if re.fullmatch(r"\d{1,2}", t.strip()): continue
        cols["left" if float(xm) < W / 2 - 5 else "right"].append((float(yM), t))
    return {k: max(v) for k, v in cols.items() if v}
for label, pg in (("main content (Conclusion) page 6", 6), ("appendix last page", n)):
    r = last_y(pg)
    print(label, {k: "%.1f spare lines (ends: %s)" % ((775.2 - y) / 13.6, t[:32]) for k, (y, t) in r.items()})
PY
rm -rf "$TMP"
