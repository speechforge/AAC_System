"""Board concept registry, locale text helpers and selection analysis for the repaired pipeline.

Used by (1) the backend request normaliser, (2) the gate (semantic.py) and (3) the templates (templates.py).
The browser client carries a compact JavaScript port of `analyze_selection` (frontend/index.html) because the
client must decide the act before the request is sent; the backend recomputes it only for legacy payloads.

Act and polarity are separate fields:
    act      in {REQUEST, FEELING, FEELING_REQUEST, QUESTION, GREETING, UNKNOWN}
    negation bool   (a refusal is REQUEST + negation; a negated feeling is FEELING + negation)
Concept IDs are the board's own stable IDs (board_concepts.json); typed or "My Words" entries have no ID.
"""
import json
import os
import re
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = json.load(open(os.path.join(_HERE, "board_concepts.json"), encoding="utf-8"))["concepts"]
LANGS = ("en", "hi", "gu", "mr")

FEELINGS = ["HAPPY", "SAD", "ANGRY", "TIRED", "SICK", "SCARED", "LOVE", "EXCITED", "PAIN"]
OBJECTS = [c for c, v in BOARD.items() if v["cat"] == "food"] + ["MEDICINE"]
ACTIONS = [c for c, v in BOARD.items() if v["cat"] == "actions"]
PEOPLE = [c for c, v in BOARD.items() if v["cat"] == "people"]
PLACES = [c for c, v in BOARD.items() if v["cat"] == "places"]
BODY = [c for c, v in BOARD.items() if v["cat"] == "body"]
FUNCTION = {"NO", "WANT", "MORE", "ME", "PLEASE", "YES"}          # carry polarity, act, quantity or speaker, not content

# ────────────────────────── text normalisation ──────────────────────────
_PUNCT = re.compile(r"[\.,!\?;:।\"“”‘’\(\)\[\]/\\|•]")


def canon(text):
    """NFC, casefold, drop nukta and zero-width marks, map chandrabindu to anusvara, strip punctuation."""
    t = unicodedata.normalize("NFC", text or "").casefold()
    t = t.replace("़", "").replace("઼", "").replace("‍", "").replace("‌", "")
    t = t.replace("ँ", "ं").replace("ઁ", "ં").replace("’", "'")
    t = _PUNCT.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(text):
    return canon(text).split()


def script_of(text):
    """Counts of letters by script: (latin, devanagari, gujarati)."""
    lat = sum(ch.isascii() and ch.isalpha() for ch in text or "")
    dev = sum("ऀ" <= ch <= "ॿ" for ch in text or "")
    guj = sum("઀" <= ch <= "૿" for ch in text or "")
    return lat, dev, guj


# ────────────────────────── label resolution ──────────────────────────
def _label_index():
    idx = {}
    for cid, v in BOARD.items():
        for lg in LANGS:
            lab = canon(v[lg])
            idx.setdefault(lab, set()).add(cid)
            for part in re.split(r"\s*/\s*", v[lg]):
                p = canon(part)
                if p:
                    idx.setdefault(p, set()).add(cid)
    idx.setdefault("i", set()).add("ME")
    idx.setdefault("me", set()).add("ME")
    return idx


_IDX = _label_index()


def resolve_all(label, lang=None):
    """All board concepts whose label (in `lang`, else any locale) equals `label`, in board order."""
    c = canon(label)
    hits = _IDX.get(c)
    if not hits:
        return []
    if lang:
        exact = [h for h in hits if canon(BOARD[h][lang]) == c or c in [canon(p) for p in re.split(r"\s*/\s*", BOARD[h][lang])]]
        if exact:
            hits = set(exact)
    order = list(BOARD)
    return sorted(hits, key=order.index)


def resolve_label(label, lang=None):
    """Board concept ID for a label shown on the board (any locale), or None for typed / personal words.
    The same surface can belong to two concepts in one locale (Hindi 'khana' = FOOD and EAT): the language
    column of the label decides; if still ambiguous the first match in board order is returned and the
    caller must prefer explicit concept IDs."""
    c = canon(label)
    hits = _IDX.get(c)
    if not hits:
        return None
    if lang:
        exact = [h for h in hits if canon(BOARD[h][lang]) == c or c in [canon(p) for p in re.split(r"\s*/\s*", BOARD[h][lang])]]
        if exact:
            hits = set(exact)
    order = list(BOARD)
    return sorted(hits, key=order.index)[0]


