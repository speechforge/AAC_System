"""Request normalisation and the decision policy of the repaired hybrid (shared by the web backend and the evaluation harness).

* `normalize_request`  : act and polarity as separate fields; explicit user choice wins; legacy payloads (intent REQUEST / STATEMENT /
                         QUESTION / NEGATION, no `act`) are still accepted.
* `decide`             : the gate-and-fallback policy over a candidate stream.  The live path generates attempts lazily; the harness
                         replays saved streams through the same function, so every policy comparison uses identical candidates.
Outcomes (distinct, never conflated): sentence_model | sentence_template | clarification | literal_preview | failure | sentence_ungated.
"""
import time

import aac_lexicon as L

VALID_ACTS = {"REQUEST", "FEELING", "FEELING_REQUEST", "QUESTION", "GREETING", "UNKNOWN"}
ACT_TO_INTENT = {"REQUEST": "REQUEST", "FEELING": "STATEMENT", "FEELING_REQUEST": "REQUEST", "QUESTION": "QUESTION",
                 "GREETING": "STATEMENT", "UNKNOWN": "REQUEST"}
LEGACY_INTENT_TO_ACT = {"REQUEST": "REQUEST", "WANT": "REQUEST", "NEGATION": "REQUEST", "STATEMENT": "FEELING", "FEEL": "FEELING",
                        "FEELING": "FEELING", "QUESTION": "QUESTION"}


def _realiser_entities(content, lang):
    """Labels handed to the realiser; the quantity symbol MORE is kept in front of the item it modifies."""
    out = []
    for c in content:
        if c.get("more") and "MORE" in L.BOARD:
            out.append(L.BOARD["MORE"][lang if lang in L.LANGS else "en"])
        out.append(c["label"])
    return out


def normalize_request(r, reconcile=True):
    """r: request dict (AACRequest fields).  Returns the context used by the generator, the gate and the templates."""
    lang = r.get("language", "en")
    ents = list(r.get("entities") or [])
    ids = list(r.get("concept_ids") or [])
    ids = (ids + [None] * len(ents))[:len(ents)] if ids else [None] * len(ents)
    intent = (r.get("intent") or "REQUEST").upper()
    legacy_neg = bool(r.get("negation")) or intent == "NEGATION" or "NOT" in intent
    act_in = (r.get("act") or "").upper() or None
    source = r.get("act_source") or ("legacy" if act_in is None else "client")
    forced = act_in if (source == "user" and act_in in VALID_ACTS and act_in != "UNKNOWN") else None
    a = L.analyze_selection([dict(cid=i or None, label=e) for e, i in zip(ents, ids)], lang, forced_act=forced)
    reconciled = False
    if act_in in VALID_ACTS:
        act = act_in
        neg_field = r.get("negation")
        if r.get("polarity") in ("negative", "negated"):
            neg_field = True
        negation = bool(neg_field) if neg_field is not None else (a["negation"] or legacy_neg)
        if neg_field is False and a["negation"] and source != "user":
            negation = True                                  # a NO symbol is in the selection: the field cannot contradict it
    else:                                                    # legacy payload: honour the intent contract, reconcile only an unspecified act
        act = LEGACY_INTENT_TO_ACT.get(intent, "REQUEST")
        negation = legacy_neg or (a["negation"] and any((i == "NO") for i in ids))
        if reconcile and act == "REQUEST" and a["act"] in ("FEELING", "FEELING_REQUEST"):
            act, reconciled = a["act"], True
    content = a["content"] if (a["content"] and (act_in in VALID_ACTS or reconcile)) else [dict(cid=i or None, label=e, cat="custom", more=False) for e, i in zip(ents, ids)]
    ctx = dict(
        intent=ACT_TO_INTENT.get(act, "REQUEST"), actor=r.get("actor", "USER"),
        entities=_realiser_entities(content, lang), attributes=r.get("attributes", []), relations=r.get("relations", []),
        temporal_state=r.get("temporal_state"), location=r.get("location"), people=r.get("people", []), actions=r.get("actions", []),
        negation=bool(negation), speaker_role=r.get("speaker_role", "USER"), act=act, act_source=source,
        concept_ids=[c.get("cid") for c in content], content=content, code_mix=bool(r.get("code_mix", False)),
        analysis_act=a["act"], analysis_ambiguous=a["ambiguous"], reconciled=reconciled, legacy_negation=legacy_neg,
        literal=" ".join(e for e in ents if e),
    )
    return ctx


