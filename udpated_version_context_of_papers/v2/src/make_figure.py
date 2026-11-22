#!/usr/bin/env python3
"""One figure: (A) what the gate accepts and rejects, scored against the automatic scorer (first candidates of the saved streams), for the archived gate V0 and the
revised gate V1; (B) the dominant failure categories of the archived system and the revised hybrid.  Source data: results/figures/fig_gate_source.csv (written here).
Palette: blue #2a78d6 / orange #eb6834 (validated, CVD dE >= 24); grey for rejected candidates; direct labels, no dual axes.
Usage: python make_figure.py --split holdout"""
import argparse, csv, collections
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import *

BLUE, ORANGE, G1, G2, INK = "#2a78d6", "#eb6834", "#c9c8c2", "#8f8e88", "#0b0b0b"


def main(split):
    t4 = [r for r in csv.DictReader(open(V2 / f"results/tables/T4_gate_confusion_{split}.csv", encoding="utf-8")) if r["lang"] == "ALL"]
    t3 = list(csv.DictReader(open(V2 / f"results/tables/T3_errors_{split}.csv", encoding="utf-8")))
    src = []
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.2, 3.9), gridspec_kw=dict(width_ratios=[1.15, 1]))
    # ---- A: gate verdict vs scorer verdict
    rows = {}
    for r in t4:
        rows.setdefault(r["gate"], collections.Counter())
        for k in ("accept_correct", "accept_wrong", "reject_wrong", "reject_correct"): rows[r["gate"]][k] += int(r[k])
    names = {"V0_archived": "Archived gate", "V1_revised": "Revised gate"}
    ypos = {"V1_revised": 1, "V0_archived": 0}
    segs = [("accept_correct", "accepted, correct", BLUE), ("accept_wrong", "accepted, wrong", ORANGE), ("reject_wrong", "rejected, wrong", G1), ("reject_correct", "rejected, correct", G2)]
    for g, c in rows.items():
        n = sum(c.values()); left = 0
        for k, lab, col in segs:
            w = 100 * c[k] / n
            ax.barh(ypos[g], w, left=left, color=col, edgecolor="#fcfcfb", linewidth=2, height=0.55, hatch=("////" if k == "reject_correct" else None))
            if w >= 4: ax.text(left + w / 2, ypos[g], f"{c[k]}", ha="center", va="center", fontsize=8.5, color=("white" if col in (BLUE, ORANGE, G2) else INK))
            src.append(dict(panel="A", gate=g, category=lab, count=c[k], n=n, pct=round(w, 1))); left += w
        ax.text(101.5, ypos[g], f"n = {n}", va="center", fontsize=8.5, color="#52514e")
    ax.set_yticks([0, 1]); ax.set_yticklabels([names["V0_archived"], names["V1_revised"]], fontsize=9.5)
    ax.set_xlim(0, 112); ax.set_xlabel("share of first candidates (%)", fontsize=9)
    ax.set_title("A  Gate verdict against the automatic scorer", loc="left", fontsize=10.5, fontweight="bold")
    h = [plt.Rectangle((0, 0), 1, 1, color=c, hatch=("////" if "rejected, correct" in l else None)) for _, l, c in segs]
    ax.legend(h, [l for _, l, _ in segs], ncol=2, fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2))
    # ---- B: failure categories, determinate scenarios, rev (browser) input where available
    cats = [("missing_concepts", "missed concept"), ("unsupported", "added content"), ("act_wrong", "wrong act"), ("act_missing", "act missing"),
            ("polarity_drop", "negation dropped"), ("polarity_spur", "spurious negation"), ("polarity_scope", "negation scope"), ("third_person", "third person"), ("script_err", "script error")]
    def pick(system, modes):
        for m in modes:
            for r in t3:
                if r["system"] == system and r["mode"] == m: return r
    A = pick("archived_deployed", ["orig", "gold"]); B = pick("revised_hybrid", ["rev", "gold"])
    if A and B:
        import numpy as np
        y = np.arange(len(cats))[::-1]
        for yy, (key, lab) in zip(y, cats):
            a = int(float(A[key])) if key in A else 0; b = int(float(B[key])) if key in B else 0
            na, nb = int(A["n_rows"]), int(B["n_rows"])
            bx.barh(yy + 0.19, 100 * a / na, height=0.34, color=BLUE, edgecolor="#fcfcfb", linewidth=1)
            bx.barh(yy - 0.19, 100 * b / nb, height=0.34, color=ORANGE, edgecolor="#fcfcfb", linewidth=1)
            bx.text(100 * a / na + 0.6, yy + 0.19, str(a), va="center", fontsize=8, color="#52514e"); bx.text(100 * b / nb + 0.6, yy - 0.19, str(b), va="center", fontsize=8, color="#52514e")
            src.append(dict(panel="B", gate="", category=lab, count=a, n=na, pct=round(100 * a / na, 1), system=f"archived_deployed|{A['mode']}"))
            src.append(dict(panel="B", gate="", category=lab, count=b, n=nb, pct=round(100 * b / nb, 1), system=f"revised_hybrid|{B['mode']}"))
        bx.set_yticks(y); bx.set_yticklabels([l for _, l in cats], fontsize=9); bx.set_xlabel("outputs with the flag (% of determinate draws)", fontsize=9)
        bx.legend([plt.Rectangle((0, 0), 1, 1, color=BLUE), plt.Rectangle((0, 0), 1, 1, color=ORANGE)], [f"archived system ({A['mode']} input)", f"revised hybrid ({B['mode']} input)"], fontsize=8, frameon=False, loc="lower right")
        bx.set_title("B  Error categories of the final output", loc="left", fontsize=10.5, fontweight="bold")
    for a_ in (ax, bx):
        for s in ("top", "right"): a_.spines[s].set_visible(False)
        a_.tick_params(labelsize=8.5); a_.xaxis.grid(True, color="#e5e4df", linewidth=0.6); a_.set_axisbelow(True)
    fig.tight_layout()
    d = V2 / "results/figures"; d.mkdir(parents=True, exist_ok=True)
    fig.savefig(d / f"fig_gate_{split}.pdf"); fig.savefig(d / f"fig_gate_{split}.png", dpi=200)
    write_csv(d / f"fig_gate_source_{split}.csv", src, ["panel", "gate", "system", "category", "count", "n", "pct"])
    print("figure ->", d / f"fig_gate_{split}.png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--split", default="holdout"); main(ap.parse_args().split)
