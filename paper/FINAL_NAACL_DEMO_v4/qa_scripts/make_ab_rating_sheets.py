#!/usr/bin/env python3
"""Review point 1 (template beats the gate under a lexical scorer): materials for the study that CAN separate them.

The lexical scorer rewards echoing the selected labels, so it cannot measure what model phrasing adds over a template.
This script builds BLIND paired-comparison sheets for native speakers: for every primary scenario in which the deployed
system spoke an accepted MODEL sentence that differs from the template sentence for the same selection, the two sentences
are shown in random order (A/B) with the selection and its intended meaning. Raters answer, for each sentence:
  meaning  - does it say exactly what the selection means? (yes / no)
  natural  - how natural is it as something a person would say? (1-5)
and once per pair: preferred (A / B / no preference). The key (which side is the model) is written to a separate file.
Analysis plan (fixed before ratings): paired difference model - template in meaning-correct rate and mean naturalness,
95 % bootstrap CI over the 46 scenario groups (as paired_group_bootstrap.py); two raters per language; agreement reported.
Inputs (read only): paper/CLAUDE_WRITTEN/naacl2027_demo/eval/{fixtures/scenarios.jsonl, results/scored.csv}
Outputs: ab_rating/<lang>_sheet.csv (for raters), ab_rating/KEY_do_not_share.csv (for the analyst).
Usage: python3 make_ab_rating_sheets.py"""
import csv, json, pathlib, random

HERE = pathlib.Path(__file__).resolve().parent
EVAL = HERE.parents[2] / "paper/CLAUDE_WRITTEN/naacl2027_demo/eval"
OUT = HERE / "ab_rating"; OUT.mkdir(exist_ok=True)
sc = {json.loads(l)["id"]: json.loads(l) for l in open(EVAL / "fixtures/scenarios.jsonl", encoding="utf-8")}
rows = [r for r in csv.DictReader(open(EVAL / "results/scored.csv", encoding="utf-8")) if r["code_mix"] == "False" and r["overlap"] == "False"]
d = {(r["id"], r["system"], r["cond"]): r for r in rows}
pairs = {}
for (i, s, c), r in d.items():
    t = d.get((i, "template_only", c))
    if s == "deployed" and t and r["fallback"] == "False" and r["text"].strip() != t["text"].strip():
        pairs.setdefault((i, r["text"].strip(), t["text"].strip()), set()).add(c)   # same sentence pair in both conditions -> once
rng = random.Random(20261123); key = []; sheets = {}
for n, ((i, model, tmpl), conds) in enumerate(sorted(pairs.items())):
    s = sc[i]; flip = rng.random() < 0.5; a, b = (tmpl, model) if flip else (model, tmpl)
    item = f"{s['lang']}-{n:03d}"
    meaning = ("NOT " if s["gold_neg"] else "") + f"{s['gold_act']}: " + " + ".join(s["labels"])
    sheets.setdefault(s["lang"], []).append(dict(item=item, selection=" + ".join(s["labels"]), intended=meaning, sentence_A=a, sentence_B=b,
                                                  A_meaning_yes_no="", A_natural_1to5="", B_meaning_yes_no="", B_natural_1to5="", preferred_A_B_none=""))
    key.append(dict(item=item, scenario_id=i, group=i.split("-", 1)[1], conditions="+".join(sorted(conds)), model_side="B" if flip else "A"))
for lang, items in sheets.items():
    rng.shuffle(items)
    with open(OUT / f"{lang}_sheet.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(items[0])); w.writeheader(); w.writerows(items)
with open(OUT / "KEY_do_not_share.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(key[0])); w.writeheader(); w.writerows(key)
print({l: len(v) for l, v in sheets.items()}, "pairs:", len(key))
