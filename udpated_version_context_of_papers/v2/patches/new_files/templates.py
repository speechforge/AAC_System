"""Compositional, locale-specific template realiser (the deterministic fallback of the repaired hybrid).

A sentence is composed from a frame (request, refusal, feeling, negated feeling, action, help or call, feeling plus
request) and locale lexical entries (noun phrases with gender, feeling predicates, verb forms, person case forms).
Act and polarity are separate inputs.  When no complete sentence can be composed safely the result is *not* a guess:

    status "ok"          -> `text` is a complete sentence
    status "ambiguous"   -> no determinate act: the UI asks the user (clarification), `options` lists acts
    status "unsupported" -> determinate act but no frame: a labelled literal preview of the selected symbols

Linguistic status: written by the authoring assistant; **not yet reviewed by native speakers** (see FINAL_CONTEXT.md).
Gender-neutral constructions are used wherever the speaker's gender would otherwise be marked.
"""
import re

from aac_lexicon import BOARD, analyze_selection, canon

# ───────────── lexical entries ─────────────
GENDER = {   # grammatical gender of the object noun (Gujarati, Marathi)
    "gu": {"WATER": "n", "FOOD": "m", "MILK": "n", "RICE": "m", "ROTI": "f", "FRUIT": "n", "TEA": "f", "JUICE": "m",
           "SNACK": "n", "PIZZA": "m", "MEDICINE": "f"},
    "mr": {"WATER": "n", "FOOD": "n", "MILK": "n", "RICE": "m", "ROTI": "f", "FRUIT": "n", "TEA": "m", "JUICE": "m",
           "SNACK": "n", "PIZZA": "m", "MEDICINE": "n"},
}
NP_OVERRIDE = {
    "en": {"FOOD": "food", "ROTI": "roti", "SNACK": "biscuits", "WATER": "water", "MILK": "milk", "RICE": "rice",
           "FRUIT": "fruit", "TEA": "tea", "JUICE": "juice", "PIZZA": "pizza", "MEDICINE": "medicine"},
}
PERSON = {   # (noun phrase for 'call', vocative)
    "en": {"MOTHER": ("my mother", "Mother"), "FATHER": ("my father", "Father"), "SISTER": ("my sister", "Sister"),
           "BROTHER": ("my brother", "Brother"), "TEACHER": ("my teacher", "Teacher"), "DOCTOR": ("the doctor", "Doctor"),
           "FRIEND": ("my friend", "Friend")},
    "hi": {"MOTHER": ("माँ को", "माँ"), "FATHER": ("पिताजी को", "पिताजी"), "SISTER": ("बहन को", "बहन"), "BROTHER": ("भाई को", "भाई"),
           "TEACHER": ("शिक्षक को", "शिक्षक"), "DOCTOR": ("डॉक्टर को", "डॉक्टर"), "FRIEND": ("दोस्त को", "दोस्त")},
    "gu": {"MOTHER": ("માતાને", "માતા"), "FATHER": ("પિતાજીને", "પિતાજી"), "SISTER": ("બહેનને", "બહેન"), "BROTHER": ("ભાઈને", "ભાઈ"),
           "TEACHER": ("શિક્ષકને", "શિક્ષક"), "DOCTOR": ("ડૉક્ટરને", "ડૉક્ટર"), "FRIEND": ("મિત્રને", "મિત્ર")},
    "mr": {"MOTHER": ("आईला", "आई"), "FATHER": ("बाबांना", "बाबा"), "SISTER": ("बहिणीला", "बहीण"), "BROTHER": ("भावाला", "भाऊ"),
           "TEACHER": ("शिक्षकांना", "शिक्षक"), "DOCTOR": ("डॉक्टरांना", "डॉक्टर"), "FRIEND": ("मित्राला", "मित्र")},
}
CUSTOM_CASE = {"en": "{w}", "hi": "{w} को", "gu": "{w}ને", "mr": "{w}ला"}
VERB = {   # EN verb phrase | HI infinitive | GU 'verb-નું' | MR genitive (…ची)
    "en": {"EAT": "eat", "DRINK": "drink", "PLAY": "play", "SLEEP": "sleep", "GO": "go", "STUDY": "study", "BATH": "take a bath",
           "CALL": "call", "WRITE": "write", "LOOK": "look"},
    "hi": {"EAT": "खाना", "DRINK": "पीना", "PLAY": "खेलना", "SLEEP": "सोना", "GO": "जाना", "STUDY": "पढ़ना", "BATH": "नहाना",
           "CALL": "करना", "WRITE": "लिखना", "LOOK": "देखना"},
    "gu": {"EAT": "જમવાનું", "DRINK": "પીવાનું", "PLAY": "રમવાનું", "SLEEP": "ઊંઘવાનું", "GO": "જવાનું", "STUDY": "ભણવાનું",
           "BATH": "નાહવાનું", "CALL": "ફોન કરવાનું", "WRITE": "લખવાનું", "LOOK": "જોવાનું"},
    "mr": {"EAT": "खाण्याची", "DRINK": "पिण्याची", "PLAY": "खेळण्याची", "SLEEP": "झोपण्याची", "GO": "जाण्याची",
           "STUDY": "अभ्यास करण्याची", "BATH": "आंघोळ करण्याची", "CALL": "फोन करण्याची", "WRITE": "लिहिण्याची", "LOOK": "पाहण्याची"},
}
# feeling predicates: (positive, negative) complete clauses without final punctuation
FEEL = {
    "en": {"HAPPY": ("I am happy", "I am not happy"), "SAD": ("I am sad", "I am not sad"), "ANGRY": ("I am angry", "I am not angry"),
           "TIRED": ("I am tired", "I am not tired"), "SICK": ("I am sick", "I am not sick"), "SCARED": ("I am scared", "I am not scared"),
           "LOVE": ("I feel love", "I do not feel love"), "EXCITED": ("I am excited", "I am not excited"),
           "PAIN": ("I am in pain", "I am not in pain"), "GOOD": ("I feel good", "I do not feel good"), "BAD": ("I feel bad", "I do not feel bad")},
    "hi": {"HAPPY": ("मैं खुश हूँ", "मैं खुश नहीं हूँ"), "SAD": ("मैं उदास हूँ", "मैं उदास नहीं हूँ"),
           "ANGRY": ("मुझे गुस्सा आ रहा है", "मुझे गुस्सा नहीं आ रहा है"), "TIRED": ("मुझे थकान हो रही है", "मुझे थकान नहीं हो रही है"),
           "SICK": ("मैं बीमार हूँ", "मैं बीमार नहीं हूँ"), "SCARED": ("मुझे डर लग रहा है", "मुझे डर नहीं लग रहा है"),
           "LOVE": ("मुझे प्यार महसूस हो रहा है", "मुझे प्यार महसूस नहीं हो रहा है"), "EXCITED": ("मैं उत्साहित हूँ", "मैं उत्साहित नहीं हूँ"),
           "PAIN": ("मुझे दर्द हो रहा है", "मुझे दर्द नहीं हो रहा है"), "GOOD": ("मुझे अच्छा लग रहा है", "मुझे अच्छा नहीं लग रहा है"),
           "BAD": ("मुझे बुरा लग रहा है", "मुझे बुरा नहीं लग रहा है")},
    "gu": {"HAPPY": ("હું ખુશ છું", "હું ખુશ નથી"), "SAD": ("હું ઉદાસ છું", "હું ઉદાસ નથી"),
           "ANGRY": ("મને ગુસ્સો આવે છે", "મને ગુસ્સો આવતો નથી"), "TIRED": ("મને થાક લાગ્યો છે", "મને થાક લાગ્યો નથી"),
           "SICK": ("હું બીમાર છું", "હું બીમાર નથી"), "SCARED": ("મને ડર લાગે છે", "મને ડર લાગતો નથી"),
           "LOVE": ("મને પ્રેમ લાગે છે", "મને પ્રેમ લાગતો નથી"), "EXCITED": ("હું ઉત્સાહિત છું", "હું ઉત્સાહિત નથી"),
           "PAIN": ("મને દુખાવો થાય છે", "મને દુખાવો થતો નથી"), "GOOD": ("મને સારું લાગે છે", "મને સારું લાગતું નથી"),
           "BAD": ("મને ખરાબ લાગે છે", "મને ખરાબ લાગતું નથી")},
    "mr": {"HAPPY": ("मी आनंदी आहे", "मी आनंदी नाही"), "SAD": ("मी दुःखी आहे", "मी दुःखी नाही"),
           "ANGRY": ("मला राग आला आहे", "मला राग आलेला नाही"), "TIRED": ("मला थकवा आला आहे", "मला थकवा आलेला नाही"),
           "SICK": ("मी आजारी आहे", "मी आजारी नाही"), "SCARED": ("मला भीती वाटत आहे", "मला भीती वाटत नाही"),
           "LOVE": ("मला प्रेम वाटते", "मला प्रेम वाटत नाही"), "EXCITED": ("मी उत्साही आहे", "मी उत्साही नाही"),
           "PAIN": ("मला वेदना होत आहेत", "मला वेदना होत नाहीत"), "GOOD": ("मला चांगले वाटते", "मला चांगले वाटत नाही"),
           "BAD": ("मला वाईट वाटते", "मला वाईट वाटत नाही")},
}
AND = {"en": " and ", "hi": " और ", "gu": " અને ", "mr": " आणि "}
OR_NEG = {"en": " or ", "hi": " और ", "gu": " અને ", "mr": " आणि "}
MORE = {"en": "more ", "hi": "और ", "gu": "વધુ ", "mr": "आणखी "}


