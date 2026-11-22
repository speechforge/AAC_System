#!/usr/bin/env python3
"""Scorer v2 (automatic, lexical).  The archived scorer (paper/CLAUDE_WRITTEN/naacl2027_demo/eval/score.py, v1) is kept
unchanged; every saved output can be scored with both versions (src/rescore_archived.py) so the effect of the change is measured.

What changed from v1 (each change answers a finding of the Phase-A audit, results/audit/A3, A5):
  1. Request and feeling markers cover valid desire and state constructions the v1 lists missed (Gujarati 'laagatu nathi',
     'jamvu chhe', 'mann chhe'; Hindi 'mujhe ... naa hai'; Marathi 'yacha aahe'; English 'would love', 'could I have').
  2. Polarity is scoped: a negator must sit in a clause that carries a selected concept (v1 accepted any negator anywhere).
  3. 'Off-task' is split into model_refusal (sorry / cannot generate), meta (quotes, translation talk), third_person
     (locale pronouns; implicit first person stays valid), too_long, empty and latin_leak.  v1 pattern "can't" no longer flags a
     user's own negated request, and "the user" is reported as a perspective error rather than a refusal.
  4. Added reason and time words are part of 'unsupported'.
  5. Supports act 'feeling_request' (both a state and a request), 'greeting', personal (typed) words and the quantity MORE.
Success = every selected concept present and polarity correct (scoped) and gold act expressed and no added concept and
not off-task and correct script.  Lexical only: no grammaticality judgement; the lexicon is not native-reviewed.
Independent of backend/semantic.py (separate code and tables).
"""
import json, pathlib, re, sys, unicodedata

ARCH = pathlib.Path("/home/linux/Documents/aac_system_november_11/AAC_System_merged/paper/CLAUDE_WRITTEN/naacl2027_demo/eval")
LEX = json.loads((ARCH / "fixtures/lexicon.json").read_text(encoding="utf-8"))
BOARD = json.loads((ARCH / "fixtures/board_vocab.json").read_text(encoding="utf-8"))["vocab"]
NFC = lambda s: unicodedata.normalize("NFC", s)
VERSION = "scorer-v2"

