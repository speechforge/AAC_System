"""Context-aware next-word prediction at concept level, identical for en/hi/gu/mr.

Words in the sentence are mapped to board concept IDs (any language), the grammar of everyday AAC
speech decides which concepts usually follow, and the result is localised with BOARD[cid][lang].
This makes suggestions change with every selected word, even where the statistical model is sparse.
"""
from aac_lexicon import BOARD, resolve_label

FOOD = ["WATER", "FOOD", "MILK", "RICE", "ROTI", "FRUIT", "TEA", "JUICE", "SNACK", "PIZZA"]
FEEL = ["HAPPY", "SAD", "ANGRY", "TIRED", "SICK", "SCARED", "EXCITED", "LOVE"]
PEOPLE = ["MOTHER", "FATHER", "SISTER", "BROTHER", "TEACHER", "DOCTOR", "FRIEND"]
PLACES = ["HOME", "SCHOOL", "HOSPITAL", "TOILET", "ROOM", "MARKET"]
BODY = ["LUNGS", "HEART", "BRAIN", "BONE", "TOOTH", "EYE", "EAR", "NOSE"]

# Explicit successors by last concept (most specific rule wins), best first.
NEXT = {
    "ME": ["WANT", "EAT", "DRINK", "GO", "HELP", "TIRED", "HAPPY", "SICK", "LOVE", "PLAY"],
    "YOU": ["HELP", "GOOD", "HOW", "PLAY", "GO", "WANT", "LOVE", "CALL"],
    "WANT": FOOD[:4] + ["MORE", "PLAY", "HELP", "SLEEP", "GO", "BATH", "TOILET"],
    "EAT": ["FOOD", "RICE", "ROTI", "FRUIT", "SNACK", "PIZZA", "MORE", "PLEASE"],
    "DRINK": ["WATER", "MILK", "TEA", "JUICE", "MORE", "PLEASE"],
    "PLAY": ["FRIEND", "MORE", "OUTSIDE", "HOME", "PLEASE", "STOP"],
    "SLEEP": ["TIRED", "ROOM", "PLEASE", "STOP", "HOME"],
    "GO": ["HOME", "SCHOOL", "TOILET", "MARKET", "HOSPITAL", "ROOM", "PLEASE"],
    "STUDY": ["SCHOOL", "TEACHER", "HELP", "MORE", "STOP"],
    "BATH": ["PLEASE", "ROOM", "HELP", "MORE", "STOP"],
    "CALL": ["MOTHER", "FATHER", "DOCTOR", "FRIEND", "TEACHER", "HELP"],
    "WRITE": ["HELP", "MORE", "STOP", "TEACHER"],
    "LOOK": ["MOTHER", "FRIEND", "HELP", "MORE"],
    "HELP": ["PLEASE", "MOTHER", "DOCTOR", "FATHER", "PAIN", "TOILET", "MEDICINE"],
    "HELP_EMERGENCY": ["DOCTOR", "AMBULANCE", "MOTHER", "PAIN", "HOSPITAL", "FIRE"],
    "MORE": FOOD[:4] + ["PLAY", "PLEASE", "TIME", "STOP"],
    "STOP": ["PLEASE", "NO", "HELP", "THANKS"],
    "YES": ["PLEASE", "THANKS", "MORE", "GOOD", "WANT"],
    "NO": ["MORE", "STOP", "THANKS", "PAIN", "WANT", "HELP"],
    "PLEASE": ["HELP", "WATER", "FOOD", "MORE", "STOP", "GO", "THANKS"],
    "THANKS": ["BYE", "GOOD", "LOVE", "MORE", "FRIEND"],
    "NAMASTE": ["HOW", "ME", "YOU", "FRIEND", "THANKS"],
    "HOW": ["YOU", "GOOD", "BAD", "THANKS", "ME"],
    "BYE": ["THANKS", "FRIEND", "HOME", "LOVE"],
    "GOOD": ["THANKS", "MORE", "FOOD", "FRIEND", "LOVE", "BYE"],
    "BAD": ["PAIN", "SICK", "HELP", "STOP", "TIRED", "ANGRY"],
    "PAIN": ["HELP", "DOCTOR", "MEDICINE", "HOSPITAL", "MOTHER", "STOP", "AMBULANCE"],
    "SICK": ["DOCTOR", "MEDICINE", "HOSPITAL", "HELP", "MOTHER", "PAIN"],
    "MEDICINE": ["PLEASE", "HELP", "WATER", "DOCTOR", "MORE"],
    "TOILET": ["PLEASE", "HELP", "GO", "NOW"],
    "HOSPITAL": ["DOCTOR", "HELP", "PAIN", "AMBULANCE", "MOTHER"],
    "DOCTOR": ["HELP", "PAIN", "MEDICINE", "CALL", "HOSPITAL"],
    "AMBULANCE": ["HELP", "HOSPITAL", "DOCTOR", "CALL", "PAIN"],
    "FIRE": ["HELP_EMERGENCY", "AMBULANCE", "STOP", "SCARED", "GO"],
}
# Category defaults when no explicit rule exists.
CATEGORY_NEXT = {
    "food": ["PLEASE", "MORE", "THANKS", "GOOD", "NO", "YES", "EAT", "DRINK"],
    "feelings": ["HELP", "MOTHER", "PLEASE", "MORE", "STOP", "DOCTOR", "LOVE", "FRIEND"],
    "people": ["HELP", "CALL", "LOVE", "PLAY", "PLEASE", "WANT", "THANKS"],
    "places": ["GO", "PLEASE", "MORE", "FRIEND", "MOTHER", "STOP"],
    "body": ["PAIN", "HELP", "DOCTOR", "MEDICINE", "SICK", "STOP"],
    "actions": ["PLEASE", "MORE", "STOP", "HELP", "NOW"],
    "chat": ["ME", "YOU", "PLEASE", "THANKS", "HELP"],
    "emergency": ["HELP", "DOCTOR", "MOTHER", "PLEASE"],
    "core": ["PLEASE", "MORE", "HELP", "WANT"],
}
START = ["ME", "WANT", "HELP", "NAMASTE", "YOU", "WATER", "FOOD", "PAIN", "TOILET"]