def _np(item, lang):
    cid = item["cid"]
    if cid is None:
        return item["label"].strip()
    if lang == "en":
        return NP_OVERRIDE["en"].get(cid, BOARD[cid]["en"].split("/")[0].strip().lower())
    return BOARD[cid][lang].split("/")[0].strip()


def _more(items, lang):
    return MORE[lang] if any(i.get("more") for i in items) else ""


def _person(item, lang):
    cid = item["cid"]
    if cid is None:
        w = item["label"].strip()
        return CUSTOM_CASE[lang].format(w=w), w
    return PERSON[lang][cid]


def _joined(items, lang, neg):
    nps = [_np(i, lang) for i in items]
    return (OR_NEG if neg else AND)[lang].join(nps)


def _object_clause(objs, lang, neg):
    more = _more(objs, lang)
    np = _joined(objs, lang, neg)
    plural = len(objs) > 1
    if lang == "en":
        return ("I do not want " if neg else "I want ") + more + np
    if lang == "hi":
        return "मुझे " + more + np + (" नहीं चाहिए" if neg else " चाहिए")
    if lang == "gu":
        if not neg:
            return "મને " + more + np + " જોઈએ છે"
        g = "n" if plural else GENDER["gu"].get(objs[0]["cid"], "n")
        return "મને " + more + np + " નથી " + ("જોઈતાં" if plural else {"m": "જોઈતો", "f": "જોઈતી", "n": "જોઈતું"}[g])
    if lang == "mr":
        if neg:
            return "मला " + more + np + " नको आहे"
        g = "n" if plural else GENDER["mr"].get(objs[0]["cid"], "n")
        return "मला " + more + np + " " + ("हवे आहेत" if plural else {"m": "हवा आहे", "f": "हवी आहे", "n": "हवे आहे"}[g])


