#!/usr/bin/env python3
"""Reproduces EVERY confidence interval printed in Section 4 (Evaluation) of the v3 paper, from the frozen scored outputs only.

Method (as stated in Section 4): paired difference in success rate between two systems on the same scenarios, in percentage
points; 95 % percentile interval from a bootstrap over the 46 SCENARIO GROUPS (a group = one board selection in its four
language versions, so the four translations are resampled together); 10,000 resamples; seed 20261113. Each resample draws
46 groups with replacement and divides the summed paired differences by the number of scenarios drawn (a ratio estimator,
because groups hold 3-4 scenarios after the nine few-shot exclusions). The 8 Hinglish scenarios and the 9 scenarios that
duplicate a few-shot prompt example are excluded (175 scenarios remain).

Input : paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results/scored.csv  (frozen; read only)
Output: prints each comparison and writes paired_group_bootstrap.json next to this script.
Same procedure as udpated_version_context_of_papers/v2/src/audit_archived.py (block A7), which wrote
v2/results/audit/A7_paired_ci_recomputed.json; this file needs only numpy and the CSV.
Usage : python3 paired_group_bootstrap.py [path/to/scored.csv]"""
import collections, csv, json, pathlib, sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CSV = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results/scored.csv"
SEED, B = 20261113, 10000
# (system, condition) pairs as named in scored.csv; ui = client input, st = explicit fields
PRINTED = [  # comparison, what the paper prints (pp, 95 % CI)
    (("deployed", "ui"), ("llm3_pre", "ui"), "gate + fallback vs ungated cascade, client input", (18.3, 11.9, 25.2)),
    (("deployed", "st"), ("llm3_pre", "st"), "gate + fallback vs ungated cascade, explicit fields", (34.9, 26.7, 43.4)),
    (("deployed", "st"), ("deployed", "ui"), "explicit fields vs client input, deployed", (20.0, 12.0, 28.7)),
    (("template_only", "st"), ("deployed", "st"), "template baseline vs deployed, explicit fields", (20.0, 14.0, 26.4)),
    (("template_only", "ui"), ("deployed", "ui"), "template baseline vs deployed, client input", (12.0, 6.4, 17.9)),
]

rows = [r for r in csv.DictReader(open(CSV, encoding="utf-8")) if r["code_mix"] == "False" and r["overlap"] == "False"]
succ = {(r["id"], r["system"], r["cond"]): float(r["success"] == "True") for r in rows}
ids = sorted({r["id"] for r in rows})
group = lambda i: i.split("-", 1)[1]            # "hi-T1_request_object-WATER" -> "T1_request_object-WATER"


def paired(a, b):
    cells = collections.defaultdict(list)
    for i in ids:
        if (i, *a) in succ and (i, *b) in succ:
            cells[group(i)].append(succ[(i, *a)] - succ[(i, *b)])
    g = sorted(cells); tot = np.array([sum(cells[k]) for k in g]); cnt = np.array([len(cells[k]) for k in g])
    idx = np.random.default_rng(SEED).integers(0, len(g), size=(B, len(g)))
    bs = tot[idx].sum(1) / cnt[idx].sum(1)
    return dict(n_scenarios=int(cnt.sum()), n_groups=len(g), diff_pp=round(100 * tot.sum() / cnt.sum(), 2),
                ci95_pp=[round(100 * float(np.percentile(bs, 2.5)), 2), round(100 * float(np.percentile(bs, 97.5)), 2)])


out, ok_all = {}, True
for a, b, name, printed in PRINTED:
    r = paired(a, b)
    ok = all(abs(x - y) < 0.051 for x, y in zip((r["diff_pp"], *r["ci95_pp"]), printed))
    ok_all &= ok
    out[name] = dict(r, printed=printed, matches_paper=ok)
    print(f"{name:55s} {r['diff_pp']:6.2f} [{r['ci95_pp'][0]:6.2f}, {r['ci95_pp'][1]:6.2f}]  n={r['n_scenarios']} groups={r['n_groups']}"
          f"  paper {printed}  {'OK' if ok else 'MISMATCH'}")
json.dump(dict(method=__doc__.split("Input")[0].strip(), seed=SEED, resamples=B, results=out, all_match=ok_all),
          open(HERE / "paired_group_bootstrap.json", "w"), indent=1)
print("ALL PRINTED INTERVALS REPRODUCED" if ok_all else "SOME INTERVALS DO NOT MATCH")
sys.exit(0 if ok_all else 1)
