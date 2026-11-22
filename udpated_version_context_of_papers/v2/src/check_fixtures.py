#!/usr/bin/env python3
"""Fixture checks: unique keys, four-language groups, label fidelity to the board, exact / semantic overlap between splits, few-shot prompt overlap.
Writes results/checks/fixture_checks_<split>.json and exits non-zero on a violated rule.
Rules (fixtures/PREREGISTRATION.md section 5): (1) exact concept-sequence overlap holdout vs legacy/dev must be 0; (2) order-insensitive semantic key may coincide
only inside the word-order families H3 and H5 and is then listed; (3) no holdout selection reproduces a few-shot example input of the revised prompts."""
import ast, collections, json, re, sys
from common import *
sys.path.insert(0, str(REPO / "backend"))
import aac_lexicon as L, pipeline as P

CH = V2 / "results/checks"; CH.mkdir(parents=True, exist_ok=True)
SRC = (REPO / "backend/llm.py").read_text(encoding="utf-8")
tree = ast.parse(SRC); FEW = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "FEW_SHOT" for t in node.targets):
        FEW = ast.literal_eval(node.value)
EXAMPLES = {lg: {i for i, _ in cfg["examples"]} for lg, cfg in FEW.items()}
HEADS = re.findall(r'q = f"(.*?)\{', SRC)


def sem_key(r):
    return (r["gold_act"], bool(r["gold_neg"]), tuple(sorted(r["content_concepts"])), bool(r.get("more")))


def few_shot_queries(r):
    """Queries the revised realiser builds from the revised-client payload and from the explicit-gold payload (hi, gu, mr)."""
    if r["lang"] not in FEW: return []
    import run_streams as RS   # noqa (imports torch; fine for a check)
    qs = []
    for pay in (RS.gold_payload(r, "G1"),):
        ctx = P.normalize_request(dict(pay, language=r["lang"]))
        pre = {"hi": ("नहीं चाहिए", "मुझे चाहिए", "मैं कह रहा हूँ"), "gu": ("નથી જોઈતું", "મને જોઈએ છે", "હું કહું છું"), "mr": ("नको आहे", "मला हवे आहे", "मी सांगत आहे")}[r["lang"]]
        head = {"hi": HEADS[0], "gu": HEADS[1], "mr": HEADS[2]}[r["lang"]]
        intent = ctx["intent"]
        p = pre[0] if ctx["negation"] else (pre[1] if intent in ("REQUEST", "WANT") else pre[2])
        parts = [p] + ctx["entities"]
        if ctx["negation"] and ctx["act"] == "FEELING":
            parts = [pre[2], {"hi": "नहीं", "gu": "નથી", "mr": "नाही"}[r["lang"]]] + ctx["entities"]
        qs.append(head + " + ".join(parts))
    return qs


def main(split):
    rows = jl(V2 / "fixtures" / split / "scenarios.jsonl"); rep = dict(split=split, n=len(rows)); bad = []
    ids = [r["id"] for r in rows]; rep["unique_ids"] = len(set(ids)) == len(ids)
    if not rep["unique_ids"]: bad.append("duplicate ids")
    gl = collections.defaultdict(set)
    for r in rows: gl[r["group"]].add(r["lang"])
    rep["groups"] = len(gl); rep["groups_without_four_languages"] = [g for g, s in gl.items() if len(s) != 4 and not g.startswith("CM")]
    if split != "legacy" and rep["groups_without_four_languages"]: bad.append("groups missing a language")
    lab_bad = []
    for r in rows:
        if r.get("code_mix"): continue
        for el, lab in zip(r["seq"], r["labels"]):
            exp = el["typed"] if "typed" in el else L.BOARD[el["cid"]][r["lang"]]
            if exp != lab: lab_bad.append((r["id"], lab, exp))
    rep["label_mismatches"] = lab_bad
    if lab_bad: bad.append("label mismatch")
    others = {s: jl(V2 / "fixtures" / s / "scenarios.jsonl") for s in ("legacy", "dev", "holdout") if s != split}
    for name, rs in others.items():
        if not rs: continue
        seqs = {tuple(r["concept_seq"]) for r in rs}; keys = {sem_key(r) for r in rs}
        ex = sorted({"+".join(r["concept_seq"]) for r in rows if tuple(r["concept_seq"]) in seqs})
        se = sorted({(r["family"], "+".join(r["concept_seq"])) for r in rows if sem_key(r) in keys and tuple(r["concept_seq"]) not in seqs})
        rep[f"exact_sequence_overlap_with_{name}"] = ex; rep[f"semantic_key_overlap_only_with_{name}"] = se
        if split == "holdout":
            if ex: bad.append(f"exact overlap with {name}: {ex}")
            wo = [x for x in se if not x[0].startswith(("H3", "H4", "H5"))]
            if wo: bad.append(f"semantic overlap outside word-order families with {name}: {wo}")
    ov = sorted({r["id"] for r in rows if any(q in EXAMPLES.get(r["lang"], set()) for q in few_shot_queries(r))})
    rep["few_shot_prompt_overlap_ids"] = ov
    if split == "holdout" and ov: bad.append(f"few-shot overlap: {ov}")
    rep["violations"] = bad
    (CH / f"fixture_checks_{split}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(split, json.dumps({k: (v if not isinstance(v, list) or len(v) < 6 else f"{len(v)} items") for k, v in rep.items()}, ensure_ascii=False)); sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1])