def _action_clause(acts, objs, ppl, custom, lang, neg):
    act = acts[0]["cid"]
    obj = (objs + custom)[:2]
    obj_np = _joined(obj, lang, False) if obj else ""
    if act == "CALL":
        who = (ppl + custom)[:1]
        if not who:
            return None
        case, _ = _person(who[0], lang)
        if lang == "en":
            return ("I do not want to call " if neg else "I want to call ") + case
        if lang == "hi":
            return "मुझे " + case + (" फ़ोन नहीं करना है" if neg else " फ़ोन करना है")
        if lang == "gu":
            return "મને " + case + " ફોન કરવાનું મન " + ("નથી" if neg else "છે")
        return "मला " + case + " फोन करण्याची इच्छा " + ("नाही" if neg else "आहे")
    if ppl and act != "CALL":
        return None                                      # e.g. 'eat' + a person: not a supported frame
    v = VERB[lang][act]
    if lang == "en":
        return ("I do not want to " if neg else "I want to ") + v + (" " + obj_np if obj_np else "")
    if lang == "hi":
        return "मुझे " + (obj_np + " " if obj_np else "") + ("नहीं " if neg else "") + v + " है"
    if lang == "gu":
        return "મને " + (obj_np + " " if obj_np else "") + v + " મન " + ("નથી" if neg else "છે")
    return "मला " + (obj_np + " " if obj_np else "") + v + " इच्छा " + ("नाही" if neg else "आहे")


