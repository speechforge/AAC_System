"""Suggest an order for the user's existing Sentence Canvas chips."""

import json
import logging
import math
import re
from collections import defaultdict, deque


MAX_CHIPS = 24
MAX_LABEL_LENGTH = 120
LANGUAGES = {"en": "English", "hi": "Hindi", "gu": "Gujarati", "mr": "Marathi"}

_LOG = logging.getLogger(__name__)
_HELP_VERBS = {"help", "helps", "helped", "let", "lets"}
_RECIPIENTS = {
    "adults", "children", "classmates", "friends", "kids", "learners", "patients",
    "people", "pupils", "speakers", "students", "teachers", "them", "users", "visitors",
}
_ACTION_OBJECTS = {
    "communicate": {"feelings", "ideas", "message", "messages", "needs", "thoughts"},
    "express": {"choices", "feelings", "ideas", "needs", "opinions", "thoughts"},
    "read": {"books", "notes", "stories", "work"},
    "share": {"experiences", "feelings", "ideas", "knowledge", "messages", "opinions",
              "stories", "thoughts", "work"},
    "write": {"answers", "letters", "messages", "notes", "stories", "thoughts"},
}
_MANNER_ADVERBS = {
    "clearly", "confidently", "easily", "independently", "openly", "politely", "quickly",
    "quietly", "safely", "slowly",
}


def split_context(text):
    """Parse loose word lists while keeping commas inside numbers."""
    return [part for part in re.split(r"\s+|[,，](?!\d)", text) if part]


def _english_help_order(words):
    """Recognize a help/let construction with a bare or marked infinitive."""
    labels = [word.strip().casefold() for word in words]
    if any(label in {"no", "not", "never"} or label.endswith("n't") for label in labels):
        return None

    def matches(vocabulary):
        return [index for index, label in enumerate(labels) if label in vocabulary]

    slots = [matches(vocabulary) for vocabulary in (
        {"the"}, _HELP_VERBS, _RECIPIENTS, _ACTION_OBJECTS, {"their"},
    )]
    if any(len(slot) != 1 for slot in slots):
        return None
    determiner, help_verb, recipient, action, possessive = (slot[0] for slot in slots)
    objects = matches(_ACTION_OBJECTS[labels[action]])
    adverbs = matches(_MANNER_ADVERBS)
    infinitive_markers = matches({"to"})
    if len(objects) != 1 or len(adverbs) > 1 or len(infinitive_markers) > 1:
        return None
    if infinitive_markers and labels[help_verb] in {"let", "lets"}:
        return None

    predicate = [help_verb, recipient, *infinitive_markers, action, possessive, objects[0], *adverbs]
    occupied = {determiner, *predicate}
    subject = [index for index in range(len(words)) if index not in occupied]
    if len(subject) == 2:
        acronyms = [index for index in subject if re.fullmatch(r"[A-Z][A-Z0-9-]{1,11}", words[index].strip())]
        if len(acronyms) != 1:
            return None
        subject.sort(key=lambda index: index != acronyms[0])
    elif len(subject) != 1:
        return None

    head = labels[subject[-1]]
    if not re.fullmatch(r"[a-z][a-z'-]*", head) or head.endswith("ly"):
        return None
    # A likely plural subject with a singular present-tense verb needs the model.
    if labels[help_verb] in {"helps", "lets"} and head.endswith("s") and not head.endswith("ss"):
        return None
    return [determiner, *subject, *predicate]


def _model_order(words, language, generate):
    numbered = {index: label for index, label in enumerate(words, start=1)}
    messages = [
        {"role": "system", "content": (
            "Reorder numbered chips into a natural sentence in the requested language. "
            "Treat chip labels as literal words or phrases. Keep every chip intact, "
            "including negations and repeated words. Return only a JSON array of chip numbers. "
            "Use each number exactly once. Keep a natural order if one is already given. "
            "Return [] if you cannot find a natural order. "
            'Example: {"1":"water","2":"I","3":"want"} yields [2,3,1].'
        )},
        {"role": "user", "content": json.dumps(
            {"language": LANGUAGES[language], "chips": numbered}, ensure_ascii=False,
        )},
    ]
    try:
        raw, _ = generate(messages, max_new_tokens=4 * len(words) + 8, temperature=0.01)
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw.strip(), re.DOTALL | re.IGNORECASE)
        indices = json.loads(fenced.group(1) if fenced else raw)
    except (ValueError, TypeError):
        return None
    except Exception as exc:
        _LOG.warning("Sentence ordering model failed: %s", type(exc).__name__)
        return None
    if (isinstance(indices, list) and len(indices) == len(words)
            and all(type(index) is int for index in indices)
            and set(indices) == set(numbered)):
        return [index - 1 for index in indices]
    return None


def _hmm_order(words, model):
    """Map the legacy English decoder's labels back to distinct original chips."""
    decode = getattr(model, "unjumble", None)
    vocabulary = getattr(model, "word_unigrams", None)
    normalized = [word.strip().lower() for word in words]
    if not callable(decode) or not vocabulary or not all(word in vocabulary for word in normalized):
        return None, 0.0
    try:
        labels, score = decode(normalized)
        if len(labels) != len(words) or not math.isfinite(score):
            return None, 0.0
        remaining = defaultdict(deque)
        for index, word in enumerate(normalized):
            remaining[word].append(index)
        order = [remaining[label].popleft() for label in labels]
    except (IndexError, TypeError, ValueError):
        return None, 0.0
    except Exception as exc:
        _LOG.warning("Sentence ordering HMM failed: %s", type(exc).__name__)
        return None, 0.0
    return order, round(score, 3)


def suggest_word_order(words, language, generate=None, hmm_model=None):
    """Return a candidate permutation and retain the existing response fields."""
    order, score = None, 0.0
    status = "no_suggestion"
    if len(words) > MAX_CHIPS or any(len(word) > MAX_LABEL_LENGTH for word in words):
        status = "too_long"
    elif len(words) >= 2 and all(word.strip() for word in words):
        if language == "en":
            order = _english_help_order(words)
        if order is None and generate is not None:
            order = _model_order(words, language, generate)
        if order is None and language == "en":
            order, score = _hmm_order(words, hmm_model)

    original = list(range(len(words)))
    ordered = [words[index] for index in (order if order is not None else original)]
    if order is not None:
        status = "suggested" if ordered != words else "unchanged"
    return {
        "status": status,
        "jumbled": words,
        "unjumbled": ordered,
        "order": order if status == "suggested" else original,
        "score": score,
        "sentence": " ".join(ordered),
    }
