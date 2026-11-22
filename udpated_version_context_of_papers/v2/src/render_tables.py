#!/usr/bin/env python3
"""Fill the <!--TABLE:name--> markers of FINAL_CONTEXT.template.md with markdown tables rendered from results/tables and results/audit, so no number in a table is typed by hand.
Usage: python render_tables.py  ->  ../FINAL_CONTEXT.md"""
import csv, json, re
from common import *

T = V2 / "results/tables"
SYS_NAME = {"archived_deployed": "archived system (deployed)", "archived_llm1_stage": "archived few-shot realiser alone (LLM-1 stage)", "revised_llm1_stage": "repaired few-shot realiser alone (LLM-1 stage)", "archived_unconstrained_prompt": "archived unconstrained prompt (historical diagnostic)", "cascade_ungated_first": "archived cascade, no gate (first candidate)", "cascade_ungated_last": "archived cascade, no gate (last candidate)",
            "gate_only_v1": "archived candidates, revised gate, archived template", "revised_cascade_first": "revised cascade, no gate (first candidate)", "revised_cascade_last": "revised cascade, no gate (last candidate)",
            "revised_hybrid": "revised hybrid", "template_archived": "archived template alone", "template_revised": "repaired template alone", "onepass": "matched one-pass Qwen prompt"}
MODE_NAME = {"orig": "original browser", "rev": "repaired browser", "gold": "explicit gold fields", "cross": "original-browser payload into repaired realiser"}


def md(rows, cols, heads=None):
    heads = heads or cols
    out = ["| " + " | ".join(heads) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows: out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(out)


def csvrows(p): return list(csv.DictReader(open(p, encoding="utf-8"))) if p.exists() else []


def t1(split):
    rows = csvrows(T / f"T1_success_{split}.csv"); out = []
    for r in rows:
        def cell(tag):
            if not r.get(f"{tag}_n"): return ""
            return f"{float(r[f'{tag}_k']):.1f}/{r[f'{tag}_n']} ({r[f'{tag}_rate']}%)"
        out.append(dict(system=SYS_NAME.get(r["system"], r["system"]), mode=MODE_NAME.get(r["mode"], r["mode"]), en=cell("en"), hi=cell("hi"), gu=cell("gu"), mr=cell("mr"),
                        pooled=cell("ALL"), ci=r.get("ALL_ci", "")))
    return md(out, ["system", "mode", "en", "hi", "gu", "mr", "pooled", "ci"], ["System", "Input", "EN", "HI", "GU", "MR", "Pooled k/n (rate)", "95% CI (group bootstrap)"])


def t2(split):
    rows = [r for r in csvrows(T / f"T2_paired_{split}.csv")]; out = []
    for r in rows:
        if r["lang"] == "ALL":                       # pooled rows here; per-language rows are in results/tables/T2_paired_<split>.csv
            out.append(dict(comparison=r["comparison"], lang=r["lang"], n=r["n_items"], groups=r["n_groups"], diff=r["diff_pp"], ci=f"[{r['lo']}, {r['hi']}]", wins=f"{r['n_a_only_wins']}/{r['n_b_only_wins']}"))
    return md(out, ["comparison", "lang", "n", "groups", "diff", "ci", "wins"], ["Comparison (A vs B)", "Lang", "Items", "Groups", "A-B (pp)", "95% CI", "A-only / B-only wins"])


def simple(name):
    p = T / name
    rows = csvrows(p)
    return md(rows, list(rows[0].keys())) if rows else "_(not available)_"


def main():
    tpl = (V2 / "FINAL_CONTEXT.template.md").read_text(encoding="utf-8")
    tpl = re.sub(r"<!--SECTION:(.*?)-->", lambda m: (V2 / "sections" / (m.group(1) + ".md")).read_text(encoding="utf-8"), tpl)
    def sub(m):
        k = m.group(1)
        if k.startswith("T1_"): return t1(k[3:])
        if k.startswith("T2_"): return t2(k[3:])
        if k.startswith("CSV:"): return simple(k[4:])
        if k.startswith("AUDIT:"):
            p = V2 / "results/audit" / k[6:]; return "```json\n" + (p.read_text(encoding="utf-8")[:3500] if p.exists() else "(missing)") + "\n```"
        return m.group(0)
    (V2 / "FINAL_CONTEXT.md").write_text(re.sub(r"<!--TABLE:(.*?)-->", sub, tpl), encoding="utf-8"); print("wrote FINAL_CONTEXT.md")


if __name__ == "__main__":
    main()
