"""Deterministic semantic gate (repaired).  A heuristic, not a proof of meaning preservation.

Checks (each yields a reason code; the gate accepts only when none fires):
  script_language     output is in the target script (no Latin leakage in Indic output)
  off_task            refusals, translations, quotes of the symbol label, tool talk
  speaker_perspective third-person reports ("the user ...", he/she/they, locale pronouns); implicit first person is valid
  missing_concept     a selected concept (board ID, else typed word) is absent (locale forms, inflections, token boundaries)
  added_concept       a board concept or distractor that was not selected appears (substitution = missing + added)
  added_reason_time   unrequested reason, time or venue words
  negation_missing / negation_spurious / negation_scope
                      polarity must match; the negator must sit in the clause of the selected concept (right word in the
                      wrong clause is rejected)
  act_wrong / act_missing
                      request marker for REQUEST, state marker without request marker for FEELING, both for FEELING_REQUEST,
                      question marker for QUESTION (locale rules in aac_lexicon.py)
  too_long            more than 25 tokens
`validate(context, ledger, text, language)` keeps the signature of the archived validator.
"""
import re

import aac_lexicon as L


class SemanticValidator:
    VERSION = "gate-v2"

    def __init__(self, llm=None):
        self.llm = llm

    # ------------------------------------------------------------------
    def _content(self, context, language):
        items = context.get("content")
        if items is None:
            ents = context.get("entities", [])
            ids = context.get("concept_ids") or [None] * len(ents)
            a = L.analyze_selection([dict(cid=(i or None), label=e) for e, i in zip(ents, ids)], language)
            items = a["content"]
        return items

    def validate(self, context, ledger, generated_sentence, language="en"):
        lang = language if language in L.LANGS else "en"
        text = generated_sentence or ""
        raw_lower = text.lower().strip()
        t = L.canon(text)
        toks = t.split()
        act = (context.get("act") or "REQUEST").upper()
        neg = bool(context.get("negation", False))
        code_mix = bool(context.get("code_mix", False))
        content = self._content(context, lang)
        v = []                                   # violation codes

        # script / language ------------------------------------------------
        lat, dev, guj = L.script_of(text)
        letters = max(1, lat + dev + guj)
        custom_latin = sum(ch.isascii() and ch.isalpha() for it in content if it.get("cid") is None for ch in it.get("label", ""))
        if not t:
            v.append("empty")
        elif not code_mix:
            if lang == "en":
                if lat / letters < 0.8:
                    v.append("script_language")
            else:
                want = guj if lang == "gu" else dev
                if want == 0 or max(0, lat - custom_latin) / letters > 0.3:
                    v.append("script_language")
        # off-task / meta ----------------------------------------------------
        if re.search(L.META_RX, raw_lower) or re.search(r"[\"“”]", text):
            v.append("off_task")
        if len(toks) > 25:
            v.append("too_long")
        # speaker perspective ------------------------------------------------
        if not code_mix and re.search(L.THIRD_PERSON[lang], t):
            v.append("speaker_perspective")

        # concepts -------------------------------------------------------------
        selected_forms, sel_ids = [], set()
        missing, present_sel = [], []
        for it in content:
            cid = it.get("cid")
            if cid:
                sel_ids.add(cid)
                forms = L.concept_forms(cid, lang) + (L.concept_forms(cid, "en") if code_mix else [])
                selected_forms += [f.lstrip("=") for f in forms]
                ok = L.concept_present(cid, lang, t, toks) or (code_mix and L.concept_present(cid, "en", t, toks))
            else:
                selected_forms.append(L.canon(it["label"]))
                ok = L.label_present(it["label"], lang, t, toks)
            (present_sel if ok else missing).append(cid or it["label"])
            if it.get("more"):
                more_rx = {"en": r"\bmore\b", "hi": r"(?<!\S)और(?!\S)", "gu": r"(વધુ|વધારે|ફરીથી)", "mr": r"(आणखी|अजून|जास्त)"}[lang]
                if not re.search(more_rx, t):
                    missing.append("MORE")
        sel_cids = {it.get("cid") for it in content}
        if lang == "hi" and {"EAT", "FOOD"} <= sel_cids and "EAT" not in missing and "FOOD" not in missing:
            # Hindi 'khana' names both the food and the verb 'eat': one occurrence cannot carry both selected concepts
            if (t.count("खाना") + t.count("खाने")) < 2 and not re.search("खाऊं|खाता|खाती|खाया", t):
                missing.append("EAT")
        if missing:
            v.append("missing_concept:" + ",".join(missing))

        added = []
        for cid in L.BOARD:
            if cid in sel_ids or cid in L.NOT_CONTENT:
                continue
            for f in L.concept_forms(cid, lang):
                if L._form_hits(f, t, toks, lang):
                    fb = f.lstrip("=")
                    if any((fb in sf) or (sf in fb) for sf in selected_forms if sf):
                        continue
                    added.append(cid)
                    break
        for f in L.EXTRA_DISTRACTORS[lang]:
            fc = L.canon(f)
            if L._form_hits(fc, t, toks, lang) and not any((fc in sf) or (sf in fc) for sf in selected_forms if sf):
                added.append(f)
        if added:
            v.append("added_concept:" + ",".join(sorted(set(added))))
        rt = re.search(L.REASON_TIME_RX[lang], t) if not code_mix else None
        if rt and not any(rt.group(0) in sf for sf in selected_forms if sf):
            v.append("added_reason_time:" + rt.group(0))

        # polarity and negation scope ------------------------------------------
        cls = L.clauses(text, lang)
        has_neg = any(L.has_negator(c, lang) for c in cls)
        if neg and not has_neg:
            v.append("negation_missing")
        elif (not neg) and has_neg:
            v.append("negation_spurious")
        elif neg and has_neg:
            # every clause that carries a selected concept must carry the negator (list items joined by 'and' share one clause)
            for c in cls:
                ctoks = c.split()
                carries = any((it.get("cid") and L.concept_present(it["cid"], lang, c, ctoks)) or
                              (it.get("cid") is None and L.label_present(it["label"], lang, c, ctoks)) for it in content)
                if carries and not L.has_negator(c, lang):
                    v.append("negation_scope")
                    break

        # communicative act ------------------------------------------------------
        feel_wanted = False
        for c in cls:
            ctoks = c.split()
            if any(it.get("cid") in L.FEELINGS and L.concept_present(it["cid"], lang, c, ctoks) for it in content) and re.search(L.REQUEST_RX[lang], c):
                feel_wanted = True                                # "I want tired": a feeling governed by a request marker
        req = bool(re.search(L.REQUEST_RX[lang], t))
        state = bool(re.search(L.STATE_RX[lang], t))
        if act == "REQUEST":
            if not req:
                v.append("act_wrong" if state else "act_missing")
        elif act == "FEELING":
            if req:
                v.append("act_wrong")
            elif not state:
                v.append("act_missing")
        elif act == "FEELING_REQUEST":
            if feel_wanted:
                v.append("act_wrong")
            elif not (req and state):
                v.append("act_wrong" if (req != state) else "act_missing")
        elif act == "QUESTION":
            if not re.search(L.QUESTION_RX[lang], text.lower()):
                v.append("act_missing")

        # ------------------------------------------------------------------------
        hard = [x for x in v]
        score = max(0.0, 1.0 - 0.25 * len(hard))
        data = dict(
            gate_version=self.VERSION,
            intent_match=not any(x.startswith("act_") for x in v),
            entity_match=not any(x.startswith("missing_concept") for x in v),
            negation_match=not any(x.startswith("negation") for x in v),
            temporal_match=not any(x.startswith("added_reason_time") for x in v),
            unsupported_additions=any(x.startswith(("added_", "off_task", "speaker")) for x in v),
            violations_detected=v,
            semantic_score=round(score, 2),
        )
        return (len(hard) == 0), data
