#!/usr/bin/env python3
"""PHASE A (cont.) -- audit the ORIGINAL scorer (score.py, unmodified) with scripted probes and over all archived outputs.
Questions answered: (1) what does the off-task flag really catch (model refusal vs legitimate user refusal)?  (2) is negation scoped to the
relevant clause?  (3) can first person be implicit, and is third person caught outside English?  (4) do valid inflections/paraphrases fail
lexical matching?  (5) which scorer failures explain the 8 template-only and 6 template-fallback failures?
Outputs: results/audit/A5_scorer_probes.csv, A5_offtask_causes.json.  No model is loaded."""
import collections, json, pathlib, sys, csv
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

S1 = load_module("score_v1", ARCH / "score.py")
OUT = V2 / "results/audit"
LEX = json.loads((ARCH / "fixtures/lexicon.json").read_text(encoding="utf-8"))


def sc(lang, concepts, neg=False, act="request"):
    return dict(lang=lang, code_mix=False, content_concepts=concepts, gold_neg=neg, gold_act=act)


# (question, language, concepts, gold_neg, gold_act, text, EXPECTED verdict by a careful reader, note)
PROBES = [
    ("refusal meaning", "en", ["PIZZA"], True, "request", "I can't have pizza.", True, "legitimate negated request; 'can't' is both a negator and an off-task (model-refusal) pattern"),
    ("refusal meaning", "en", ["PIZZA"], True, "request", "I don't want pizza.", True, "control"),
    ("refusal meaning", "en", ["WATER"], False, "request", "I'm sorry, but I can't generate that.", False, "genuine model refusal"),
    ("negation scope", "en", ["TIRED"], True, "feeling", "I am tired, I do not know.", False, "negator in an unrelated clause; the selected feeling is not negated"),
    ("negation scope", "en", ["TIRED"], True, "feeling", "I am not tired.", True, "control"),
    ("negation scope", "hi", ["TIRED"], True, "feeling", "मैं थका हुआ हूँ, मुझे पानी नहीं चाहिए।", False, "negation attaches to 'water' (added), not to 'tired'"),
    ("perspective", "en", ["WATER"], False, "request", "Water, please.", True, "implicit first person is valid"),
    ("perspective", "en", ["WATER"], False, "request", "He wants water.", False, "third-person report"),
    ("perspective", "en", ["WATER"], False, "request", "The user wants water.", False, "third-person report"),
    ("perspective", "hi", ["WATER"], False, "request", "पानी चाहिए।", True, "implicit first person (pro-drop) is valid Hindi"),
    ("perspective", "hi", ["WATER"], False, "request", "उसे पानी चाहिए।", False, "third person: 'he/she needs water'"),
    ("perspective", "gu", ["WATER"], False, "request", "તેને પાણી જોઈએ છે.", False, "third person: 'he/she wants water'"),
    ("inflection/paraphrase", "gu", ["EAT", "RICE"], False, "request", "મને ભાત જમવો છે.", True, "valid desire construction 'I want to eat rice' (no જોઈએ)"),
    ("inflection/paraphrase", "gu", ["NO", "TIRED"][1:], True, "feeling", "મને થાકેલું લાગતું નથી.", True, "valid 'I do not feel tired'; verb લાગતું not in the feeling-marker list"),
    ("inflection/paraphrase", "hi", ["DRINK", "WATER"], False, "request", "मुझे पानी पीना है।", True, "valid 'I want to drink water'"),
    ("inflection/paraphrase", "mr", ["EAT", "RICE"], False, "request", "मला भात खायचा आहे.", True, "valid 'I want to eat rice'"),
    ("inflection/paraphrase", "en", ["WATER"], False, "request", "I would love some water.", True, "valid request paraphrase ('would like' is listed, 'would love' is not)"),
    ("inflection/paraphrase", "en", ["WATER"], False, "request", "Could I have some water, please?", True, "valid polite request"),
    ("concept substitution", "en", ["WATER"], False, "request", "I want juice.", False, "substituted concept"),
    ("added content", "en", ["TIRED"], False, "feeling", "I am tired because of the long trip.", False, "added reason not selected (not in the distractor lexicon)"),
]
rows = []
for q, lang, cs, neg, act, text, expected, note in PROBES:
    r = S1.score(sc(lang, cs, neg, act), text)
    rows.append(dict(question=q, lang=lang, concepts="+".join(cs), gold_neg=neg, gold_act=act, text=text, expected_success=expected, scorer_success=r["success"],
                     agrees=(expected == r["success"]), kind=("false_accept" if r["success"] and not expected else "false_reject" if expected and not r["success"] else "ok"),
                     offtask=r["offtask"], act_ok=r["act_ok"], polarity_ok=r["polarity_ok"], unsupported_hits="|".join(r["unsupported_hits"]), note=note))
write_csv(OUT / "A5_scorer_probes.csv", rows)

# ---- off-task causes over every archived output
meta = LEX["meta_patterns_en"]
causes = collections.defaultdict(lambda: collections.Counter())
examples = collections.defaultdict(list)
for r in csv.DictReader(open(ARCH / "results/scored.csv", encoding="utf-8")):
    if r["offtask"] != "True":
        continue
    t = S1.norm(r["text"]); toks = t.split()
    cause = []
    if len(toks) == 0: cause.append("empty")
    if len(toks) > 25: cause.append("longer_than_25_tokens")
    hit = [p for p in meta if p in t] if r["lang"] == "en" or r["code_mix"] == "True" else []
    for p in hit: cause.append(f"meta:{p}")
    if r["lang"] != "en" and not r["code_mix"] == "True":
        lat = sum(ch.isascii() and ch.isalpha() for ch in r["text"]); let = sum(ch.isalpha() for ch in r["text"]) or 1
        if lat / let > 0.3: cause.append("latin_leak_in_indic")
    for c in (cause or ["unknown"]):
        causes[f"{r['system']}|{r['cond']}"][c] += 1
        if len(examples[c]) < 3: examples[c].append(r["text"])
(OUT / "A5_offtask_causes.json").write_text(json.dumps(dict(causes={k: dict(v) for k, v in causes.items()}, examples=dict(examples),
                                                          scorer_meta_patterns=meta,
                                                          note="'off-task' bundles model refusals/meta text, the English third-person pattern 'the user', empty/long text and Latin leakage. It is NOT a test of a user's own refusal; the pattern \"can't\" would flag a legitimate user refusal."),
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
fa = [r for r in rows if r["kind"] == "false_accept"]; fr = [r for r in rows if r["kind"] == "false_reject"]
print(f"probes: {len(rows)} | agree {sum(r['agrees'] for r in rows)} | false accepts {len(fa)} | false rejects {len(fr)}")
for r in fa + fr:
    print(f"  {r['kind']:13s} [{r['question']}] {r['lang']} {r['text']}")