def _help_clause(ppl, custom, lang):
    voc = None
    who = (ppl + custom)[:1]
    if who:
        _, voc = _person(who[0], lang)
    if lang == "en":
        return (voc + ", please help me") if voc else "Please help me"
    if lang == "hi":
        return (voc + ", कृपया मेरी मदद कीजिए") if voc else "कृपया मेरी मदद कीजिए"
    if lang == "gu":
        return (voc + ", કૃપા કરીને મને મદદ કરો") if voc else "કૃપા કરીને મને મદદ કરો"
    return (voc + ", कृपया मला मदत करा") if voc else "कृपया मला मदत करा"


def _sentence(clause, lang):
    clause = clause.strip()
    return clause + ("।" if lang == "hi" else ".")


def _request_clause(a, lang, neg):
    c, objs = a["content"], None
    objs = [i for i in c if i["cat"] == "food" or i["cid"] == "MEDICINE"]
    acts = [i for i in c if i["cat"] == "actions"]
    ppl = [i for i in c if i["cat"] == "people"]
    custom = [i for i in c if i["cid"] is None]
    help_ = [i for i in c if i["cid"] in ("HELP", "HELP_EMERGENCY")]
    if help_:
        return None if neg else _help_clause(ppl, custom, lang)
    if acts:
        return _action_clause(acts, objs, ppl, custom, lang, neg)
    if objs or custom:
        return _object_clause(objs + custom, lang, neg)
    return None


def literal_preview(items):
    return " ".join(i["label"] for i in items if i.get("label"))


def realize(items, lang="en", forced_act=None, negation=None):
    """items: [{cid, label}] in the order selected.  Returns dict(status, text, act, negation, frame, options, literal)."""
    a = analyze_selection(items, lang, forced_act=forced_act)
    if negation is not None:                       # the request's explicit polarity field wins over the symbols' own NO
        a["negation"] = bool(negation)
    neg, act = a["negation"], a["act"]
    out = dict(status="unsupported", text=None, act=act, negation=neg, frame=a["frame"], options=[], literal=literal_preview(items),
               ambiguous=a["ambiguous"])
    if a["ambiguous"] and not forced_act:
        out.update(status="ambiguous", options=["REQUEST", "FEELING"])
        return out
    fr = a["frame"]
    c = a["content"]
    try:
        if fr == "feeling":
            f = next(i for i in c if i["cid"] in FEEL["en"])
            out.update(status="ok", text=_sentence(FEEL[lang][f["cid"]][1 if neg else 0], lang))
        elif fr == "feeling_request":
            f = next(i for i in c if i["cid"] in FEEL["en"])
            rest = [dict(i) for i in c if i is not f]
            sub = dict(content=rest)
            rq = _request_clause(sub, lang, False)
            if rq is not None:
                head = FEEL[lang][f["cid"]][0]
                if lang == "en" and rq.startswith("Please"):
                    rq = "p" + rq[1:]
                out.update(status="ok", text=_sentence(head + ", " + rq, lang))
        elif fr in ("object", "action", "help"):
            rq = _request_clause(a, lang, neg)
            if rq is not None:
                out.update(status="ok", text=_sentence(rq, lang))
    except Exception:
        out.update(status="unsupported", text=None)
    return out
