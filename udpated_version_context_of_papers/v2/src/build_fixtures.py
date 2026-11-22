#!/usr/bin/env python3
"""Build scenario fixtures from the board vocabulary.  Splits: legacy (the archived 175 + 8 Hinglish, converted), dev (hand-listed), holdout (candidate lists + seeded draw).
The holdout generator is executed ONLY after the system freeze (config/freeze_manifest.json must exist) -- see fixtures/PREREGISTRATION.md.
Scenario schema (one row per scenario group x language):
  id, group, family, lang, seq [{cid} | {typed:{lang:word}}], labels (clicked, in order), concept_ids, content_concepts, customs, more,
  gold_act (request|feeling|feeling_request|greeting|ambiguous), gold_neg, expected_outcome (sentence|clarification), template_covered, intended_en, status
"""
import argparse, json, pathlib, random, sys
from common import *

BOARD = json.loads((ARCH / "fixtures/board_vocab.json").read_text(encoding="utf-8"))["vocab"]
LAB = {s["id"]: s for cat in BOARD.values() for s in cat}
FEEL = {"HAPPY", "SAD", "ANGRY", "TIRED", "SICK", "SCARED", "LOVE", "EXCITED"}
ACTS = set(c["id"] for c in BOARD["actions"]); OBJ = set(c["id"] for c in BOARD["food"]) | {"MEDICINE"}; PPL = set(c["id"] for c in BOARD["people"])
TYPED = {  # personal vocabulary (typed words) in each script
    "NAME1": dict(en="Anil", hi="अनिल", gu="અનિલ", mr="अनिल"), "NAME2": dict(en="Meera", hi="मीरा", gu="મીરા", mr="मीरा"),
    "DISH1": dict(en="Dosa", hi="डोसा", gu="ઢોસા", mr="डोसा"), "DISH2": dict(en="Idli", hi="इडली", gu="ઈડલી", mr="इडली"),
    "DRINK1": dict(en="Horlicks", hi="हॉर्लिक्स", gu="હોર્લિક્સ", mr="हॉर्लिक्स")}


def gold_from(seq_ids):
    """Independent gold annotation from the concept sequence (author's rule, to be checked by native speakers)."""
    neg = seq_ids.count("NO") % 2 == 1
    more = "MORE" in seq_ids
    content = [c for c in seq_ids if c not in ("NO", "MORE", "ME", "WANT", "PLEASE", "YES")]
    feel = [c for c in content if c in FEEL or c in ("GOOD", "BAD")]
    typed = [c for c in content if c.startswith("~")]
    if any(c in ("NAMASTE", "THANKS", "BYE") for c in content):
        act = "greeting"
    elif feel and len(content) > 1:
        act = "feeling_request"
    elif feel and len(content) == 1 and content[0] in FEEL:
        act = "feeling"
    elif content and all(c in ACTS | OBJ | PPL | {"HELP", "SCHOOL", "HOME", "HOSPITAL"} or c.startswith("~") for c in content):
        act = "request"
    else:
        act = "ambiguous"
    return dict(gold_act=act, gold_neg=neg, more=more, content_concepts=content)


def render(group, family, seq_ids, lang, covered, split, expected="sentence", gloss=""):
    seq, labels, customs = [], [], []
    for c in seq_ids:
        if c.startswith("~"):
            w = TYPED[c[1:]][lang]; seq.append(dict(typed=w)); labels.append(w); customs.append(w)
        else:
            seq.append(dict(cid=c)); labels.append(LAB[c][lang])
    g = gold_from(seq_ids)
    cc = [c for c in g["content_concepts"] if not c.startswith("~")] + ["~" + TYPED[c[1:]][lang] for c in g["content_concepts"] if c.startswith("~")]
    return dict(id=f"{lang}-{group}", group=group, family=family, lang=lang, code_mix=False, split=split, seq=seq, labels=labels,
                concept_ids=[c if not c.startswith("~") else None for c in seq_ids], concept_seq=seq_ids,
                content_concepts=cc, customs=customs, more=g["more"], gold_act=("ambiguous" if expected == "clarification" else g["gold_act"]),
                gold_neg=g["gold_neg"], expected_outcome=expected, template_covered=covered, intended_en=gloss, status="DRAFT (native-speaker check pending)")