def to_concepts(words):
    out = []
    for w in words:
        cid = resolve_label(w)
        out.append(cid)
    return out


def predict(words, language, top_k=10):
    """Return [{'word','emoji','prob','source':'context','cid'}] localised to `language`."""
    cids = to_concepts(words)
    known = [c for c in cids if c]
    chosen = set(known)
    ranked = []
    if not known:
        ranked = list(START)
    else:
        last = known[-1]
        ranked = list(NEXT.get(last) or CATEGORY_NEXT.get(BOARD[last]["cat"], []))
        # Second-to-last concept refines: e.g. "I want" -> food; "I feel" style combos get extras.
        if len(known) >= 2:
            prev = known[-2]
            if prev == "ME" and last in FEEL:
                ranked = ["PLEASE", "HELP", "MOTHER", "DOCTOR", "STOP"] + ranked
            if prev == "WANT" and last in FOOD:
                ranked = ["PLEASE", "MORE", "THANKS"] + ranked
            if prev == "NO" and last == "WANT":
                ranked = ["MORE", "FOOD", "WATER", "STOP", "PLAY"] + ranked
        # Backfill so there are always enough diverse choices.
        ranked += NEXT["ME"] + ["PLEASE", "HELP", "MORE", "THANKS"]
    out, seen = [], set()
    for cid in ranked:
        if cid in chosen or cid in seen or cid not in BOARD:
            continue
        seen.add(cid)
        rank = len(out)
        out.append({"word": BOARD[cid][language], "emoji": BOARD[cid]["emoji"],
                    "prob": round(max(0.05, 0.6 - rank * 0.05), 3), "source": "context", "cid": cid})
        if len(out) >= top_k:
            break
    return out
