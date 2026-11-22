#!/usr/bin/env python3
"""Independent automatic scorer. Imports nothing from the backend.

Per (scenario, output) it returns boolean flags:
  retention      : fraction of required content-concept instances present   (denominator: concept instances)
  polarity_ok    : negation marker present  ==  gold_neg                      (denominator: all scenarios)
  polarity_drop  : gold_neg and no negation marker      (dropped negation)
  polarity_spur  : not gold_neg and negation marker     (spurious negation)
  act_ok         : the gold communicative act is expressed (request marker / feeling marker without request marker)
  act_wrong      : the opposite act is expressed (e.g. 'I want Tired')
  act_missing    : telegraphic output (neither act expressed)
  unsupported    : a board concept that was NOT selected (or an extra distractor: time, venue, hunger) appears
  offtask        : refusal / meta text / third-person 'the user' / empty / very long / Latin leakage in an Indic target
  script_ok      : output is in the target script
  success        : retention==1 and polarity_ok and act_ok and not unsupported and not offtask and script_ok
Limits: lexical, no morphology/grammaticality judgement; lexicon NOT native-speaker reviewed.
"""
import json, re, unicodedata, pathlib

HERE = pathlib.Path(__file__).resolve().parent
LEX = json.loads((HERE / "fixtures/lexicon.json").read_text(encoding="utf-8"))
BOARD = json.loads((HERE / "fixtures/board_vocab.json").read_text(encoding="utf-8"))["vocab"]
NFC = lambda s: unicodedata.normalize("NFC", s)
PUNCT = re.compile(r"[\.,!\?;:।\"“”‘’\(\)\[\]/\\]")


def norm(t):
    t = NFC(t or "").lower()
    t = t.replace("’", "'")
    t = PUNCT.sub(" ", t).replace("'", "'")
    return re.sub(r"\s+", " ", t).strip()


def toks(t):
    return norm(t).split()


def _match_en(form, text):
    if form.startswith("="):
        return re.search(rf"(?<![a-z']){re.escape(form[1:])}(?![a-z'])", text) is not None
    if form == "n't":
        return "n't" in text
    return re.search(rf"(?<![a-z']){re.escape(form)}(?:s|es|ed|d|ing)?(?![a-z'])", text) is not None


def _match_in(form, text, tokens):
    form_n = NFC(form)
    if form_n.startswith("="):
        return form_n[1:] in tokens
    return form_n in text


def has(forms, lang, text, tokens):
    return any((_match_en(f, text) if lang == "en" else _match_in(f, text, tokens)) for f in forms)


def forms_for(cid, lang, code_mix):
    langs = ["hi", "en"] if code_mix else [lang]
    out = []
    for l in langs:
        out += LEX["concepts"].get(cid, {}).get(l, [])
    return out


def _lang_keys(lang, code_mix):
    return ["hi", "en"] if code_mix else [lang]


def _any(table, lang, code_mix, text, tokens):
    for l in _lang_keys(lang, code_mix):
        if has(table[l], l, text, tokens):
            return True
    return False


_DISTR = {}


def distractors(lang, code_mix, selected):
    """Forms of every non-selected board concept (closed vocabulary) + extra distractors."""
    key = (lang, code_mix, tuple(sorted(selected)))
    if key in _DISTR:
        return _DISTR[key]
    forms = []  # (form, lang_key)
    for l in _lang_keys(lang, code_mix):
        for cat in LEX["distractor_categories"]:
            for s in BOARD[cat]:
                if s["id"] in selected:
                    continue
                if s["id"] in LEX["concepts"]:
                    fs = LEX["concepts"][s["id"]][l]
                else:
                    lab = norm(s[l])
                    fs = [lab] if len(lab) >= 3 else ["=" + lab]
                    if l == "en":
                        fs = [x.strip() for x in re.split(r"\s*/\s*", s["en"].lower())]
                forms += [(f, l) for f in fs]
        forms += [(f, l) for f in LEX["extra_distractors"][l]]
    _DISTR[key] = forms
    return forms