def gloss(seq_ids):
    g = gold_from(seq_ids); names = [(TYPED[c[1:]]["en"] if c.startswith("~") else LAB[c]["en"].split("/")[0].lower()) for c in g["content_concepts"]]
    n = "not " if g["gold_neg"] else ""
    return {"request": f"The speaker does {n}want / ask for: {', '.join(names)}" + (" (more of it)" if g["more"] else ""), "feeling": f"The speaker is {n}feeling: {', '.join(names)}",
            "feeling_request": f"The speaker feels {names[0]} and also wants: {', '.join(names[1:])}", "greeting": f"The speaker greets: {', '.join(names)}",
            "ambiguous": f"Unclear what the speaker means by: {', '.join(names)} (the system should ask)"}[g["gold_act"]]


DEV = {   # hand-listed development groups: family -> concept sequences
    "D1_request_two_objects": [["TEA", "SNACK"], ["MILK", "FRUIT"]],
    "D2_request_more": [["MORE", "MILK"], ["MORE", "FRUIT"]],
    "D3_refusal": [["NO", "MORE", "TEA"], ["ROTI", "NO"], ["NO", "WATER", "RICE"]],
    "D4_feeling": [["ME", "SAD"], ["ANGRY", "ME"]],
    "D5_negated_feeling": [["ME", "NO", "TIRED"], ["HAPPY", "NO"]],
    "D6_action": [["EAT", "FOOD"], ["PLAY"]],
    "D7_negated_action": [["NO", "PLAY"], ["NO", "SLEEP"]],
    "D8_help_call": [["HELP", "FATHER"], ["CALL", "SISTER"]],
    "D9_feeling_request": [["TIRED", "WATER"], ["SCARED", "HELP"]],
    "D10_personal": [["DRINK", "~DRINK1"]],
    "D11_ambiguous": [["GOOD"]],
}
HOLDOUT = {   # family -> (slots, candidates, covered, expected)
    "H1_request_more": (2, [["MORE", "WATER"], ["MORE", "RICE"], ["MORE", "JUICE"], ["MORE", "ROTI"], ["MORE", "SNACK"]], True, "sentence"),
    "H2_request_two_objects": (2, [["WATER", "MILK"], ["RICE", "ROTI"], ["FRUIT", "JUICE"], ["ROTI", "TEA"], ["WATER", "FRUIT"]], True, "sentence"),
    "H3_refusal": (3, [["NO", "MORE", "RICE"], ["FRUIT", "NO"], ["NO", "SNACK", "JUICE"], ["JUICE", "NO"], ["NO", "MORE", "WATER"], ["NO", "MILK", "TEA"], ["PIZZA", "NO"]], True, "sentence"),
    "H4_feeling": (2, [["ME", "TIRED"], ["SCARED", "ME"], ["ME", "SICK"], ["EXCITED", "ME"], ["ME", "HAPPY"]], True, "sentence"),
    "H5_negated_feeling": (3, [["ME", "NO", "SICK"], ["SAD", "NO"], ["NO", "SCARED", "ME"], ["ANGRY", "NO"], ["ME", "NO", "LOVE"]], True, "sentence"),
    "H6_action_object": (3, [["EAT", "PIZZA"], ["DRINK", "JUICE"], ["EAT", "SNACK"]], True, "sentence"),
    "H7_negated_action": (3, [["NO", "GO"], ["NO", "EAT", "PIZZA"], ["NO", "STUDY"], ["NO", "BATH"], ["NO", "DRINK", "MILK"]], True, "sentence"),
    "H8_help_call": (3, [["HELP", "TEACHER"], ["CALL", "FRIEND"], ["CALL", "FATHER"], ["HELP", "FRIEND"], ["CALL", "BROTHER"]], True, "sentence"),
    "H9_feeling_request": (2, [["TIRED", "SLEEP"], ["SICK", "MEDICINE"], ["HAPPY", "PLAY"]], True, "sentence"),
    "H10_personal": (2, [["CALL", "~NAME1"], ["EAT", "~DISH1"], ["CALL", "~NAME2"], ["EAT", "~DISH2"]], True, "sentence"),
    "H11_ambiguous": (2, [["NOSE"], ["BAD"], ["HEART"], ["EYE"]], False, "clarification"),
    "H12_template_uncovered": (3, [["GO", "SCHOOL"], ["GO", "HOME"], ["NAMASTE", "TEACHER"], ["GO", "HOSPITAL"], ["NAMASTE", "FRIEND"]], False, "sentence"),
}