# ────────────────────────── negators and acts (locale rules) ──────────────────────────
NEGATORS = {
    "en": [r"\bnot\b", r"\bno\b", r"\bnever\b", r"\bcannot\b", r"\bnothing\b", r"n't\b", r"\bnor\b", r"\bneither\b"],
    "hi": [r"(?<!\S)नहीं(?!\S)", r"(?<!\S)नही(?!\S)", r"(?<!\S)न(?!\S)", r"(?<!\S)मत(?!\S)"],
    "gu": [r"(?<!\S)નથી(?!\S)", r"(?<!\S)નહીં(?!\S)", r"(?<!\S)નહિ(?!\S)", r"(?<!\S)નહી(?!\S)", r"(?<!\S)ના(?!\S)", r"(?<!\S)ન(?!\S)"],
    "mr": [r"(?<!\S)नाही(?!\S)", r"(?<!\S)नाहीत(?!\S)", r"(?<!\S)नको(?!\S)", r"(?<!\S)नका(?!\S)", r"(?<!\S)नये(?!\S)", r"(?<!\S)न(?!\S)"],
}
# whole-token negators accepted from typed board labels (client side uses the same list)
NEGATOR_TOKENS = {"no", "not", "नहीं", "नही", "ना", "ના", "नाही", "नको"}

REQUEST_RX = {
    "en": r"\b(want|wants|need|needs|would like|i'd like|give me|may i have|can i have|could i have|please|wish|require)\b",
    "hi": r"(चाहिए|चाहिये|जरूरत|चाहता|चाहती|चाहते|चाहूं|दीजिए|दीजिये|कृपया|कीजिए|कीजिये|(?<!\S)दो(?!\S)|(?<!\S)दें(?!\S)|का मन|"
          r"(?<!\S)मुझे\s+.*(ना|ने|नी)\s+(नहीं\s+)?(है|हैं|होगा|चाहिए)(?!\S))",
    "gu": r"(જોઈએ|જોઈત|જરૂર|આપો|ઈચ્છ|માગ|મન છે|મન નથી|કૃપા|કરો(?!\S)|(?<!\S)મારે(?!\S))",
    "mr": r"(हवे|हवा|हवी|हवेत|गरज|आवश्यक|पाहिजे|पाहिजेत|नको|इच्छा|मागत|द्या|कृपया|करा(?!\S)|यचे आहे|यचा आहे|यची आहे|यचे नाही|यचा नाही|यची नाही)",
}
STATE_RX = {
    "en": r"\b(i am|i'm|i feel|feeling|i do not feel|i don't feel|i am not|i'm not)\b",
    "hi": r"(हूं|हूँ|महसूस|लग रहा|लग रही|लगा है|लगी है|आ रहा|आ रही|हो रहा|हो रही|थकान|(?<!\S)मैं(?!\S)|(?<!\S)मुझे(?!\S))",
    "gu": r"(છું|લાગે|લાગ્યો|લાગી|લાગતો|લાગતી|લાગતું|અનુભવ|થાય|આવે|આવતો|આવતી|(?<!\S)હું(?!\S)|(?<!\S)મને(?!\S))",
    "mr": r"(आहे|वाटते|वाटत|वाटतो|आला|आली|आलेला|आलेली|होत|(?<!\S)मी(?!\S)|(?<!\S)मला(?!\S))",
}
QUESTION_RX = {
    "en": r"(\?|\b(can|could|may|where|what|how|do you|will you)\b)",
    "hi": r"(\?|(?<!\S)क्या(?!\S)|कहाँ|कैसे|कब)",
    "gu": r"(\?|(?<!\S)શું(?!\S)|ક્યાં|કેમ|કેવી)",
    "mr": r"(\?|(?<!\S)का(?!\S)|(?<!\S)काय(?!\S)|कुठे|कसे)",
}
FIRST_PERSON = {
    "en": r"\b(i|me|my|mine|i'm|i'd|myself)\b",
    "hi": r"(?<!\S)(मैं|मुझे|मेरा|मेरी|मेरे|मैंने|हम|हमें|हमारा)(?!\S)",
    "gu": r"(?<!\S)(હું|મને|મારે|મારું|મારા|મારી|મેં|અમે|અમને)(?!\S)",
    "mr": r"(?<!\S)(मी|मला|माझे|माझा|माझी|माझ्या|मी|आम्ही|आम्हाला)(?!\S)",
}
THIRD_PERSON = {
    "en": r"\b(the user|the patient|the person|he|she|they|him|her|his|them|their|user's|user)\b",
    "hi": r"(?<!\S)(वह|वो|उसे|उसको|उसका|उसकी|उसके|उन्हें|उनका|उनकी|उनके|वे|उपयोगकर्ता|यूज़र|यूजर)(?!\S)",
    "gu": r"(?<!\S)(તે|તેને|તેણે|તેનું|તેની|તેના|તેઓ|તેમને|વપરાશકર્તા|યુઝર)(?!\S)",
    "mr": r"(?<!\S)(तो|ती|ते|त्याला|तिला|त्यांना|त्याचा|त्याची|त्याचे|तिचा|तिची|त्यांचा|वापरकर्ता|यूजर)(?!\S)",
}
META_RX = (r"(sorry|cannot fulfill|can't fulfill|cannot generate|can't generate|as an ai|language model|"
           r"in hindi|in gujarati|in marathi|in english|means\b|translation|translates|selected symbol|the symbol|"
           r"input sequence|इनपुट क्रम|ઈનપુટ ક્રમ|इनपुट|क्षमा|माफ़|માફ|क्षमस्व)")
