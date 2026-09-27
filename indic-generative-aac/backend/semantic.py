import json
import re

class SemanticValidator:
    def __init__(self, llm):
        self.llm = llm

    def validate(self, context, ledger, generated_sentence, language="en"):
        """
        Hard Semantic Validator acting as the final authoritative gatekeeper.
        Applies strict deterministic verification and LLM-assisted scoring.
        """
        gen_lower = generated_sentence.lower().strip()
        data = {
            "intent_match": True,
            "entity_match": True,
            "negation_match": True,
            "temporal_match": True,
            "unsupported_additions": False,
            "violations_detected": []
        }

        # ── 1. Deterministic Negation Match ─────────────────────────
        negation_words = {
            "not", "no", "n't", "don't", "doesn't", "didn't", "never",
            "नहीं", "ना", "नको", "नाही", "નથી", "ના", "નહીં"
        }
        tokens = set(re.findall(r"[^\s।.,?!;:]+", gen_lower))
        has_negation = bool(tokens & negation_words)
        req_negation = bool(context.get("negation", False))

        if req_negation and not has_negation:
            data["negation_match"] = False
            data["violations_detected"].append("missing_required_negation")
        elif not req_negation and has_negation:
            data["negation_match"] = False
            data["violations_detected"].append("unsupported_negation_added")

        # ── 2. Deterministic Entity Match ───────────────────────────
        missing_entities = []
        for ent in context.get("entities", []):
            clean_ent = ent.strip('!?. ')
            parts = [p.strip().lower() for p in re.split(r'[/,]', clean_ent) if p.strip()]
            matched = False
            for p in parts:
                if (p in gen_lower or 
                    p.rstrip('s') in gen_lower or 
                    (p + 's') in gen_lower):
                    matched = True
                    break
                # Indic matra/oblique case inflections (e.g. खाना -> खाने में, रोटा -> रोटी/रोटे)
                if len(p) >= 2:
                    if p.endswith('ा') and (p[:-1] + 'े' in gen_lower or p[:-1] in gen_lower):
                        matched = True
                        break
                    if p.endswith('े') and (p[:-1] + 'ा' in gen_lower or p[:-1] in gen_lower):
                        matched = True
                        break
                    stem = p[:-1] if p[-1] in 'ाेीूो' else p
                    if len(stem) >= 2 and stem in gen_lower:
                        matched = True
                        break
            if not matched:
                missing_entities.append(ent)

        if missing_entities:
            data["entity_match"] = False
            data["missing_entities"] = missing_entities
            data["violations_detected"].append(f"missing_entities: {missing_entities}")

        # ── 3. Deterministic Forbidden Concepts & Additions ─────────
        forbidden_found = []
        for f in ledger.get("forbidden", []):
            if f and len(f) > 2:
                if re.search(rf'\b{re.escape(f.lower())}\b', gen_lower):
                    forbidden_found.append(f)

        if forbidden_found:
            data["unsupported_additions"] = True
            data["forbidden_detected"] = forbidden_found
            data["violations_detected"].append(f"forbidden_concepts: {forbidden_found}")

        # ── 4. Deterministic Temporal State Check ───────────────────
        temporal_words = [
            "today", "tomorrow", "yesterday", "morning", "night", "evening",
            "tonight", "breakfast", "lunch", "dinner", "later", "now"
        ]
        if not context.get("temporal_state"):
            for tw in temporal_words:
                if re.search(rf'\b{re.escape(tw)}\b', gen_lower):
                    data["temporal_match"] = False
                    data["violations_detected"].append(f"unsupported_temporal: {tw}")
                    data["unsupported_additions"] = True

        # ── 5. Deterministic Intent Check ───────────────────────────
        intent = context.get("intent", "").upper()
        if "FEEL" in intent or "STATEMENT" in intent:
            # If candidate expresses pure WANT ("I want ...") without feeling, flag mismatch
            if re.search(r'\bi want\b', gen_lower) and not re.search(r'\b(feel|feeling)\b', gen_lower):
                data["intent_match"] = False
                data["violations_detected"].append("intent_mismatch: WANT substituted for FEELING")
        elif "QUESTION" in intent:
            if not ("?" in generated_sentence or any(w in gen_lower for w in ["can", "could", "may", "where", "what", "how", "क्या", "का", "શું"])):
                data["intent_match"] = False
                data["violations_detected"].append("intent_mismatch: missing question structure")

        # ── 6. Score Calculation ────────────────────────────────────
        score = 0.0
        score += 0.3 if data["intent_match"] else 0.0
        score += 0.3 if data["entity_match"] else 0.0
        score += 0.2 if data["negation_match"] else 0.0
        score += 0.2 if data["temporal_match"] else 0.0

        if data["unsupported_additions"]:
            score = max(0.0, score - 0.4)

        data["semantic_score"] = round(score, 2)

        # ── Hard Gate Criteria ──────────────────────────────────────
        is_valid = (
            data["intent_match"] and
            data["entity_match"] and
            data["negation_match"] and
            not data["unsupported_additions"]
        )

        return is_valid, data
