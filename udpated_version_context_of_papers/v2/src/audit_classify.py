#!/usr/bin/env python3
"""PHASE A (cont.) -- record the manual inspection of every failing output of the archived explicit-gold run
(37 accepted-model + 6 template-fallback + 8 template-only = 51 rows in A3_failures.csv).

The labels below are the ASSISTANT'S reading of each recorded string (not a native speaker); they are provisional until a native reviewer
confirms them. Strings are never altered. Categories:
  THIRD_PERSON            fluent but a report about 'the user' (perspective error); meaning otherwise preserved
  ADDED_CONTENT           concept(s) or reasons not selected were added
  NEGATED_WANT            a negated FEELING was realized as a negated WANT ('I do not want sad'): act error
  UNGRAMMATICAL           word order / agreement broken; message not recoverable or only guessable
  SCORER_LEXICAL_GAP      meaning preserved, the original scorer's marker list does not cover the wording (false failure)
Output: results/audit/A3_failure_classification.csv, A3_classification_summary.json"""
import collections, csv, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

OUT = V2 / "results/audit"
rows = list(csv.DictReader(open(OUT / "A3_failures.csv", encoding="utf-8")))


def classify(r):
    i, c, lang, fam = r["id"], r["cohort"], r["lang"], r["family"]
    if c in ("template_fallback", "template_only"):   # all are Gujarati negated feelings: 'મને <feeling> લાગતું નથી'
        return ("SCORER_LEXICAL_GAP", "scorer", "meaning 'I do not feel <X>' preserved; the Gujarati feeling-marker list has લાગે but not લાગતું. "
                "Phrasing for ગુસ્સો/પ્રેમ/ડરેલું may be unnatural (native review pending)")
    if lang == "en" and fam in ("T1_request_object", "T5_action_object") and "The user" in r["output_text"]:
        return ("THIRD_PERSON", "scorer_correct", "'The user ...' report; flagged off-task by the English pattern 'the user'")
    if i in ("en-T3_feeling-SICK", "en-T3_feeling-SCARED"):
        return ("ADDED_CONTENT", "scorer_correct", "unselected eating/restaurant content added; flagged by the distractor list")
    if i == "en-T3_feeling-LOVE":
        return ("ADDED_CONTENT", "scorer_partial", "'spending time with you' added; the scorer flags only the missing feeling marker")
    if i.startswith("en-T4_negated_feeling"):
        return ("ADDED_CONTENT", "scorer_correct", "garbled; negation attaches to an added 'eat' clause, not to the selected feeling")
    if fam == "T4_negated_feeling":   # hi / gu / mr accepted outputs
        return ("NEGATED_WANT", "scorer_correct", "negated feeling realized as a negated want (act error); accepted by the gate")
    if i == "gu-T5_action_object-EAT+RICE":
        return ("SCORER_LEXICAL_GAP", "scorer", "'મને જમવું છે ભાત' keeps 'I want to eat rice' but with awkward word order; no marker from the request list")
    if i == "gu-T6_help_person-CALL+DOCTOR":
        return ("SCORER_LEXICAL_GAP", "scorer", "'I want to phone the doctor' is recoverable; case marking is nonstandard (મને / no ને); scorer finds no request marker")
    if lang == "gu" and fam == "T3_feeling":
        return ("UNGRAMMATICAL", "scorer_correct", "echoes the prompt prefix ('હું કહું') into the sentence; not a well-formed Gujarati feeling statement")
    if lang in ("gu", "mr") and fam in ("T5_action_object", "T6_help_person"):
        return ("UNGRAMMATICAL", "scorer_correct" if lang == "gu" else "scorer_artifact", "word order/agreement broken or the request turned into a question; "
                "the scorer's wrong-act flag for Marathi comes from the list treating आहे as a feeling marker" if lang == "mr" else "word order/agreement broken")
    return ("UNCLASSIFIED", "", "")


out = []
for r in rows:
    cat, verdict, note = classify(r)
    out.append(dict(cohort=r["cohort"], id=r["id"], lang=r["lang"], family=r["family"], output_text=r["output_text"], category=cat, scorer_verdict=verdict, note=note,
                    classified_by="assistant (not a native speaker); native-speaker confirmation pending"))
write_csv(OUT / "A3_failure_classification.csv", out)
cnt = collections.Counter((o["cohort"], o["category"]) for o in out)
summary = dict(n_rows=len(out), by_cohort_and_category={f"{a}|{b}": v for (a, b), v in sorted(cnt.items())},
               accepted_model_genuine=sum(v for (a, b), v in cnt.items() if a == "accepted_model" and b != "SCORER_LEXICAL_GAP"),
               accepted_model_scorer_gap=cnt[("accepted_model", "SCORER_LEXICAL_GAP")],
               fallback_and_template_only_scorer_gap=cnt[("template_fallback", "SCORER_LEXICAL_GAP")] + cnt[("template_only", "SCORER_LEXICAL_GAP")],
               unclassified=cnt[("accepted_model", "UNCLASSIFIED")] + cnt[("template_fallback", "UNCLASSIFIED")] + cnt[("template_only", "UNCLASSIFIED")])
(OUT / "A3_classification_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=1))