# additions (hand-written for v2; concepts absent from the v1 lexicon and new locale constructions)
ADD_CONCEPTS = {
    "GO": {"en": ["go", "going", "went"], "hi": ["जाना", "जाने", "जाऊं", "जाऊँ", "=जा"], "gu": ["જવ", "જાઉં", "જાય", "જઈશ"], "mr": ["जाण", "जावे", "जाऊ", "जायचे", "=जा"]},
    "STUDY": {"en": ["study", "studying", "learn"], "hi": ["पढ़", "पढ"], "gu": ["ભણ", "અભ્યાસ"], "mr": ["अभ्यास", "शिकण"]},
    "PLAY": {"en": ["play"], "hi": ["खेल"], "gu": ["રમ", "રમવ", "રમે", "રમી", "રમું"], "mr": ["खेळ"]},
    "SLEEP": {"en": ["sleep", "nap", "rest"], "hi": ["सोना", "सोने", "सो", "नींद"], "gu": ["ઊંઘ", "સૂ", "સુવ"], "mr": ["झोप"]},
    "BATH": {"en": ["bath", "bathe", "shower"], "hi": ["नहा"], "gu": ["નાહ", "નહાવ"], "mr": ["आंघोळ"]},
    "WRITE": {"en": ["write"], "hi": ["लिख"], "gu": ["લખ"], "mr": ["लिह"]},
    "LOOK": {"en": ["look", "see", "watch"], "hi": ["देख"], "gu": ["જોવ", "જુઓ"], "mr": ["पाह", "बघ"]},
    "FATHER": {"en": ["father", "dad", "papa"], "hi": ["पिता", "पापा"], "gu": ["પિતા", "પપ્પા"], "mr": ["बाबा", "वडील"]},
    "SISTER": {"en": ["sister"], "hi": ["बहन"], "gu": ["બહેન"], "mr": ["बहीण", "बहिण", "ताई"]},
    "BROTHER": {"en": ["brother"], "hi": ["भाई"], "gu": ["ભાઈ"], "mr": ["भाऊ", "भावा", "दादा"]},
    "TEACHER": {"en": ["teacher"], "hi": ["शिक्षक", "अध्यापक"], "gu": ["શિક્ષક"], "mr": ["शिक्षक"]},
    "FRIEND": {"en": ["friend"], "hi": ["दोस्त", "मित्र"], "gu": ["મિત્ર", "દોસ્ત"], "mr": ["मित्र", "दोस्त"]},
    "MEDICINE": {"en": ["medicine", "medication", "pills"], "hi": ["दवा", "दवाई"], "gu": ["દવા"], "mr": ["औषध", "गोळ्या"]},
    "PAIN": {"en": ["pain", "hurt", "ache"], "hi": ["दर्द"], "gu": ["દુખાવો", "દર્દ", "દુખ"], "mr": ["वेदना", "दुखत"]},
    "GOOD": {"en": ["good", "well", "fine"], "hi": ["अच्छा", "अच्छे", "अच्छी"], "gu": ["સારું", "સારો", "સારી"], "mr": ["चांगले", "चांगला", "चांगली"]},
    "BAD": {"en": ["bad", "terrible", "awful"], "hi": ["बुरा", "बुरी", "खराब"], "gu": ["ખરાબ"], "mr": ["वाईट"]},
    "HOME": {"en": ["home", "house"], "hi": ["घर"], "gu": ["ઘર"], "mr": ["घर"]},
    "SCHOOL": {"en": ["school"], "hi": ["स्कूल", "विद्यालय"], "gu": ["શાળા", "સ્કૂલ"], "mr": ["शाळा", "स्कूल"]},
    "NAMASTE": {"en": ["hello", "hi", "namaste"], "hi": ["नमस्ते", "नमस्कार"], "gu": ["નમસ્તે"], "mr": ["नमस्ते", "नमस्कार"]},
    "NOSE": {"en": ["nose"], "hi": ["नाक"], "gu": ["નાક"], "mr": ["नाक"]},
    "HELP_PLEASE": {"en": ["help"], "hi": ["मदद"], "gu": ["મદદ"], "mr": ["मदत"]},
}
# an inflected or alternative form that v1 missed (kept separate so the origin of each change is visible)
PATCH_CONCEPTS = {
    "WATER": {"mr": ["पाण्य"]},
    "MILK": {"mr": ["दुध"], "gu": ["દુધ"]},
    "EAT": {"mr": ["खाण"], "hi": ["खाने", "खाऊं", "खाता", "खाती"], "gu": ["જમવ", "જમું", "જમે", "ખાવા", "ખાવું", "ખાવ"]},
    "FOOD": {"hi": ["खाने"]},
    "TIRED": {"hi": ["थका", "थकी", "थकान"], "mr": ["थकवा"]},
    "SCARED": {"gu": ["ડરેલ", "ડરી", "ડરતો", "ડર્યો"]},
}
REQ = {
    "en": [r"\bwant", r"\bneed", r"would (?:like|love)", r"i'd (?:like|love)", r"\bplease\b", r"(?:can|could|may) i (?:have|get)", r"give me", r"\bwish\b", r"\brequire", r"help me"],
    "hi": ["चाहिए", "चाहिये", "चाहता", "चाहती", "चाहते", "चाहूं", "चाहूँ", "जरूरत", "ज़रूरत", "दीजिए", "दीजिये", "कृपया", "कीजिए", "(?<!\\S)दो(?!\\S)", "(?<!\\S)दें(?!\\S)", "का मन",
           "मुझे\\s+.*(?:ना|ने|नी)\\s+(?:नहीं\\s+)?(?:है|हैं)(?!\\S)"],
    "gu": ["જોઈએ", "જોઈત", "જરૂર", "આપો", "ઈચ્છ", "માગ", "મન છે", "મન નથી", "કૃપા", "મારે", "(?:વું|વો|વી|વા|વાનું)\\s+(?:મન\\s+)?(?:છે|નથી)(?!\\S)"],
    "mr": ["हवे", "हवा", "हवी", "पाहिजे", "नको", "द्या", "इच्छा", "मागत", "गरज", "कृपया", "करा(?!\\S)", "(?:यचा|यचे|यची|यचं)\\s+(?:आहे|नाही)"],
}
STATE = {
    "en": [r"\bi am\b", r"\bi'm\b", r"\bi feel\b", r"\bfeeling\b", r"\bi do not feel\b", r"\bi don't feel\b", r"\bi'm not\b", r"\bi am not\b"],
    "hi": ["हूँ", "हूं", "महसूस", "लग रहा", "लग रही", "लगता", "लगती", "आ रहा", "आ रही", "हो रहा", "हो रही", "थकान"],
    "gu": ["છું", "લાગે", "લાગ્યો", "લાગી", "લાગતો", "લાગતી", "લાગતું", "અનુભવ", "થાય", "થતો", "આવે", "આવતો", "(?<!\\S)હું(?!\\S)"],
    "mr": ["आहे", "वाटते", "वाटत", "वाटतो", "वाटतेय", "आला", "आली", "आलेला", "आलेली", "होत", "(?<!\\S)मी(?!\\S)"],
}
THIRD = {
    "en": [r"\bthe user\b", r"\buser's\b", r"\bthe patient\b", r"\bhe\b", r"\bshe\b", r"\bthey\b", r"\bhis\b", r"\bher\b", r"\bthem\b"],
    "hi": ["(?<!\\S)(?:वह|वो|उसे|उसको|उसका|उसकी|उसके|उन्हें|उनका|वे)(?!\\S)", "उपयोगकर्ता", "यूज़र|यूजर"],
    "gu": ["(?<!\\S)(?:તે|તેને|તેણે|તેનું|તેની|તેના|તેઓ|તેમને)(?!\\S)", "વપરાશકર્તા"],
    "mr": ["(?<!\\S)(?:तो|ती|ते|त्याला|तिला|त्यांना|त्याचा|त्याची|त्याचे)(?!\\S)", "वापरकर्ता"],
}
REFUSAL_EN = [r"sorry", r"cannot (?:generate|fulfill|help|assist)", r"can't (?:generate|fulfill|help with|assist)", r"as an ai", r"language model", r"ethical", r"guidelines", r"copyright", r"instead, i"]
META = [r"selected symbol", r"\bmeans\b", r"in (?:hindi|gujarati|marathi|english)", r"translat", r"input sequence", r"इनपुट क्रम", r"ઈનપુટ ક્રમ", r"[\"“”]", r"मतलब", r"અર્થ", r"म्हणजे"]
REASON_TIME = {
    "en": [r"\bbecause\b", r"\bso that\b", r"\bsince i\b", r"\btoday\b", r"\btomorrow\b", r"\bnow\b", r"\blater\b", r"\bsoon\b", r"\bmorning\b", r"\bevening\b", r"\bnight\b", r"\bbreakfast\b", r"\blunch\b", r"\bdinner\b"],
    "hi": ["क्योंकि", "इसलिए", "ताकि", "(?<!\\S)आज(?!\\S)", "(?<!\\S)कल(?!\\S)", "(?<!\\S)अभी(?!\\S)", "सुबह", "शाम", "रात"],
    "gu": ["કારણ કે", "તેથી", "આજે", "કાલે", "હમણાં", "સવારે", "સાંજે", "રાત્રે"],
    "mr": ["कारण", "म्हणून", "(?<!\\S)आज(?!\\S)", "उद्या", "आत्ता", "सकाळी", "संध्याकाळी", "रात्री"],
}
MORE = {"en": r"\bmore\b", "hi": r"(?<!\S)और(?!\S)", "gu": r"(વધુ|વધારે|ફરીથી)", "mr": r"(आणखी|अजून|जास्त)"}
NEG_EXTRA = {"hi": [], "gu": [], "mr": [], "en": []}
GREET = {"en": [r"\bhello\b", r"\bhi\b", r"\bnamaste\b", r"\bgreet"], "hi": ["नमस्ते", "नमस्कार"], "gu": ["નમસ્તે", "નમસ્કાર"], "mr": ["नमस्ते", "नमस्कार"]}