def _gate(validator, ctx, ledger, text, language):
    ok, d = validator.validate(ctx, ledger, text, language)
    return ok, d


def decide(ctx, language, get_attempt, validator, llm, max_retries=2, policy="hybrid", skip_deterministic_retry=False):
    """Apply a policy over a candidate stream.  `get_attempt(k)` returns an attempt dict
    {text, llm1, llm2, llm3_text, latency, error?, ledger?} or None when the stream has no k-th attempt."""
    out = dict(text=None, outcome=None, route=None, fallback_used=False, validated=False, attempts=[], act=ctx["act"],
               negation=ctx["negation"], act_source=ctx["act_source"], options=[], literal=ctx.get("literal"), gate_version=getattr(validator, "VERSION", "gate"),
               template_status=None, stream_incomplete=False)
    if ctx["act"] == "UNKNOWN" and policy in ("hybrid", "template_only"):
        out.update(outcome="clarification", route="clarification", options=["REQUEST", "FEELING"])
        return out
    if policy == "template_only":
        return _template_step(ctx, language, validator, llm, out, first_route="template_only")
    retries = 1 if (skip_deterministic_retry and language != "en" and not ctx.get("code_mix")) else max_retries
    last = None
    for k in range(retries):
        at = get_attempt(k)
        if at is None:
            out["stream_incomplete"] = True
            break
        rec = dict(k=k, text=at.get("text"), llm1=at.get("llm1"), llm2=at.get("llm2"), llm3_text=at.get("llm3_text"), latency=at.get("latency"),
                   error=at.get("error"))
        last = at
        if at.get("error") or not at.get("text"):
            rec.update(accepted=False, reasons=["pipeline_error" if at.get("error") else "empty"])
            out["attempts"].append(rec)
            continue
        if policy == "ungated":
            rec.update(accepted=True, reasons=[], gate_skipped=True)
            out["attempts"].append(rec)
            out.update(text=at["text"], outcome="sentence_ungated", route="ungated_first", validated=False)
            return out
        ok, d = _gate(validator, ctx, at.get("ledger") or {}, at["text"], language)
        rec.update(accepted=ok, reasons=d.get("violations_detected", []), score=d.get("semantic_score"))
        out["attempts"].append(rec)
        if ok:
            out.update(text=at["text"], outcome="sentence_model", route=("model_first" if k == 0 else "model_retry"), validated=True)
            return out
    if policy == "ungated":                                   # all attempts errored
        out.update(outcome="failure", route="ungated_error")
        return out
    return _template_step(ctx, language, validator, llm, out, first_route="template_after_rejection")


def _template_step(ctx, language, validator, llm, out, first_route):
    res = llm.realize_template(ctx, language)
    out["template_status"] = res.get("status")
    if res.get("status") == "ok":
        ok, d = _gate(validator, ctx, {}, res["text"], language)
        out["template_gate"] = dict(accepted=ok, reasons=d.get("violations_detected", []))
        if ok:
            out.update(text=res["text"], outcome="sentence_template", route=first_route, fallback_used=True, validated=True)
            return out
        out.update(text=res["text"], outcome="literal_preview", route="template_rejected_by_gate", options=[], literal=res.get("literal"))
        out["text"] = res.get("literal")                      # show the literal selection, not the unsafe sentence
        out["rejected_template_text"] = res["text"]
        return out
    if res.get("status") == "ambiguous":
        out.update(outcome="clarification", route="clarification_from_template", options=res.get("options", ["REQUEST", "FEELING"]))
        return out
    out.update(text=res.get("literal"), outcome="literal_preview", route="no_template_frame", literal=res.get("literal"))
    return out
