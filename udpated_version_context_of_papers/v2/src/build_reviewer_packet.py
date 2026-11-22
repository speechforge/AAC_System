#!/usr/bin/env python3
"""Blind, randomised native-rater packet: repaired template vs repaired hybrid on the SAME scenarios, per language, for two independent raters.
Neutral output IDs, balanced A/B side, per-rater item order, selected concepts and intended message shown, meaning rubric before naturalness and preference.
The key that maps neutral IDs to systems is written to a separate file that raters must never see.
Usage: python build_reviewer_packet.py --split holdout --mode rev"""
import argparse, csv, random
from common import *
import analyze_v2 as A

RUBRIC_COLS = ["content_added(Y/N)", "content_added_note", "content_omitted(Y/N)", "content_omitted_note", "polarity_and_negation_scope_correct(Y/N)",
               "act_correct(Y/N)", "speaker_is_first_person(Y/N)", "naturalness_1to5"]

INSTR = """# Rater instructions (blind packet)
You will see, for each item: the symbols the user selected (in your language), a short English statement of the intended message, and two candidate
sentences (Output 1, Output 2). You are not told how the sentences were made. Please work item by item and do not discuss with the other rater.

For EACH output answer, in this order:
1. content_added: does the sentence add something the user did not select (a place, time, reason, extra object, extra feeling)? Y/N, note what.
2. content_omitted: is a selected concept missing or replaced by another? Y/N, note which.
3. polarity_and_negation_scope_correct: is the sentence positive or negative exactly as the intended message says, and does the negation apply to the right word? Y/N.
4. act_correct: does it express the intended communicative act (asking for or wanting something, refusing something, saying how one feels, greeting)? Y/N.
5. speaker_is_first_person: is it said from the user's own point of view (implicit first person is fine; "the user wants..." is not)? Y/N.
6. naturalness_1to5 (ONLY after 1-5): 1 = not something a speaker would say, 5 = fully natural and grammatical.
Then give one preference per item: "1", "2" or "tie" (prefer the sentence that is clearer and more natural to a native speaker; choose tie if you cannot tell or both are equal).
Leave a cell empty if you cannot answer (missing ratings are reported, never imputed). Ambiguous selections: the intended message says the app should ask the user; rate
the sentence as given and use the note column if a confident sentence is not appropriate.
This is a language review of meaning and phrasing. It is not a usability study with AAC users.
"""
ADJ = """# Adjudication
Where the two raters disagree on any Y/N field, the adjudicator (a third native speaker, or the two raters together after finishing independently) decides the
field, and records the decision in adjudicated_<lang>.csv (same columns, one row per output). Pre-adjudication agreement is computed before this step from the two original files.
"""


def main(split, mode):
    rows = A.build_rows(split)
    scs = {r["id"]: r for r in jl(V2 / "fixtures" / split / "scenarios.jsonl")}
    by = {}
    for r in rows:
        if r["mode"] == mode and r["system"] in ("template_revised", "revised_hybrid") and not r["code_mix"] and r["seed"] in (None, 11):
            by.setdefault(r["id"], {})[r["system"]] = r
    out = V2 / "reviewer_packet"; out.mkdir(exist_ok=True)
    rng = random.Random(20261113); key = []; items = []
    for sid, d in sorted(by.items()):
        if "template_revised" not in d or "revised_hybrid" not in d: continue
        items.append((sid, d))
    for lang in LANGS:
        its = [(s, d) for s, d in items if scs[s]["lang"] == lang]
        flips = [i % 2 == 1 for i in range(len(its))]; rng.shuffle(flips)       # exactly half of the items swap sides
        for rater in ("R1", "R2"):
            order = list(range(len(its))); rng.shuffle(order)
            with open(out / f"packet_{lang}_{rater}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["item_id", "selected_symbols", "intended_message_en", "output_id_1", "output_1", "output_id_2", "output_2"] +
                           [f"o1_{c}" for c in RUBRIC_COLS] + [f"o2_{c}" for c in RUBRIC_COLS] + ["preference(1/2/tie)", "comment"])
                for pos, i in enumerate(order, 1):
                    sid, d = its[i]; sc = scs[sid]
                    a, b = d["template_revised"], d["revised_hybrid"]
                    if flips[i]: a, b = b, a
                    iid = f"{lang}-{rater}-{pos:03d}"
                    oid1, oid2 = f"{iid}a", f"{iid}b"
                    sym = " + ".join(sc["labels"])
                    w.writerow([iid, sym, sc["intended_en"], oid1, a["text"] or "", oid2, b["text"] or ""] + [""] * (2 * len(RUBRIC_COLS) + 2))
                    key.append(dict(item_id=iid, scenario=sid, group=sc["group"], rater=rater, lang=lang, output_id_1=oid1, system_1=a["system"], output_id_2=oid2, system_2=b["system"],
                                    identical_text=int(a["text"] == b["text"]), expected_outcome=sc["expected_outcome"]))
    write_csv(out / "KEY_DO_NOT_SHARE_WITH_RATERS.csv", key)
    (out / "RATER_INSTRUCTIONS.md").write_text(INSTR, encoding="utf-8"); (out / "ADJUDICATION.md").write_text(ADJ, encoding="utf-8")
    (out / "README.md").write_text(f"""# Reviewer packet (status: PENDING; no ratings collected)
Built {now_utc()} from the {split} split, input mode '{mode}', frozen system (config/freeze_manifest.json).
Files: packet_<lang>_R1.csv / _R2.csv (give one to each of two independent native raters per language), RATER_INSTRUCTIONS.md, ADJUDICATION.md,
KEY_DO_NOT_SHARE_WITH_RATERS.csv (maps neutral IDs to systems; analysts only), analyze_ratings.py (run after ratings return).
Items: {len(items)} scenarios (all with both outputs); pairs per language R1/R2 each: {len(items)//4}. Fixtures are DRAFT until the same raters confirm gold concepts, act and polarity.
""", encoding="utf-8")
    print(len(items), "items;", len(key), "key rows")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--split", default="holdout"); ap.add_argument("--mode", default="rev"); a = ap.parse_args()
    main(a.split, a.mode)