def legacy():
    rows = []
    for s in jl(ARCH / "fixtures/scenarios.jsonl"):
        cids = s["concept_ids"]
        r = render(s["id"].split("-", 1)[1], s["type"], cids, s["lang"], True, "legacy", gloss=gloss(cids))
        r["id"] = s["id"]; r["code_mix"] = s["code_mix"]; r["gold_act"] = s["gold_act"]; r["gold_neg"] = s["gold_neg"]; r["content_concepts"] = s["content_concepts"]
        if s["code_mix"]:
            r["labels"] = s["labels"]; r["lang"] = "hi"; r["archived_payload_ui"] = s["payload_ui"]; r["archived_payload_structured"] = s["payload_structured"]
        rows.append(r)
    return rows


def dev():
    rows = []
    for fam, seqs in DEV.items():
        for i, seq in enumerate(seqs):
            for lang in LANGS:
                rows.append(render(f"{fam.split('_')[0]}-{i + 1:02d}", fam, seq, lang, fam not in ("D11_ambiguous",), "dev",
                                   expected=("clarification" if fam == "D11_ambiguous" else "sentence"), gloss=gloss(seq)))
    return rows


def _overlaps_few_shot(seq):
    """Pre-registered rule 3 (enforced by rejection, Addendum 1): a candidate is dropped when any language rendering reproduces a few-shot example input."""
    import check_fixtures as CF
    return any(CF.few_shot_queries(r) and any(q in CF.EXAMPLES.get(r["lang"], set()) for q in CF.few_shot_queries(r))
               for r in (render("x", "x", seq, lg, True, "holdout", gloss="") for lg in LANGS))


def holdout():
    rng = random.Random(20261113)
    rows, log = [], []
    for fam, (k, cands, cov, exp) in HOLDOUT.items():
        rejected = [c for c in cands if _overlaps_few_shot(c)]
        pool = sorted(c for c in cands if c not in rejected)
        pick = pool if len(pool) <= k else rng.sample(pool, k)
        pick = sorted(pick)
        log.append(dict(family=fam, slots=k, candidates=pool, rejected_for_few_shot_overlap=rejected, drawn=pick))
        for i, seq in enumerate(pick):
            for lang in LANGS:
                rows.append(render(f"{fam.split('_')[0]}-{i + 1:02d}", fam, seq, lang, cov, "holdout", expected=exp, gloss=gloss(seq)))
    return rows, log


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("split", choices=["legacy", "dev", "holdout"]); a = ap.parse_args()
    d = V2 / "fixtures" / a.split
    d.mkdir(parents=True, exist_ok=True)
    if a.split == "holdout":
        if not (V2 / "config/freeze_manifest.json").exists():
            sys.exit("REFUSED: config/freeze_manifest.json is missing; the holdout may only be generated after the system freeze.")
        rows, log = holdout()
        (d / "build_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        rows = legacy() if a.split == "legacy" else dev()
    write_jl(d / "scenarios.jsonl", rows)
    print(a.split, len(rows), "rows;", len({r['group'] for r in rows}), "groups; sha256", sha256(d / "scenarios.jsonl")[:16])
