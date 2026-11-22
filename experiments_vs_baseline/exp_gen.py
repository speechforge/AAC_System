"""Experiment 4: sentence-generation effectiveness of the deterministic realiser + semantic gate, identical concept suite in en/hi/gu/mr.
Compared inside our system against the 'literal' output (symbols spoken as a bare word list, what a plain symbol grid does)."""
import sys, json, re, itertools, collections
sys.path.insert(0, "../indic-generative-aac/backend")
import aac_lexicon as L
from templates import realize
from pipeline import normalize_request
from semantic import SemanticValidator
V = SemanticValidator()
OBJ = L.OBJECTS; ACT = L.ACTIONS; FEEL = [f for f in L.FEELINGS if f in L.BOARD]
cases = []   # (name, concept ids, gold_act, gold_negation, determinate)
for o in OBJ:
    cases += [("obj", [o], "REQUEST", False, True), ("want+obj", ["WANT", o], "REQUEST", False, True), ("me+want+obj", ["ME", "WANT", o], "REQUEST", False, True),
              ("please+obj", ["PLEASE", o], "REQUEST", False, True), ("no+want+obj", ["NO", "WANT", o], "REQUEST", True, True)]
    if L.BOARD[o]["cat"] == "food": cases.append(("more+obj", ["MORE", o], "REQUEST", False, True))
for a in ACT: cases.append(("me+action", ["ME", a], "REQUEST", False, True))
for f in FEEL:
    cases += [("feeling", [f], "FEELING", False, True), ("me+feeling", ["ME", f], "FEELING", False, True), ("no+feeling", ["NO", f], "FEELING", True, True)]
    for o in ("WATER", "MEDICINE", "FOOD"):
        if o in L.BOARD: cases.append(("feeling+obj", [f, o], "FEELING_REQUEST", False, True))
cases += [("help", ["HELP"], "REQUEST", False, True), ("please+help", ["PLEASE", "HELP"], "REQUEST", False, True)]
for p in L.PEOPLE: cases.append(("person-alone(ambiguous)", [p], None, False, False))
for o in OBJ[:4]: cases.append(("double-negation(ambiguous)", ["NO", "NO", o], None, False, False))
cases += [("two-feelings(ambiguous)", ["HAPPY", "SAD"], None, False, False), ("two-feelings(ambiguous)", ["TIRED", "ANGRY"], None, False, False)]
NEG = {"en": r"\b(not|no|don't|do not|never)\b", "hi": r"(नहीं|मत)", "gu": r"(નથી|નહીં|ના\b|નહિ)", "mr": r"(नको|नाही|नये)"}
out = {}
for lang in L.LANGS:
    S = collections.Counter(); rows = collections.defaultdict(collections.Counter)
    for name, ids, gact, gneg, det in cases:
        if any(i not in L.BOARD for i in ids): continue
        items = [dict(cid=i, label=L.BOARD[i][lang]) for i in ids]
        content_ids = [i for i in ids if i not in ("NO", "WANT", "ME", "PLEASE", "MORE")]
        for sysname in ("ours_template+gate", "literal_symbols"):
            S_ = rows[sysname]; S_["n"] += 1 if det else 0; S_["n_amb"] += 0 if det else 1
            if sysname == "literal_symbols":
                text = " ".join(it["label"] for it in items); status = "ok"
            else:
                r = realize(items, lang); text, status = r["text"], r["status"]
            if not det:
                S_["abstained_correctly"] += status != "ok"; S_["amb_invented"] += status == "ok"; continue
            if status != "ok" or not text:
                S_["no_output"] += 1; continue
            ctx = normalize_request(dict(entities=[x["label"] for x in items], concept_ids=ids, language=lang, act=gact, act_source="user", negation=gneg))
            acc, d = V.validate(ctx, {}, text, lang)
            S_["gate_accept"] += acc
            S_["act_ok"] += d["intent_match"]; S_["entity_ok"] += d["entity_match"]; S_["neg_ok"] += d["negation_match"]
            S_["no_additions"] += not d["unsupported_additions"]
            S_["neg_indep_ok"] += (bool(re.search(NEG[lang], text.lower())) == gneg)
            S_["entity_indep_ok"] += all(L.canon(L.BOARD[c][lang]).split("/")[0].strip()[:3] in L.canon(text) for c in content_ids)
            lat = sum(ch.isascii() and ch.isalpha() for ch in text)
            S_["native_script_ok"] += (lat == 0) if lang != "en" else True
    out[lang] = {k: dict(v) for k, v in rows.items()}
    print(lang, json.dumps(out[lang]["ours_template+gate"]), flush=True)
out["n_cases"] = len(cases)
# examples
ex = {}
for lang in L.LANGS:
    ex[lang] = []
    for ids, act, neg in ((["WATER"], None, None), (["NO", "WANT", "MEDICINE"], None, None), (["PAIN", "MEDICINE"], None, None), (["TIRED"], None, None), (["ME", "GO", "SCHOOL"], None, None)):
        if any(i not in L.BOARD for i in ids): continue
        it = [dict(cid=i, label=L.BOARD[i][lang]) for i in ids]; r = realize(it, lang); ex[lang].append((" ".join(x["label"] for x in it), r["text"], r["status"]))
out["examples"] = ex
json.dump(out, open("results/gen.json", "w"), indent=1, ensure_ascii=False)