REASON_TIME_RX = {
    "en": r"\b(because|since|so that|so i can|today|tomorrow|yesterday|tonight|morning|evening|afternoon|night|breakfast|lunch|dinner|later|soon|now|right now|at school|at home|at the|restaurant|store|shop|hungry|thirsty|delicious)\b",
    "hi": r"(क्योंकि|इसलिए|ताकि|आज|कल|सुबह|शाम|दोपहर|रात|अभी|नाश्ते|नाश्ता|रेस्तरां|रेस्टोरेंट|दुकान|भूख|भूखा|भूखे|प्यास|स्वादिष्ट)",
    "gu": r"(કારણ કે|કેમ કે|તેથી|આજે|કાલે|સવારે|સાંજે|રાત્રે|બપોરે|હમણાં|નાસ્તો|રેસ્ટોરન્ટ|દુકાન|ભૂખ|તરસ|સ્વાદિષ્ટ)",
    "mr": r"(कारण|म्हणून|आज|उद्या|सकाळी|संध्याकाळी|रात्री|दुपारी|आत्ता|नाश्ता|रेस्टॉरंट|दुकान|भूक|तहान|स्वादिष्ट|चविष्ट)",
}

# ────────────────────────── concept surface forms for the gate ──────────────────────────
# Prefix match for forms of >= 3 characters, whole-token match for shorter forms and for forms marked '='.
EXTRA = {
    "FOOD": {"en": ["food", "meal"], "hi": ["खाना", "खाने", "भोजन"], "gu": ["ખોરાક", "ભોજન", "જમવાનું", "ખાવાનું"], "mr": ["जेवण", "अन्न"]},
    "ROTI": {"en": ["roti", "bread", "chapati"], "hi": ["रोटी", "चपाती"], "gu": ["રોટલી", "રોટલા", "રોટી"], "mr": ["पोळी", "चपाती", "भाकरी", "रोटी"]},
    "SNACK": {"en": ["biscuit", "snack", "cookie"], "hi": ["बिस्कुट", "बिस्किट", "नाश्ता"], "gu": ["બિસ્કિટ", "બિસ્કીટ", "નાસ્તો"], "mr": ["बिस्किट", "बिस्कीट", "बिस्कुट"]},
    "WATER": {"en": ["water"], "hi": ["पानी"], "gu": ["પાણી"], "mr": ["पाणी", "पाण्य"]},
    "MILK": {"en": ["milk"], "hi": ["दूध"], "gu": ["દૂધ", "દુધ"], "mr": ["दूध", "दुध"]},
    "TEA": {"en": ["tea"], "hi": ["चाय"], "gu": ["=ચા", "ચાય", "ચાને"], "mr": ["चहा", "चहाला"]},
    "JUICE": {"en": ["juice"], "hi": ["जूस", "=रस"], "gu": ["જ્યુસ", "=રસ"], "mr": ["=रस", "रसाची", "ज्यूस", "जूस"]},
    "PIZZA": {"en": ["pizza"], "hi": ["पिज्जा", "पिज़्ज़ा"], "gu": ["પિઝા", "પીઝા"], "mr": ["पिझ्झा", "पिझा", "पिज्जा"]},
    "HAPPY": {"en": ["happy", "glad"], "hi": ["खुश", "प्रसन्न"], "gu": ["ખુશ", "આનંદ"], "mr": ["आनंद", "खुश"]},
    "SAD": {"en": ["sad", "unhappy"], "hi": ["उदास", "दुखी", "दुःखी"], "gu": ["ઉદાસ", "દુઃખી", "દુખી"], "mr": ["दुःखी", "दुखी", "उदास"]},
    "ANGRY": {"en": ["angry", "mad"], "hi": ["गुस्स"], "gu": ["ગુસ્સ"], "mr": ["राग"]},
    "TIRED": {"en": ["tired", "exhausted"], "hi": ["थक", "थका"], "gu": ["થાક"], "mr": ["दमल", "थक", "थकवा"]},
    "SICK": {"en": ["sick", "=ill", "unwell"], "hi": ["बीमार"], "gu": ["બીમાર"], "mr": ["आजारी", "आजार"]},
    "SCARED": {"en": ["scared", "afraid", "fear"], "hi": ["डरा", "डर"], "gu": ["ડર"], "mr": ["घाबर", "भीती", "भित"]},
    "LOVE": {"en": ["love"], "hi": ["प्यार", "प्रेम"], "gu": ["પ્રેમ", "પ્યાર"], "mr": ["प्रेम"]},
    "EXCITED": {"en": ["excited"], "hi": ["उत्साहित", "उत्साह"], "gu": ["ઉત્સાહ"], "mr": ["उत्साह"]},
    "PAIN": {"en": ["pain", "hurt", "ache"], "hi": ["दर्द"], "gu": ["દુખાવો", "દુખ", "દર્દ"], "mr": ["वेदना", "दुखत", "दुखणे"]},
    "MEDICINE": {"en": ["medicine", "medication", "pills"], "hi": ["दवा", "दवाई"], "gu": ["દવા"], "mr": ["औषध", "गोळ्या"]},
    "EAT": {"en": ["eat", "ate", "eaten", "eating"], "hi": ["खा", "खाने", "खाऊं", "खाता", "खाती", "खाया"], "gu": ["જમવા", "જમવું", "જમું", "જમે", "જમી", "ખાવ", "ખાય", "ખાઉં", "ખાધ"], "mr": ["खाणे", "खाण", "खायच", "खात", "खाऊ", "खाल्", "जेव"]},
    "DRINK": {"en": ["drink", "drank", "drunk", "drinking"], "hi": ["पीना", "पीने", "पीत", "पिया", "पिल", "=पी"], "gu": ["પીવ", "પીઉં", "પીધ", "=પી"], "mr": ["पिण", "प्यायच", "पित", "पिऊ", "पिले", "=प्या"]},
    "PLAY": {"en": ["play"], "hi": ["खेल"], "gu": ["રમવ", "રમે", "રમી", "રમું", "રમત"], "mr": ["खेळ"]},
    "SLEEP": {"en": ["sleep", "rest", "nap"], "hi": ["सो", "सोना", "सोने", "नींद"], "gu": ["ઊંઘ", "સૂવ", "સુવ"], "mr": ["झोप"]},
    "GO": {"en": ["go", "going", "went"], "hi": ["जाना", "जाने", "जाऊं", "जाऊँ", "जा"], "gu": ["જવ", "જાઉં", "જાય"], "mr": ["जाण", "जावे", "जाऊ", "जा"]},
    "STUDY": {"en": ["study", "studying"], "hi": ["पढ़", "पढ"], "gu": ["ભણ"], "mr": ["अभ्यास"]},
    "BATH": {"en": ["bathe", "bath", "shower"], "hi": ["नहा"], "gu": ["નાહ", "નહાવ"], "mr": ["आंघोळ"]},
    "CALL": {"en": ["call", "phone"], "hi": ["फोन", "बुला"], "gu": ["ફોન", "બોલાવ"], "mr": ["फोन", "बोलाव", "कॉल"]},
    "WRITE": {"en": ["write", "writing"], "hi": ["लिख"], "gu": ["લખ"], "mr": ["लिह"]},
    "LOOK": {"en": ["look", "see", "watch"], "hi": ["देख"], "gu": ["જોવ", "જુઓ"], "mr": ["पाह", "बघ"]},
    "HELP": {"en": ["help"], "hi": ["मदद", "सहायता"], "gu": ["મદદ"], "mr": ["मदत"]},
    "MOTHER": {"en": ["mother", "mom", "mum", "mommy", "mama"], "hi": ["=माँ", "=मां", "माता", "मम्मी"], "gu": ["માતા", "મમ્મી", "=મા", "=માં"], "mr": ["आई", "आईल", "आईच", "आईस", "माता", "मम्मी"]},
    "FATHER": {"en": ["father", "dad", "daddy", "papa"], "hi": ["पिता", "पापा"], "gu": ["પિતા", "પપ્પા"], "mr": ["बाबा", "वडील", "पिता"]},
    "SISTER": {"en": ["sister"], "hi": ["बहन"], "gu": ["બહેન"], "mr": ["बहीण", "बहिण"]},
    "BROTHER": {"en": ["brother"], "hi": ["भाई"], "gu": ["ભાઈ"], "mr": ["भाऊ", "भावा"]},
    "TEACHER": {"en": ["teacher"], "hi": ["शिक्षक", "अध्यापक"], "gu": ["શિક્ષક"], "mr": ["शिक्षक"]},
    "DOCTOR": {"en": ["doctor"], "hi": ["डॉक्टर", "डाक्टर", "चिकित्सक"], "gu": ["ડૉક્ટર", "ડોક્ટર"], "mr": ["डॉक्टर", "डाॅक्टर", "वैद्य"]},
    "FRIEND": {"en": ["friend"], "hi": ["दोस्त", "मित्र"], "gu": ["મિત્ર", "દોસ્ત"], "mr": ["मित्र", "दोस्त"]},
    "HOME": {"en": ["home", "house"], "hi": ["घर"], "gu": ["ઘર"], "mr": ["घर"]},
    "SCHOOL": {"en": ["school"], "hi": ["स्कूल", "विद्यालय"], "gu": ["શાળા", "સ્કૂલ"], "mr": ["शाळा", "स्कूल"]},
    "HOSPITAL": {"en": ["hospital"], "hi": ["अस्पताल"], "gu": ["હોસ્પિટલ", "દવાખાન"], "mr": ["रुग्णालय", "दवाखान", "हॉस्पिटल"]},
    "TOILET": {"en": ["toilet", "restroom", "bathroom"], "hi": ["शौचालय", "टॉयलेट"], "gu": ["શૌચાલય", "ટોયલેટ"], "mr": ["शौचालय", "टॉयलेट"]},
    "ROOM": {"en": ["bedroom", "room"], "hi": ["कमरा", "कमरे"], "gu": ["ઓરડો", "ઓરડા", "રૂમ"], "mr": ["खोली", "खोलीत"]},
    "MARKET": {"en": ["market"], "hi": ["बाजार"], "gu": ["બજાર"], "mr": ["बाजार"]},
    "MORE": {"en": ["=more"], "hi": [], "gu": [], "mr": []},     # a quantity modifier of the next concept: not an addition
}
# extra non-board distractors that count as added content
EXTRA_DISTRACTORS = {
    "en": ["restaurant", "store", "shop", "buy", "buying", "outside", "hungry", "thirsty", "delicious", "dessert", "chocolate", "coffee", "ice cream"],
    "hi": ["रेस्तरां", "रेस्टोरेंट", "दुकान", "खरीद", "भूख", "भूखा", "प्यास", "स्वादिष्ट", "कॉफी", "चॉकलेट"],
    "gu": ["રેસ્ટોરન્ટ", "દુકાન", "ખરીદ", "ભૂખ", "તરસ", "સ્વાદિષ્ટ", "કોફી", "ચોકલેટ"],
    "mr": ["रेस्टॉरंट", "दुकान", "खरेदी", "भूक", "तहान", "स्वादिष्ट", "कॉफी", "चॉकलेट"],
}
# concepts whose forms are excluded from the "added concept" test because they are function symbols or generic
NOT_CONTENT = {"YES", "NO", "WANT", "ME", "YOU", "PLEASE", "MORE", "GOOD", "BAD", "STOP", "HELP_EMERGENCY", "NAMASTE", "THANKS", "HOW", "BYE"}


