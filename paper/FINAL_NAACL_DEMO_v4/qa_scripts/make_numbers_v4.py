#!/usr/bin/env python3
"""Writes latex_source_v4/generated/numbers_v4.tex and generated/tab_baseline.tex from the result files (no hand-typed numbers).
Sources (paper/baseline_system_paper_of_AAC_system/our_experiments_vs_baseline/results/):
  step5_<lang>.json            LoRA re-ranker gain over the evaluated build's trie (5 suggestions, full test sets)
  step17_baseline_ci.json      English: OPT baseline method vs ours, same candidates and sentences, paired CIs, speed (5 runs)
Usage: python3 make_numbers_v4.py"""
import json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
RES = HERE.parents[1] / "baseline_system_paper_of_AAC_system/our_experiments_vs_baseline/results"
GEN = HERE.parent / "latex_source_v4/generated"
f1 = lambda x: f"{x:.1f}"
mac = {}
for lang, key in (("en", "EN"), ("hi", "HI"), ("mr", "MR"), ("gu", "GU")):
    s = json.load(open(RES / f"step5_{lang}.json"))["systems"]
    a = next(v for k, v in s.items() if k.startswith("A ")); i = next(v for k, v in s.items() if k.startswith("I "))
    mac[f"LoraGain{key}"] = f1(i["avg_ksr"] - a["avg_ksr"])

b = json.load(open(RES / "step17_baseline_ci.json")); S = b["systems"]; SP = b["speed_ms_per_query"]; CI = b["paired_95ci_pp"]
GPU = "OURS predictor_v2 + adapted BLOOM-560m re-ranker K50 (GPU)"; CPU = "OURS predictor_v2 (CPU)"; OLD = "OURS old shipped infinity-gram (CPU)"
PRE1, PRE3 = "BASELINE facebook/opt-125m pretrained", "BASELINE facebook/opt-350m pretrained"
AD = [k for k in S if k.startswith("BASELINE facebook/opt-125m adapted")]
ad = b["opt125m_adapted_across_seeds"]
mac.update(OptSmKSR=f1(S[PRE1]["avg_ksr"]), OptLgKSR=f1(S[PRE3]["avg_ksr"]), OptAdKSR=f1(ad["mean"]),
           OptAdRange=f"{f1(ad['min'])}--{f1(ad['max'])}", OursGpuKSR=f1(S[GPU]["avg_ksr"]))
ci0 = CI[f"{GPU} minus {AD[0]}"]                                  # seed 0 (the speed-tested adapted model)
mac["OursGpuVsAdCI"] = f"{ci0['aac'][0]:+.1f} to {ci0['aac'][1]:+.1f} and {ci0['care'][0]:+.1f} to {ci0['care'][1]:+.1f}"
spd = lambda n: SP[n]["median_over_runs"]
mac.update(OursCpuMs=f"{spd(CPU):.1f}" if spd(CPU) >= 1 else f"{spd(CPU):.2f}", OursGpuMs=f"{spd('OURS predictor_v2 + BLOOM re-ranker K50 (GPU)'):.0f}",
           OptAdMs=f"{spd('BASELINE facebook/opt-125m adapted'):.0f}")
with open(GEN / "numbers_v4.tex", "w") as fh:
    fh.write("% v4 numbers, written by qa_scripts/make_numbers_v4.py from results/step5_*.json and results/step17_baseline_ci.json\n")
    for k, v in mac.items(): fh.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")


def row(label, name, speed_name=None, ref=GPU):
    r = S[name]; c = CI.get(f"{ref} minus {name}")
    ci = f"{c['aac'][0]:+.1f}/{c['aac'][1]:+.1f} & {c['care'][0]:+.1f}/{c['care'][1]:+.1f}" if c else "-- & --"
    sp = SP.get(speed_name or name)
    ms = f"{sp['median_over_runs']:.2f} ({sp['range_of_run_medians'][0]:.2f}--{sp['range_of_run_medians'][1]:.2f})" if sp else "--"
    return f"{label} & {f1(r['aac']['ksr_pct'])} & {f1(r['care']['ksr_pct'])} & {ci} & {ms} \\\\\n"


rows = [row("Evaluated build's trie (CPU)", OLD), row("Ours, CPU", CPU),
        row("\\rowcolor{rowtint}\\textbf{Ours, + adapted \\bloom{}}", GPU, "OURS predictor_v2 + BLOOM re-ranker K50 (GPU)"),
        row("\\opt{125m}, pretrained", PRE1), row("\\opt{350m}, pretrained", PRE3)]
rows += [row(f"\\opt{{125m}}, adapted, seed {k[-1]}", k, "BASELINE facebook/opt-125m adapted" if k.endswith("0") else None) for k in AD]
tab = r"""% v4, written by qa_scripts/make_numbers_v4.py from results/step17_baseline_ci.json (exp_step17_baseline_ci.py)
\begin{table}[t]
\centering\scriptsize
\setlength{\tabcolsep}{2.2pt}
\begin{tabular}{@{}lccccc@{}}
\toprule
 & \multicolumn{2}{c}{KSR \%} & \multicolumn{2}{c}{Ours$-$row, 95\% CI} & ms per query \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}
System & AAC & Care & AAC & Care & median (range) \\
\midrule
""" + "".join(rows) + r"""\bottomrule
\end{tabular}
\caption{English, full test sets (403 AAC-user and 402 caregiver sentences), five suggestions, one keystroke to select, the same candidates (300 frequent words matching the typed letters plus five character-model completions) for every system. \opt{} rows are our re-implementation of the baseline method \citep{gaines2025adapting} (word scores from the model; its own models and test data are not public). CI: paired bootstrap over sentences (1,000 resamples) of ours with the re-ranker minus the row. Speed: median of five runs of 200 fresh queries (range of the run medians); \opt{} and the re-ranker on a GPU shared with other jobs.}
\label{tab:baseline}
\end{table}
"""
open(GEN / "tab_baseline.tex", "w").write(tab)
print(mac)
