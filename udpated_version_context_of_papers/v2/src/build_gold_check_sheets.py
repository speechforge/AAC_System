#!/usr/bin/env python3
"""Native-speaker gold check sheets: for every holdout and dev item, the symbols as the user sees them in that language, the gold concepts, act, polarity and the intended meaning
in English.  A native speaker confirms or corrects each field BEFORE scores are used in the paper (fixtures stay DRAFT until then).
Output: fixtures/<split>/native_gold_check_<lang>.csv (+ README_DRAFT.md)."""
import csv
from common import *
COLS = ["item_id", "group", "selected_symbols(as shown)", "gold_concepts", "gold_act", "gold_negated", "expected_system_outcome", "intended_meaning_en",
        "symbols_make_sense_in_this_language(Y/N)", "gold_concepts_correct(Y/N)", "gold_act_correct(Y/N)", "gold_polarity_correct(Y/N)", "is_it_truly_ambiguous(Y/N)", "acceptable_natural_sentences(free text, 1-3)", "comment"]
for split in ("holdout", "dev"):
    rows = jl(V2 / "fixtures" / split / "scenarios.jsonl")
    for lang in LANGS:
        with open(V2 / "fixtures" / split / f"native_gold_check_{lang}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(COLS)
            for r in rows:
                if r["lang"] != lang: continue
                w.writerow([r["id"], r["group"], " + ".join(r["labels"]), " + ".join(r["concept_seq"]), r["gold_act"], r["gold_neg"], r["expected_outcome"], r["intended_en"]] + [""] * 7)
    (V2 / "fixtures" / split / "README_DRAFT.md").write_text(f"""# {split} fixtures: DRAFT
Gold concepts, act, polarity and intended meaning were written by the authoring assistant from the board vocabulary. They have NOT been checked by native speakers.
Use `native_gold_check_<lang>.csv` (one sheet per language, one row per item). Until two native speakers per language have returned the sheets, every score computed on these items is
PRELIMINARY and must stay out of the paper. Personal-vocabulary items (typed words) and deliberately ambiguous items need particular attention.
""", encoding="utf-8")
print("sheets written")