def concept_forms(cid, lang):
    """Match forms for a concept in a locale: the board label (each '/'-part, first word of multiword labels) plus extras."""
    forms = []
    lab = BOARD[cid][lang]
    for part in re.split(r"\s*/\s*", lab):
        c = canon(part)
        if not c:
            continue
        forms.append(c if " " not in c else c.split()[0])
    forms += [canon(f) if not f.startswith("=") else "=" + canon(f[1:]) for f in EXTRA.get(cid, {}).get(lang, [])]
    out = []
    for f in forms:
        if f and f not in out:
            out.append(f)
    return out


def _form_hits(form, text, toks, lang):
    if lang == "en":
        f = form.lstrip("=")
        if form.startswith("=") or len(f) <= 3:
            return re.search(rf"(?<![a-z']){re.escape(f)}(?:s|es|ed|d|ing)?(?![a-z'])", text) is not None
        return re.search(rf"(?<![a-z']){re.escape(f)}(?:s|es|ed|d|ing|ly)?(?![a-z'])", text) is not None
    if form.startswith("="):
        return form[1:] in toks
    if len(form) >= 3:
        return any(t.startswith(form) for t in toks)
    return form in toks


def concept_present(cid, lang, text_canon, toks):
    return any(_form_hits(f, text_canon, toks, lang) for f in concept_forms(cid, lang))


