#!/usr/bin/env python3
r"""Extra evidence checks added after the five-agent review (all recomputed from the archived result files):
 1. paired deployed-vs-template wins and losses (scorer v1);
 2. the gate effect (deployed minus cascade-before-gate) pooled, English only, Indic only, and Gujarati, with a group bootstrap over
    board selections (same unit as the audit's A7 intervals; seed 20261113, 10,000 resamples);
 3. gate precision: accepted outputs correct, fallbacks correct, failing candidates admitted, and whether every failure->success flip is a template sentence;
 4. client payload provenance: payloads built by the harness equal the payloads captured from the real page (184 monolingual scenarios).
Usage: python3 extra_checks.py <repo_root>"""
import csv, collections, random, json, sys, pathlib
root = pathlib.Path(sys.argv[1])
ev = root / "paper/CLAUDE_WRITTEN/naacl2027_demo/eval"
rows = [r for r in csv.DictReader(open(ev / "results/scored.csv", encoding="utf-8")) if r["code_mix"] != "True" and r["overlap"] != "True"]
by = collections.defaultdict(dict)
for r in rows: by[r["id"]][(r["system"], r["cond"])] = r
B = lambda s: s == "True"
print("1. paired deployed vs template")
for cond in ("ui", "st"):
    w = sum(B(d[("deployed", cond)]["success"]) and not B(d[("template_only", cond)]["success"]) for d in by.values())
    l = sum(B(d[("template_only", cond)]["success"]) and not B(d[("deployed", cond)]["success"]) for d in by.values())
    print(f"   {cond}: deployed-only wins {w}, template-only wins {l}, net {w-l}")
print("2. gate effect with a group bootstrap")
def effect(langs, cond, n=10000, seed=20261113):
    g = collections.defaultdict(lambda: [0, 0])
    for i, d in by.items():
        if i.split("-")[0] in langs:
            k = i.split("-", 1)[1]; g[k][0] += B(d[("deployed", cond)]["success"]) - B(d[("llm3_pre", cond)]["success"]); g[k][1] += 1
    keys = list(g); rng = random.Random(seed); xs = []
    for _ in range(n):
        s = [g[rng.choice(keys)] for _ in keys]; xs.append(100 * sum(a for a, b in s) / sum(b for a, b in s))
    xs.sort(); tot = sum(v[1] for v in g.values())
    return 100 * sum(v[0] for v in g.values()) / tot, xs[int(.025 * n)], xs[int(.975 * n)], tot
for langs, name in ((("en", "hi", "gu", "mr"), "all four"), (("hi", "gu", "mr"), "Hindi+Gujarati+Marathi"), (("en",), "English"), (("gu",), "Gujarati")):
    for cond in ("ui", "st"):
        e = effect(langs, cond); print(f"   {name:24s} {cond}: {e[0]:+.1f} pp  [{e[1]:.1f}, {e[2]:.1f}]  items {e[3]}")
print("3. gate precision and flips")
for cond in ("ui", "st"):
    acc = [d[("deployed", cond)] for d in by.values() if not B(d[("deployed", cond)]["fallback"])]
    fb = [d[("deployed", cond)] for d in by.values() if B(d[("deployed", cond)]["fallback"])]
    fail = [d for d in by.values() if not B(d[("llm3_pre", cond)]["success"])]
    admitted = sum(not B(d[("deployed", cond)]["fallback"]) for d in fail)
    flips = [d for d in by.values() if not B(d[("llm3_pre", cond)]["success"]) and B(d[("deployed", cond)]["success"])]
    tmpl = sum(B(d[("deployed", cond)]["fallback"]) or d[("deployed", cond)]["text"] == d[("template_only", cond)]["text"] for d in flips)
    print(f"   {cond}: accepted {len(acc)} correct {sum(B(a['success']) for a in acc)}; fallbacks {len(fb)} correct {sum(B(a['success']) for a in fb)}; "
          f"failing candidates {len(fail)}, admitted {admitted}; failure->success flips {len(flips)}, template sentences {tmpl}")
print("4. client payload provenance")
cap = {}
for l in open(root / "udpated_version_context_of_papers/v2/results/payloads/original_legacy.jsonl", encoding="utf-8"):
    if l.strip(): r = json.loads(l); cap[r["id"]] = r
same = n = 0
for l in open(ev / "fixtures/scenarios.jsonl", encoding="utf-8"):
    if not l.strip(): continue
    s = json.loads(l)
    if s.get("code_mix"): continue
    n += 1; a = s["payload_ui"]; b = cap[s["id"]]["payload"]
    same += all(a[k] == b[k] for k in ("intent", "negation", "entities", "language", "code_mix"))
print(f"   harness payloads identical to payloads captured from the real page: {same}/{n}")