def canon(t):
    t = NFC(t or "").casefold().replace("’", "'")
    t = t.replace("़", "").replace("‍", "").replace("‌", "").replace("ँ", "ं")
    t = re.sub(r"[\.,!\?;:।\(\)\[\]/\\]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def forms(cid, lang):
    f = list(LEX["concepts"].get(cid, {}).get(lang, [])) + ADD_CONCEPTS.get(cid, {}).get(lang, []) + PATCH_CONCEPTS.get(cid, {}).get(lang, [])
    if not f and cid in {s["id"] for c in BOARD.values() for s in c}:
        lab = canon(next(s[lang] for c in BOARD.values() for s in c if s["id"] == cid))
        f = [lab if len(lab) >= 3 else "=" + lab]
    return [canon(x) if not x.startswith("=") else "=" + canon(x[1:]) for x in f]


def hit(form, text, toks, lang):
    if lang == "en":
        if form.startswith("="):
            return re.search(rf"(?<![a-z']){re.escape(form[1:])}(?![a-z'])", text) is not None
        return re.search(rf"(?<![a-z']){re.escape(form)}(?:s|es|ed|d|ing)?(?![a-z'])", text) is not None
    if form.startswith("="):
        return form[1:] in toks
    if " " in form:
        return form in text
    return any(t.startswith(form) for t in toks)          # short forms written without '=' keep v1's inflection behaviour (token prefix)


def present(cid, lang, text, toks):
    return any(hit(f, text, toks, lang) for f in forms(cid, lang))


def rx_any(patterns, text):
    return any(re.search(p, text) for p in patterns)


def neg_in(text, lang):
    t = text
    return any((_neg_hit(f, t, lang)) for f in LEX["negation"][lang])


def _neg_hit(form, text, lang):
    f = NFC(form)
    toks = text.split()
    if lang == "en":
        if f == "n't":
            return "n't" in text
        return re.search(rf"(?<![a-z']){re.escape(f.lstrip('='))}(?![a-z'])", text) is not None
    return (f[1:] in toks) if f.startswith("=") else (canon(f) in text)


def clauses(raw, lang):
    t = NFC(raw or "").casefold().replace("’", "'")
    parts = re.split(r"[\.;!\?।,]|(?<!\S)(?:but|however|yet|लेकिन|परंतु|पर|मगर|પણ|પરંતુ|पण)(?!\S)", t)
    return [canon(p) for p in parts if canon(p)]


_DIS = {}


def distractors(lang, selected):
    key = (lang, tuple(sorted(selected)))
    if key in _DIS:
        return _DIS[key]
    out = []
    for cat in LEX["distractor_categories"]:
        for s in BOARD[cat]:
            if s["id"] in selected:
                continue
            out += [(f, lang) for f in forms(s["id"], lang)]
    for cid in ("GO", "STUDY", "PLAY", "SLEEP", "BATH", "WRITE", "LOOK", "FATHER", "SISTER", "BROTHER", "TEACHER", "FRIEND", "MEDICINE", "PAIN", "HOME", "SCHOOL"):
        if cid not in selected:
            out += [(f, lang) for f in forms(cid, lang)]
    out += [(canon(f) if not f.startswith("=") else f, lang) for f in LEX["extra_distractors"][lang]]
    _DIS[key] = out
    return out


def score(sc, text, custom_words=None):
    lang, cm = sc["lang"], sc.get("code_mix", False)
    raw = text or ""
    t = canon(raw)
    tk = t.split()
    selected = [c for c in sc["content_concepts"] if not str(c).startswith("~")]
    customs = list(custom_words or sc.get("custom_words") or []) + [c[1:] for c in sc["content_concepts"] if str(c).startswith("~")]
    L = ["hi", "en"] if cm else [lang]
    def _pres(c):
        if lang == "hi" and c in ("EAT", "FOOD") and "EAT" in selected and "FOOD" in selected:   # Hindi 'khana' names both: both are present only if it occurs twice (or an inflected eat form)
            return (t.count("खाना") + t.count("खाने")) >= 2 or any(present("EAT", l, t, tk) for l in L if l == "hi" and re.search("खाने|खाऊं|खाता|खाती|खाया", t))
        return any(present(c, l, t, tk) for l in L)
    pres = [_pres(c) for c in selected] + [(canon(w) in t) or any(x.startswith(canon(w)[:max(3, len(canon(w)) - 1)]) for x in tk) for w in customs]
    more_ok = True
    if sc.get("more"):
        more_ok = any(re.search(MORE[l], t) for l in L)
    n_c = len(pres)
    retention = sum(pres) / max(1, n_c)
    # polarity, scoped
    cls = clauses(raw, lang)
    has_neg = any(neg_in(c, lang) for c in cls) if not cm else any(neg_in(c, l) for c in cls for l in L)
    gold_neg = bool(sc["gold_neg"])
    carries = []
    for c in cls:
        ct = c.split()
        carries.append(any(present(s, l, c, ct) for s in selected for l in L) or any(canon(w) in c for w in customs))
    if gold_neg:
        scoped = has_neg and all((not carr) or neg_in(c, lang) for c, carr in zip(cls, carries)) if not cm else has_neg
        polarity_ok = bool(scoped)
    else:
        polarity_ok = not has_neg
    # act
    req = any(rx_any(REQ[l], t) for l in L)
    st = any(rx_any(STATE[l], t) for l in L)
    gold_act = sc["gold_act"]
    FEEL_IDS = {"HAPPY", "SAD", "ANGRY", "TIRED", "SICK", "SCARED", "LOVE", "EXCITED", "PAIN", "GOOD", "BAD"}
    feeling_wanted = False                      # a selected feeling inside a clause governed by a request marker ("I want tired")
    if gold_act in ("feeling", "feeling_request"):
        for c in cls:
            ct = c.split()
            if any(present(f, l, c, ct) for f in selected if f in FEEL_IDS for l in L) and any(rx_any(REQ[l], c) for l in L):
                feeling_wanted = True
    if gold_act == "request":
        act_expressed, act_wrong = req, ((not req) and st)
    elif gold_act == "feeling":
        act_expressed, act_wrong = (st and not req), req
    elif gold_act == "feeling_request":
        act_expressed, act_wrong = (st and req and not feeling_wanted), ((req != st) or feeling_wanted)
    elif gold_act == "greeting":
        act_expressed, act_wrong = any(rx_any(GREET[l], t) for l in L), False
    else:                                   # ambiguous scenarios are not scored for act
        act_expressed, act_wrong = True, False
    act_missing = (not act_expressed) and (not act_wrong)
    # unsupported content (board vocabulary + distractors + reasons/times)
    sel_forms = [x.lstrip("=") for c in selected for l in L for x in forms(c, l)] + [canon(w) for w in customs]
    hits = []
    t_d = re.sub(r"\b(?:would|i'd|i would) love(?: to)?\b", "would like", t) if lang == "en" else t
    tk_d = t_d.split()
    for f, l in distractors(lang, set(selected)):
        if hit(f, t_d, tk_d, l):
            fb = f.lstrip("=")
            if any((fb in sf) or (sf in fb) for sf in sel_forms if sf):
                continue
            hits.append(f)
    rt = [p for l in L for p in REASON_TIME[l] if re.search(p, t)]
    unsupported = len(hits) > 0 or len(rt) > 0
    # off-task decomposition
    latin = sum(ch.isascii() and ch.isalpha() for ch in raw)
    letters = sum(ch.isalpha() for ch in raw) or 1
    custom_lat = sum(ch.isascii() and ch.isalpha() for w in customs for ch in w)
    model_refusal = rx_any(REFUSAL_EN, t) if (lang == "en" or cm) else False
    meta = rx_any(META, raw.lower())
    third = any(rx_any(THIRD[l], t) for l in L)
    too_long = len(tk) > 25
    empty = len(tk) == 0
    leak = (lang != "en" and not cm and max(0, latin - custom_lat) / letters > 0.3)
    if lang == "en":
        script_ok = latin / letters > 0.8
    elif lang == "gu":
        script_ok = any("઀" <= ch <= "૿" for ch in raw)
    else:
        script_ok = any("ऀ" <= ch <= "ॿ" for ch in raw)
    offtask = model_refusal or meta or too_long or empty or leak
    success = (retention == 1.0 and more_ok and polarity_ok and act_expressed and not unsupported and not offtask and not third and script_ok)
    return dict(retention=retention, n_concepts=n_c, n_present=sum(pres), polarity_ok=polarity_ok, polarity_drop=(gold_neg and not has_neg),
                polarity_spur=((not gold_neg) and has_neg), polarity_scope=(gold_neg and has_neg and not polarity_ok),
                act_ok=act_expressed, act_wrong=act_wrong, act_missing=act_missing, unsupported=unsupported, unsupported_hits=hits + rt,
                offtask=offtask, model_refusal=model_refusal, meta=meta, third_person=third, too_long=too_long, empty=empty, latin_leak=leak,
                script_ok=script_ok, more_ok=more_ok, success=success)


if __name__ == "__main__":
    print("scorer v2 module OK;", VERSION)