def label_present(label, lang, text_canon, toks):
    """Presence of a typed / personal word: whole token (or token prefix for >= 4 characters) in the output."""
    f = canon(label)
    if not f:
        return True
    if " " in f:
        return f in text_canon
    if lang == "en":
        return re.search(rf"(?<![a-z']){re.escape(f)}(?:s|es|ed|d|ing)?(?![a-z'])", text_canon) is not None
    return any(t == f or (len(f) >= 4 and t.startswith(f[:max(3, len(f) - 1)])) for t in toks)


def has_negator(text_canon, lang):
    return any(re.search(p, text_canon) for p in NEGATORS[lang])


def clauses(text, lang):
    """Split into clauses at sentence punctuation, commas and adversative conjunctions (not at 'and')."""
    t = unicodedata.normalize("NFC", text or "").casefold().replace("’", "'")
    parts = re.split(r"[\.;!\?।,]|(?<!\S)(?:but|however|yet|लेकिन|परंतु|पर|मगर|પણ|પરંતુ|पण|परंतु|मात्र)(?!\S)", t)
    return [canon(p) for p in parts if canon(p)]


# ────────────────────────── selection analysis (client port exists in index.html) ──────────────────────────
def analyze_selection(items, lang="en", forced_act=None):
    """items: list of dicts {cid: str|None, label: str}.  Returns the structure the client and backend share.

    act:        REQUEST | FEELING | FEELING_REQUEST | QUESTION | GREETING | UNKNOWN
    negation:   True when the NO symbol (or a whole-token negator typed as a word) is present (position-insensitive)
    ambiguous:  True when no determinate act can be derived (clarification expected)
    frame:      template frame name or None (not covered)
    content:    ordered list of content items (function symbols removed)
    """
    neg_n = 0
    content, more, quantity, explicit_want = [], False, None, False
    resolved = []
    for it in items:                                   # pass 1: explicit IDs and unambiguous labels
        cid, label = it.get("cid"), it.get("label", "")
        cands = [] if cid else resolve_all(label, lang)
        resolved.append((cid, label, cands))
    has_other_object = lambda me: any((c in OBJECTS) for j, (_, _, cs) in enumerate(resolved) if j != me for c in ([resolved[j][0]] if resolved[j][0] else cs[:1]))
    for i, (cid, label, cands) in enumerate(resolved):
        if cid is None and cands:
            if len(cands) == 1:
                cid = cands[0]
            else:                                      # same surface for an action and an object (Hindi 'khana'): the other symbols decide
                acts_c = [c for c in cands if c in ACTIONS]
                objs_c = [c for c in cands if c in OBJECTS]
                cid = (acts_c[0] if acts_c and has_other_object(i) else (objs_c[0] if objs_c else cands[0]))
        it = dict(cid=cid, label=label)
        if cid is None and canon(label) in NEGATOR_TOKENS:
            cid = "NO"
        if cid == "NO":
            neg_n += 1
            continue
        if cid in ("WANT", "PLEASE", "YES"):
            explicit_want = explicit_want or cid == "WANT"
            continue
        if cid == "ME":
            continue
        if cid == "MORE":
            more = True
            continue
        content.append(dict(cid=cid, label=label, cat=(BOARD[cid]["cat"] if cid else "custom"), more=False))
    if more and content:
        for c in content:
            if c["cat"] in ("food", "emergency"):
                c["more"] = True
                break
    negation = neg_n % 2 == 1
    amb = neg_n > 1                                   # double negation: not determinable
    feel_ids = FEELINGS + (["GOOD", "BAD"] if forced_act in ("FEELING", "FEELING_REQUEST") else [])
    feel = [c for c in content if c["cid"] in feel_ids]
    objs = [c for c in content if c["cid"] in OBJECTS]
    acts = [c for c in content if c["cid"] in ACTIONS]
    ppl = [c for c in content if c["cid"] in PEOPLE]
    help_ = [c for c in content if c["cid"] in ("HELP", "HELP_EMERGENCY")]
    custom = [c for c in content if c["cid"] is None]
    other = [c for c in content if c not in feel + objs + acts + ppl + help_ + custom]
    act, frame = "UNKNOWN", None
    if explicit_want and not (feel or acts or help_ or objs) and (ppl or custom) and not other:
        objs = list(ppl + custom)                      # the user pressed WANT: a person or a typed word is the wanted thing
        ppl, custom = [], []
    if amb or not content:
        amb = True
    elif other:                                       # place, body part, greeting, GOOD/BAD, YOU, ...
        amb = len(content) == 1
        if len(content) == 1 and content[0]["cid"] in ("NAMASTE", "THANKS", "BYE"):
            act, amb = "GREETING", False
        elif len(content) == 2 and any(c["cid"] in ("NAMASTE", "THANKS", "BYE") for c in content):
            act = "GREETING"
        elif any(c["cid"] == "GO" for c in acts):
            act = "REQUEST"
    elif feel:
        if len(feel) > 1:
            act, amb = "UNKNOWN", True
        elif len(content) == 1:
            act, frame = "FEELING", "feeling"
        elif negation:                                # the negator could scope over the feeling or over the request
            act, amb = "UNKNOWN", True
        else:
            act, frame = "FEELING_REQUEST", "feeling_request"
    elif help_:
        act, frame = "REQUEST", "help"
    elif acts:
        act, frame = "REQUEST", "action"
    elif objs:
        act, frame = "REQUEST", "object"
    else:                                             # a person alone or a typed word alone
        amb = True
    if forced_act:                                    # explicit user choice (clarification button or act control) wins
        act, amb = forced_act, False
        if forced_act == "FEELING":
            frame = "feeling" if len(feel) == 1 and len(content) == 1 else None
        elif forced_act == "REQUEST":
            frame = ("help" if help_ else "action" if acts else "object" if (objs or custom) else None) if not (other or feel) else None
        elif forced_act == "FEELING_REQUEST":
            frame = "feeling_request" if len(feel) == 1 and len(content) > 1 and not other else None
        else:
            frame = None
    return dict(act=act, negation=negation, ambiguous=(amb or act == "UNKNOWN"), frame=frame, content=content, n_negators=neg_n)