def score(sc, text):
    lang, cm = sc["lang"], sc["code_mix"]
    t = norm(text)
    tk = t.split()
    selected = set(sc["content_concepts"])
    # --- concept retention
    present = [_any_concept(c, lang, cm, t, tk) for c in sc["content_concepts"]]
    retention = sum(present) / max(1, len(present))
    # --- polarity
    has_neg = _any(LEX["negation"], lang, cm, t, tk)
    gold_neg = bool(sc["gold_neg"])
    polarity_ok = has_neg == gold_neg
    # --- act
    req = _any(LEX["request_markers"], lang, cm, t, tk)
    fee = _any(LEX["feeling_markers"], lang, cm, t, tk)
    if sc["gold_act"] == "request":
        act_expressed = req
        act_wrong = (not req) and fee
    else:
        act_expressed = fee and not req
        act_wrong = req
    act_missing = (not act_expressed) and (not act_wrong)
    # --- unsupported content (closed board vocabulary + distractors), excluding overlaps with selected forms
    sel_forms = [NFC(f).lstrip("=") for c in sc["content_concepts"] for f in forms_for(c, lang, cm)]
    unsupported_hits = []
    for f, l in distractors(lang, cm, selected):
        hit = _match_en(f, t) if l == "en" else _match_in_token(f, t, tk)
        if hit:
            fb = NFC(f).lstrip("=")
            if any((fb in sf) or (sf in fb) for sf in sel_forms):
                continue
            unsupported_hits.append(f)
    # --- off-task / script
    latin = sum(ch.isascii() and ch.isalpha() for ch in text or "")
    letters = sum(ch.isalpha() for ch in text or "") or 1
    meta = any(p in t for p in LEX["meta_patterns_en"]) if (lang == "en" or cm) else False
    if lang == "en":
        script_ok = latin / letters > 0.8
    elif lang == "gu":
        script_ok = any("઀" <= ch <= "૿" for ch in text or "")
    else:
        script_ok = any("ऀ" <= ch <= "ॿ" for ch in text or "")
    leak = (lang != "en" and not cm and latin / letters > 0.3)
    offtask = (len(tk) == 0) or (len(tk) > 25) or meta or leak
    unsupported = len(unsupported_hits) > 0
    success = (retention == 1.0 and polarity_ok and act_expressed and not unsupported and not offtask and script_ok)
    return dict(retention=retention, n_concepts=len(present), n_present=sum(present), polarity_ok=polarity_ok,
                polarity_drop=(gold_neg and not has_neg), polarity_spur=((not gold_neg) and has_neg),
                act_ok=act_expressed, act_wrong=act_wrong, act_missing=act_missing,
                unsupported=unsupported, unsupported_hits=unsupported_hits, offtask=offtask, script_ok=script_ok,
                success=success)


def _any_concept(c, lang, cm, t, tk):
    for l in _lang_keys(lang, cm):
        if has(LEX["concepts"].get(c, {}).get(l, []), l, t, tk):
            return True
    return False


def _match_in_token(form, text, tokens):
    f = NFC(form)
    if f.startswith("="):
        return f[1:] in tokens
    if " " in f:
        return f in text
    # token-prefix match for >=3 chars, exact for shorter
    if len(f) >= 3:
        return any(tok.startswith(f) for tok in tokens)
    return f in tokens


if __name__ == "__main__":  # smoke tests of the scorer itself (no system involved)
    sc = lambda **k: dict(lang=k.get("lang", "en"), code_mix=False, content_concepts=k["c"], gold_neg=k.get("neg", False), gold_act=k.get("act", "request"))
    cases = [
        (sc(c=["WATER"]), "I want water.", dict(success=True)),
        (sc(c=["WATER"]), "I want No Water.", dict(polarity_ok=False, polarity_spur=True)),
        (sc(c=["PIZZA"], neg=True), "I do not want pizza.", dict(success=True)),
        (sc(c=["PIZZA"], neg=True), "I want pizza.", dict(polarity_drop=True)),
        (sc(c=["TIRED"], act="feeling"), "I want Tired.", dict(act_wrong=True)),
        (sc(c=["TIRED"], act="feeling"), "I am tired.", dict(success=True)),
        (sc(c=["WATER"]), "I need to eat at the restaurant.", dict(unsupported=True)),
        (sc(c=["TIRED"], act="feeling"), "I'm sorry, but I can't generate text for you.", dict(offtask=True)),
        (sc(c=["WATER"], lang="hi"), "मुझे पानी चाहिए।", dict(success=True)),
        (sc(c=["WATER"], lang="hi", neg=True), "मुझे पानी नहीं चाहिए।", dict(success=True)),
        (sc(c=["WATER"], lang="gu"), "મને પાણી જોઈએ છે.", dict(success=True)),
        (sc(c=["WATER"], lang="mr", neg=True), "मला पाणी नको आहे.", dict(success=True)),
        (sc(c=["EAT", "RICE"], lang="hi"), "मुझे चावल खाना है।", dict(retention=1.0)),
    ]
    bad = 0
    for s, txt, exp in cases:
        r = score(s, txt)
        for k, v in exp.items():
            if r[k] != v:
                bad += 1
                print("FAIL", txt, k, "expected", v, "got", r[k], r["unsupported_hits"])
    print("scorer self-test:", "OK" if bad == 0 else f"{bad} failures", f"({len(cases)} cases)")
