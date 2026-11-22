import json, os, textwrap
R = lambda p: json.load(open(f"results/{p}")) if os.path.exists(f"results/{p}") else None
main = {l: R(f"main_{l}.json") for l in ("en", "hi", "mr", "gu")}
llm, gen = R("llm_en.json"), R("gen.json")
abl = {l: R(f"ablate_{l}.json") for l in ("en", "hi", "mr", "gu")}
f1 = lambda x: f"{x:.1f}"; f2 = lambda x: f"{x:.2f}"
L = []; P = L.append
def table(head, rows, widths=None):
    cols = list(zip(*([head] + rows))); w = [max(len(str(c)) for c in col) for col in cols]
    P("  " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(head)))
    P("  " + "-+-".join("-" * x for x in w))
    for r in rows: P("  " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)))
    P("")
exec(open("report_text.py").read())
open("RESULTS_vs_baseline.txt", "w", encoding="utf-8").write("\n".join(L))
print("\n".join(L))
