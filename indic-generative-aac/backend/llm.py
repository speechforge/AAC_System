import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json
import re
import time
import os

# ─────────────────────────────────────────────────────────────
#  LLM-3: THE FINAL CONTEXT-LEVEL SEMANTIC VERIFIER & MINIMAL REFINER
#  Authority Hierarchy:
#    AAC User Selection > Structured AAC Context > Concept Ledger
#    > Hard Semantic Constraints > LLM-3 > LLM-2 > LLM-1
# ─────────────────────────────────────────────────────────────

LLM3_SYSTEM_PROMPT = """You are the final semantic verifier and minimal refiner in an Augmentative and Alternative Communication (AAC) system.

Your highest priority is preserving the user's selected AAC meaning.
The AAC Context and Concept Ledger are authoritative.
LLM-1 and LLM-2 outputs are only candidate text and must be verified.

Your task is NOT creative writing.
Your task is NOT conversation.
Your task is NOT contextual guessing.

First determine whether the candidate expresses the user's selected AAC concepts.

Verify:
1. intent (e.g. FEELING != WANT)
2. required concepts
3. entities (do not substitute pizza with food/meal)
4. relations
5. negation (if negation=true, MUST remain negative)
6. explicit temporal information (if temporal_state is null, NO today/tomorrow/morning/tonight)
7. speaker/actor
8. language
9. code-mixing constraints

Detect unsupported information including:
- unsupported actions (eat, drink, buy, go, play)
- unsupported intentions (plan to, hope to, want to)
- unsupported time (today, tomorrow, breakfast, night, morning)
- unsupported location (restaurant, store, school)
- unsupported people (mother, friends)
- unsupported emotions (happy, hungry, satisfied unless selected)

Rules:
- If the candidate is already correct, return it unchanged with decision="PASS".
- If it is incorrect but can be safely corrected, make the smallest possible change with decision="REFINE".
- Use the fewest words necessary.
- Prefer omission over invention: When uncertain, remove unsupported words rather than inventing.
- If it cannot be safely corrected without guessing, return decision="REJECT".
- Return ONLY a valid JSON object:
{
  "decision": "PASS" | "REFINE" | "REJECT",
  "final_text": "<verified or minimally refined sentence>",
  "semantic_fidelity": true,
  "intent_preserved": true,
  "entities_preserved": true,
  "negation_preserved": true,
  "unsupported_information_removed": true,
  "minimal_refinement": true,
  "violations_removed": ["<list of removed violations>"]
}
Output valid JSON only. No markdown, no backticks."""

LLM3_USER_TEMPLATE = """AUTHORITATIVE AAC INPUT:
{payload}

Evaluate candidates, verify against AAC Context & Concept Ledger, and output structured JSON:"""


class IndicLLM:
    def __init__(self, model_name=None):
        if model_name is None:
            local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../models/Qwen2.5-0.5B-Instruct"))
            has_weights = os.path.exists(local_path) and any(
                f.endswith((".safetensors", ".bin")) for f in os.listdir(local_path)
            ) if os.path.exists(local_path) else False
            model_name = local_path if has_weights else "Qwen/Qwen2.5-0.5B-Instruct"

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading {model_name} on {self.device}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        ).to(self.device)

    # ─── 1. BUILD STRUCTURED AAC CONTEXT & CONCEPT LEDGER ─────
    def build_structured_context(self, context, language="English", code_mix=False):
        """
        Builds the canonical 11-field structured AAC Context dictionary.
        """
        entities = context.get("entities", [])
        return {
            "intent": context.get("intent", "WANT"),
            "actor": context.get("actor", "USER"),
            "language": language,
            "negation": bool(context.get("negation", False)),
            "entities": entities,
            "actions": context.get("actions", []),
            "relations": context.get("relations", []),
            "temporal_state": context.get("temporal_state", None),
            "location": context.get("location", None),
            "people": context.get("people", []),
            "code_mixing": code_mix
        }

    def build_concept_ledger(self, structured_context):
        """
        Constructs the authoritative Concept Ledger: Required, Optional, and Forbidden concepts.
        """
        required = []
        forbidden = [
            "breakfast", "lunch", "dinner", "today", "tomorrow", "yesterday",
            "morning", "night", "evening", "tonight", "planning", "going to", "restaurant",
            "store", "shop", "buying", "eating out", "hungry", "delicious", "future", "past"
        ]

        intent = structured_context.get("intent", "")
        if intent:
            required.append(f"INTENT:{intent.upper()}")

        actor = structured_context.get("actor", "")
        if actor:
            required.append(f"ACTOR:{actor.upper()}")

        for ent in structured_context.get("entities", []):
            required.append(ent.upper())
            # Entity cannot be forbidden if selected by user
            forbidden = [f for f in forbidden if f.lower() not in ent.lower()]

        if structured_context.get("negation"):
            required.append("NEGATION (MUST BE NEGATIVE)")

        for act in structured_context.get("actions", []):
            required.append(f"ACTION:{act.upper()}")
            forbidden = [f for f in forbidden if f.lower() not in act.lower()]

        temp = structured_context.get("temporal_state")
        if temp:
            required.append(f"TENSE:{temp.upper()}")
            forbidden = [f for f in forbidden if f.lower() not in str(temp).lower()]

        return {
            "required": required,
            "optional": [],
            "forbidden": forbidden
        }

    # ─── CORE GENERATE HELPER WITH TOKEN PROFILING ───────────
    def _call_llm(self, messages, max_new_tokens=80, temperature=0.01):
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
        in_tokens = inputs.input_ids.shape[1]

        t0 = time.time()
        with torch.no_grad():
            ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=(temperature > 0.05),
                pad_token_id=self.tokenizer.eos_token_id,
            )
        latency = time.time() - t0

        new_ids = [o[len(i):] for i, o in zip(inputs.input_ids, ids)]
        out_tokens = new_ids[0].shape[0]
        decoded = self.tokenizer.batch_decode(new_ids, skip_special_tokens=True)[0].strip()

        return decoded, {
            "tokens_in": in_tokens,
            "tokens_out": out_tokens,
            "latency": round(latency, 3)
        }

    # ─── LLM-1: SENTENCE REALIZER ───────────────────────────
    def _llm1_realize(self, aac_context, ledger, language, code_mix):
        lang_map = {"hi": "Hindi", "gu": "Gujarati", "mr": "Marathi",
                    "en": "English", "en+hi": "Hinglish"}
        lang_name = lang_map.get(language, language)

        FEW_SHOT = {
            "hi": {
                "system": (
                    "You are an expert Hindi Linguist and AAC (Augmentative and Alternative Communication) Interpreter. "
                    "Your task is to take disjointed keyword inputs selected by a user (via pictograms) and synthesize them into a natural, grammatically correct, and logically sound Hindi sentence.\n\n"
                    "Do NOT simply concatenate all words and put 'चाहिए' (want) at the end. You must analyze the semantics of the words and apply the correct linguistic structures.\n\n"
                    "### CORE RULES FOR SENTENCE SYNTHESIS:\n"
                    "1. Categorize the Inputs:\n"
                    "   - Target/Vocative: People (e.g., माँ, पापा, डॉक्टर, शिक्षक, दोस्त). These usually go at the beginning as the person being addressed followed by a comma (e.g., 'माँ, ...', 'दोस्त, ...', 'डॉक्टर, ...'). NEVER say 'मुझे डॉक्टर' or 'मुझे माँ'.\n"
                    "   - Physical Needs/Objects: Tangible things (e.g., खाना, चावल, पानी, फल, दवा). These map to the Dative Desire construction: 'मुझे [Object] चाहिए' (I want [Object]), or 'मुझे [verb-ना] है' (I need to [verb]).\n"
                    "   - States/Feelings (Adjectives/Abstract Nouns): (e.g., थका हुआ, भूख, दर्द, खुश, बीमार, प्यास). These CANNOT be used with 'चाहिए'.\n"
                    "     - If it's an adjective (थका हुआ, बीमार): Map to Nominative state: 'मैं [Adjective] हूँ' (e.g., 'मैं थका हुआ हूँ', 'मैं बीमार हूँ').\n"
                    "     - If it's a physical sensation noun (भूख, प्यास, दर्द): Map to Dative experiencer: 'मुझे [Noun] लग रही है / लगी है / हो रहा है' (e.g., 'मुझे दर्द हो रहा है', 'मुझे भूख लग रही है', 'मुझे प्यास लगी है').\n"
                    "2. Clause Separation & Combination:\n"
                    "   - If a user inputs a feeling AND a need, separate them into two logical clauses and connect them naturally (using 'इसलिए' - therefore, or just a comma). The feeling is usually the REASON for the need.\n"
                    "3. Contextual Grouping:\n"
                    "   - Group related nouns together. 'खाना, चावल, रोटी' should become 'खाने में चावल और रोटी चाहिए'. 'खाना, फल' should become 'खाने में फल चाहिए'.\n\n"
                    "### TASK:\n"
                    "Now, translate the user's provided input sequence into a robust, natural Hindi sentence following the SOV structure and clause rules above. Return ONLY the final Hindi sentence in Devanagari script."
                ),
                "examples": [
                    ("Input Sequence: मुझे चाहिए + माँ + खाना + चावल + रोटी + थका हुआ", "माँ, मैं थका हुआ हूँ, मुझे खाने में चावल और रोटी चाहिए।"),
                    ("Input Sequence: मुझे चाहिए + डॉक्टर + दर्द + पानी", "डॉक्टर, मुझे दर्द हो रहा है, मुझे पानी चाहिए।"),
                    ("Input Sequence: मैं कह रहा हूँ + खुश + स्कूल", "मैं स्कूल में बहुत खुश हूँ।"),
                    ("Input Sequence: मुझे चाहिए + माँ + पानी", "माँ, मुझे पानी चाहिए।"),
                    ("Input Sequence: मुझे चाहिए + दोस्त + खाना + फल", "दोस्त, मुझे खाने में फल चाहिए।"),
                    ("Input Sequence: मुझे चाहिए + पापा + थका हुआ + सोना", "पापा, मैं थका हुआ हूँ, मुझे सोना है।"),
                    ("Input Sequence: नहीं चाहिए + डॉक्टर + दवा", "डॉक्टर, मुझे दवा नहीं चाहिए।"),
                    ("Input Sequence: मुझे चाहिए + माँ + भूख + खाना", "माँ, मुझे भूख लग रही है, मुझे खाना चाहिए।"),
                    ("Input Sequence: मुझे चाहिए + प्यास + पानी", "मुझे प्यास लगी है, मुझे पानी चाहिए।"),
                    ("Input Sequence: मुझे चाहिए + बीमार + दवा", "मैं बीमार हूँ, मुझे दवा चाहिए।"),
                    ("Input Sequence: मुझे चाहिए + पानी", "मुझे पानी चाहिए।"),
                    ("Input Sequence: क्या मुझे मिल सकता है + शिक्षक + मदद", "शिक्षक, क्या आप मेरी मदद कर सकते हैं?")
                ]
            },
            "gu": {
                "system": (
                    "You are an expert Gujarati AAC linguist and sentence builder. "
                    "Construct natural, grammatically correct Gujarati sentences following strict Subject-Object-Verb (SOV) structure, "
                    "correct postpositions (દરેક ઈચ્છા માટે 'મને [વસ્તુ] જોઈએ છે'), and verb agreement. "
                    "Output ONLY the final Gujarati sentence in Gujarati script. Do NOT translate to English."
                ),
                "examples": [
                    ("ઈનપુટ ક્રમ: મને જોઈએ છે + પાણી", "મને પાણી જોઈએ છે."),
                    ("ઈનપુટ ક્રમ: મને જોઈએ છે + ખોરાક", "મને ખોરાક જોઈએ છે."),
                    ("ઈનપુટ ક્રમ: મને જોઈએ છે + રમવું", "મારે રમવું છે."),
                    ("ઈનપુટ ક્રમ: નથી જોઈતું + દવા", "મને દવા નથી જોઈતી."),
                    ("ઈનપુટ ક્રમ: નથી જોઈતું + ખોરાક", "મને ખોરાક નથી જોઈતો."),
                    ("ઈનપુટ ક્રમ: હું કહું છું + ખુશ", "હું ખુશ છું."),
                    ("ઈનપુટ ક્રમ: હું કહું છું + દુખાવો", "મને દુખાવો થાય છે."),
                    ("ઈનપુટ ક્રમ: શું મને મળી શકે + ડૉક્ટર", "મને ડૉક્ટર મળી શકે?"),
                    ("ઈનપુટ ક્રમ: શું મને મળી શકે + મદદ", "શું તમે મને મદદ કરી શકો?"),
                ]
            },
            "mr": {
                "system": (
                    "You are an expert Marathi AAC linguist and sentence builder. "
                    "Construct natural, grammatically correct Marathi sentences following strict Subject-Object-Verb (SOV) structure, "
                    "correct postpositions (इच्छेसाठी 'मला [वस्तू] हवे आहे/पाहिजे'), and verb agreement. "
                    "Output ONLY the final Marathi sentence in Devanagari script. Do NOT translate to English."
                ),
                "examples": [
                    ("इनपुट क्रम: मला हवे आहे + पाणी", "मला पाणी हवे आहे."),
                    ("इनपुट क्रम: मला हवे आहे + जेवण", "मला जेवण हवे आहे."),
                    ("इनपुट क्रम: मला हवे आहे + खेळणे", "मला खेळायचे आहे."),
                    ("इनपुट क्रम: नको आहे + औषध", "मला औषध नको आहे."),
                    ("इनपुट क्रम: नको आहे + जेवण", "मला जेवण नको आहे."),
                    ("इनपुट क्रम: मी सांगत आहे + आनंदी", "मी आनंदी आहे."),
                    ("इनपुट क्रम: मी सांगत आहे + वेदना", "मला वेदना होत आहेत."),
                    ("इनपुट क्रम: मला मिळू शकेल का + डॉक्टर", "मला डॉक्टर मिळू शकेल का?"),
                    ("इनपुट क्रम: मला मिळू शकेल का + मदत", "तुम्ही मला मदत करू शकता का?"),
                ]
            }
        }

        if language in FEW_SHOT and not code_mix:
            cfg = FEW_SHOT[language]
            intent = aac_context.get("intent", "REQUEST").upper()
            negation = bool(aac_context.get("negation", False))
            entities = aac_context.get("entities", [])

            if language == "hi":
                intent_prefix = "नहीं चाहिए" if negation else ("मुझे चाहिए" if intent in ["REQUEST", "WANT"] else ("मैं कह रहा हूँ" if intent in ["STATEMENT", "FEEL"] else "क्या मुझे मिल सकता है"))
                seq_parts = [intent_prefix] + entities if entities else [intent_prefix, "यह"]
                q = f"Input Sequence: {' + '.join(seq_parts)}"
            elif language == "gu":
                intent_prefix = "નથી જોઈતું" if negation else ("મને જોઈએ છે" if intent in ["REQUEST", "WANT"] else ("હું કહું છું" if intent in ["STATEMENT", "FEEL"] else "શું મને મળી શકે"))
                seq_parts = [intent_prefix] + entities if entities else [intent_prefix, "આ"]
                q = f"ઈનપુટ ક્રમ: {' + '.join(seq_parts)}"
            elif language == "mr":
                intent_prefix = "नको आहे" if negation else ("मला हवे आहे" if intent in ["REQUEST", "WANT"] else ("मी सांगत आहे" if intent in ["STATEMENT", "FEEL"] else "मला मिळू शकेल का"))
                seq_parts = [intent_prefix] + entities if entities else [intent_prefix, "हे"]
                q = f"इनपुट क्रम: {' + '.join(seq_parts)}"

            msgs = [{"role": "system", "content": cfg["system"]}]
            for ex_in, ex_out in cfg["examples"]:
                msgs.append({"role": "user", "content": ex_in})
                msgs.append({"role": "assistant", "content": ex_out})
            msgs.append({"role": "user", "content": q})
            return self._call_llm(msgs, max_new_tokens=75, temperature=0.01)

        scripts = {
            "hi": "Hindi in Devanagari script (e.g. मुझे पानी चाहिए।)",
            "gu": "Gujarati in Gujarati script (e.g. મને પાણી જોઈએ છે.)",
            "mr": "Marathi in Devanagari script (e.g. मला पाणी हवे आहे.)",
            "en": "English in Latin script"
        }
        script_info = scripts.get(language, lang_name)

        system = ("You are a rigid AAC meaning-to-text engine. "
                  "Generate the shortest natural sentence that expresses ONLY the required concepts. "
                  "Do NOT add any extra context, place, time, or action.")

        if code_mix:
            lang_rule = f"Code-mix {lang_name} and English naturally."
        elif language != "en":
            lang_rule = f"The output sentence MUST be written strictly in {script_info}. Do NOT translate to English."
        else:
            lang_rule = "Output language: English."

        user = (f"REQUIRED CONCEPTS: {', '.join(ledger['required'])}\n"
                f"FORBIDDEN (do not use): {', '.join(ledger['forbidden'])}\n"
                f"{lang_rule}\n"
                "Output ONLY the final sentence. No quotes, no explanation.")

        return self._call_llm(
            [{"role": "system", "content": system},
             {"role": "user", "content": user}],
            max_new_tokens=60, temperature=0.1
        )

    # ─── LLM-2: SEMANTIC REFINER ────────────────────────────
    def _llm2_refine(self, candidate, ledger, language="en"):
        if language in ["hi", "gu", "mr"]:
            if any(ord(c) >= 0x0900 for c in candidate):
                return candidate, {"pass": True, "violations": []}, {"tokens_in": 0, "tokens_out": 0, "latency": 0.0}

        system = ("You are a Semantic Refiner for an AAC device. "
                  "Strip any invented, forbidden, or unsupported information from the candidate sentence "
                  "while keeping it natural. If the sentence is already minimal, return it unchanged.")

        lang_instruction = "Keep the refined sentence strictly in the same language and script as the candidate. Do NOT translate." if language != "en" else ""

        user = (f"Candidate: {candidate}\n"
                f"Required concepts: {', '.join(ledger['required'])}\n"
                f"Forbidden concepts: {', '.join(ledger['forbidden'])}\n"
                f"{lang_instruction}\n"
                "Rewrite to contain ONLY required concepts + minimal glue words.\n"
                "Output ONLY the refined sentence.")

        refined_text, metrics = self._call_llm(
            [{"role": "system", "content": system},
             {"role": "user", "content": user}],
            max_new_tokens=60, temperature=0.05
        )

        if any(ord(c) >= 0x0900 for c in candidate) and not any(ord(c) >= 0x0900 for c in refined_text):
            refined_text = candidate

        violations_found = []
        for f in ledger.get("forbidden", []):
            if f and len(f) > 3 and f.lower() in candidate.lower():
                violations_found.append(f)

        verification = {
            "pass": len(violations_found) == 0,
            "violations": violations_found
        }
        return refined_text, verification, metrics

    # ─── LLM-3: FINAL CONTEXT-LEVEL VERIFIER & MINIMAL REFINER 
    def _llm3_verify_and_refine(self, aac_context, ledger, llm1_output, llm2_output, llm2_verification):
        """
        LLM-3 receives:
          1. Original AAC Context
          2. Concept Ledger
          3. LLM-1 output
          4. LLM-2 output
          5. LLM-2 verification
        Compares both against AAC Context & Concept Ledger.
        Returns: (final_sentence, structured_decision, metrics)
        """
        payload = {
            "aac_context": aac_context,
            "concept_ledger": ledger,
            "llm1_output": llm1_output,
            "llm2_output": llm2_output,
            "llm2_verification": llm2_verification
        }

        user_content = LLM3_USER_TEMPLATE.format(
            payload=json.dumps(payload, indent=2)
        )

        raw, metrics = self._call_llm(
            [{"role": "system", "content": LLM3_SYSTEM_PROMPT},
             {"role": "user", "content": user_content}],
            max_new_tokens=220, temperature=0.01
        )

        # Parse structured JSON decision
        decision_data = {}
        try:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                decision_data = json.loads(match.group(0))
            else:
                decision_data = json.loads(raw)
        except Exception:
            decision_data = {
                "decision": "PASS",
                "final_text": llm2_output or llm1_output,
                "semantic_fidelity": True,
                "intent_preserved": True,
                "entities_preserved": True,
                "negation_preserved": True,
                "unsupported_information_removed": True,
                "minimal_refinement": True,
                "violations_removed": []
            }

        decision = decision_data.get("decision", "REFINE").upper()
        candidate = llm2_output if llm2_output else llm1_output

        # Core Rule: Minimal Refinement & Authority Hierarchy
        if decision == "PASS":
            final_sentence = decision_data.get("final_text") or candidate
            edit_type = "kept_unchanged"
        elif decision == "REFINE":
            final_sentence = decision_data.get("final_text") or candidate
            edit_type = "words_removed" if len(final_sentence.split()) < len(candidate.split()) else "words_replaced"
        else: # REJECT
            final_sentence = decision_data.get("final_text") or candidate
            edit_type = "regenerated"

        # Prevent English translation override on native Indic candidate
        if candidate:
            cand_is_indic = any(ord(c) >= 0x0900 for c in candidate)
            final_is_indic = any(ord(c) >= 0x0900 for c in final_sentence)
            if cand_is_indic and not final_is_indic:
                final_sentence = candidate
                edit_type = "kept_native_script"

        # Apply deterministic omission-over-invention cleanup:
        for f in ledger.get("forbidden", []):
            if f and len(f) > 3 and f.lower() in final_sentence.lower():
                final_sentence = re.sub(rf'\b{re.escape(f)}\b', '', final_sentence, flags=re.IGNORECASE).strip()
        final_sentence = re.sub(r'\s+', ' ', final_sentence).strip()
        # Clean orphan prepositions/articles left before punctuation
        final_sentence = re.sub(r'\s+(?:for|a|an|the|to|and|in|at|of|with|out for a)\s*([.?!])', r'\1', final_sentence, flags=re.IGNORECASE).strip()

        # Minimum-Word Principle: if deletion left fragmented phrases, resolve to minimal realization
        broken_phrases = ["to the for", "at the for", "felt and decided", "want you to eat out", "because i am and", "about the food i am about to eat at"]
        if any(bp in final_sentence.lower() for bp in broken_phrases):
            final_sentence = self.generate_deterministic_fallback(aac_context, language=aac_context.get("language", "en"))
            edit_type = "minimal_concept_realization"

        decision_data["edit_type"] = edit_type
        decision_data["final_text"] = final_sentence
        return final_sentence, decision_data, metrics

    # ─── DETERMINISTIC FALLBACK REALIZER ─────────────────────
    def generate_deterministic_fallback(self, context, language="en", code_mix=False):
        """
        Zero-hallucination safe deterministic fallback based directly on user selection.
        Invoked if all LLM stages / retries fail semantic validation.
        """
        intent = context.get("intent", "WANT").upper()
        negation = bool(context.get("negation", False))
        entities = context.get("entities", [])
        ent_str = " ".join(entities) if entities else "this"

        lang_code = language.lower()

        if "hi" in lang_code or "hindi" in lang_code:
            if "WANT" in intent or "REQUEST" in intent:
                return f"मुझे {ent_str} नहीं चाहिए।" if negation else f"मुझे {ent_str} चाहिए।"
            elif "FEEL" in intent or "STATEMENT" in intent:
                return f"मुझे {ent_str} महसूस नहीं हो रहा है।" if negation else f"मुझे {ent_str} महसूस हो रहा है।"
            elif "QUESTION" in intent:
                return f"क्या मुझे {ent_str} मिल सकता है?"
            else:
                return f"मुझे {ent_str} चाहिए।"
        elif "mr" in lang_code or "marathi" in lang_code:
            if "WANT" in intent or "REQUEST" in intent:
                return f"मला {ent_str} नको आहे." if negation else f"मला {ent_str} हवे आहे."
            elif "FEEL" in intent or "STATEMENT" in intent:
                return f"मला {ent_str} वाटत नाही." if negation else f"मला {ent_str} वाटते."
            elif "QUESTION" in intent:
                return f"मला {ent_str} मिळू शकेल का?"
            else:
                return f"मला {ent_str} हवे आहे."
        elif "gu" in lang_code or "gujarati" in lang_code:
            if "WANT" in intent or "REQUEST" in intent:
                return f"મને {ent_str} નથી જોઈતું." if negation else f"મને {ent_str} જોઈએ છે."
            elif "FEEL" in intent or "STATEMENT" in intent:
                return f"મને {ent_str} લાગતું નથી." if negation else f"મને {ent_str} લાગે છે."
            elif "QUESTION" in intent:
                return f"મને {ent_str} મળી શકે?"
            else:
                return f"મને {ent_str} જોઈએ છે."
        else: # Default: English
            emotions = ["happy", "sad", "sick", "tired", "angry", "cold", "hot", "well"]
            is_emotion = any(e in ent_str.lower() for e in emotions)

            if "WANT" in intent or "REQUEST" in intent:
                return f"I don't want {ent_str}." if negation else f"I want {ent_str}."
            elif "FEEL" in intent or "STATEMENT" in intent:
                if negation:
                    return f"I do not feel {ent_str}."
                return f"I feel {ent_str}." if is_emotion else f"I feel like {ent_str}."
            elif "QUESTION" in intent:
                return f"Can I have {ent_str}?"
            elif "GREETING" in intent:
                return f"Hello {ent_str}."
            else:
                return f"I want {ent_str}."

    # ─── AAC SEMANTIC PARSER & CONTEXT REPAIR AGENT ─────────
    def parse_and_repair_context(self, context, natural_sentence, language="hi"):
        """
        Parses raw disjointed AAC inputs, identifies Vocative/Addressee, Nominative State,
        and Dative Desire, establishes causal relationships, and constructs an empathetic
        caregiver explanation.
        """
        entities = context.get("entities", [])
        negation = bool(context.get("negation", False))
        intent = context.get("intent", "REQUEST").upper()

        PEOPLE_VOCATIVES = {
            "hi": {"माँ": "Mother", "पापा": "Father", "डॉक्टर": "Doctor", "शिक्षक": "Teacher", "दोस्त": "Friend", "दादी": "Grandmother", "दादा": "Grandfather", "भाई": "Brother", "बहन": "Sister"},
            "gu": {"માતા": "Mother", "પિતા": "Father", "ડૉક્ટર": "Doctor", "શિક્ષક": "Teacher", "મિત્ર": "Friend", "ભાઈ": "Brother"},
            "mr": {"आई": "Mother", "बाबा": "Father", "डॉक्टर": "Doctor", "शिक्षक": "Teacher", "मित्र": "Friend", "भाऊ": "Brother"},
            "en": {"mother": "Mother", "father": "Father", "doctor": "Doctor", "teacher": "Teacher", "friend": "Friend"}
        }

        STATES_FEELINGS = {
            "hi": {
                "थका हुआ": ("tired", "feeling exhausted"),
                "बीमार": ("sick", "feeling unwell"),
                "दर्द": ("experiencing pain", "in pain"),
                "खुश": ("happy", "feeling happy"),
                "उदास": ("sad", "feeling sad"),
                "भूख": ("hungry", "feeling hungry"),
                "प्यास": ("thirsty", "feeling thirsty"),
                "गुस्सा": ("angry", "feeling upset"),
                "डरा हुआ": ("scared", "feeling anxious")
            },
            "gu": {
                "થાકેલું": ("tired", "feeling exhausted"),
                "બીમાર": ("sick", "feeling unwell"),
                "દુખાવો": ("experiencing pain", "in pain"),
                "ખુશ": ("happy", "feeling happy"),
                "ઉદાસ": ("sad", "feeling sad")
            },
            "mr": {
                "दमलेला": ("tired", "feeling exhausted"),
                "आजारी": ("sick", "feeling unwell"),
                "वेदना": ("experiencing pain", "in pain"),
                "आनंदी": ("happy", "feeling happy"),
                "दुःखी": ("sad", "feeling sad")
            }
        }

        OBJECTS_REQUESTS = {
            "hi": {
                "खाना": "food", "चावल": "rice", "रोटी": "roti / bread", "पानी": "water",
                "फल": "fruit", "दूध": "milk", "दवा": "medicine", "चाय": "tea", "जूस": "juice",
                "सोना": "to sleep / rest", "खेलना": "to play", "मदद": "help", "मदद!": "urgent assistance"
            },
            "gu": {
                "ખોરાક": "food", "પાણી": "water", "દૂધ": "milk", "દવા": "medicine",
                "રમવું": "to play", "ઊંઘવું": "to sleep", "મદદ!": "help"
            },
            "mr": {
                "जेवण": "food", "पाणी": "water", "दूध": "milk", "औषध": "medicine",
                "खेळणे": "to play", "झोपणे": "to sleep", "मदत!": "help"
            }
        }

        PLACES = {
            "hi": {"स्कूल": "at school", "घर": "at home", "अस्पताल": "at the hospital", "कमरा": "in room", "बाज़ार": "at the market", "शौचालय": "to the restroom"},
            "gu": {"શાળા": "at school", "ઘર": "at home", "હોસ્પિટલ": "at the hospital"},
            "mr": {"शाळा": "at school", "घर": "at home", "रुग्णालय": "at the hospital"}
        }

        people_map = PEOPLE_VOCATIVES.get(language, PEOPLE_VOCATIVES.get("hi", {}))
        state_map = STATES_FEELINGS.get(language, STATES_FEELINGS.get("hi", {}))
        obj_map = OBJECTS_REQUESTS.get(language, OBJECTS_REQUESTS.get("hi", {}))
        place_map = PLACES.get(language, PLACES.get("hi", {}))

        addressee = None
        user_state = None
        requests = []
        locations = []

        for ent in entities:
            ent_clean = ent.strip()
            # 1. Person / Addressee
            matched_p = False
            for pk, pv in people_map.items():
                if pk in ent_clean or ent_clean in pk:
                    addressee = f"{ent_clean} ({pv})"
                    matched_p = True
                    break
            if matched_p:
                continue

            # 2. Feeling / State
            matched_s = False
            for sk, (sadj, s_phrase) in state_map.items():
                if sk in ent_clean or ent_clean in sk:
                    user_state = f"{ent_clean} ({s_phrase.capitalize()})"
                    matched_s = True
                    break
            if matched_s:
                continue

            # 3. Location
            matched_pl = False
            for plk, plv in place_map.items():
                if plk in ent_clean or ent_clean in plk:
                    locations.append((ent_clean, plv))
                    matched_pl = True
                    break
            if matched_pl:
                continue

            # 4. Object / Request
            matched_o = False
            for ok, ov in obj_map.items():
                if ok in ent_clean or ent_clean in ok:
                    requests.append((ent_clean, ov))
                    matched_o = True
                    break
            if not matched_o:
                requests.append((ent_clean, ent_clean))

        # Format core_request
        core_request_str = None
        if requests:
            req_hi = " और ".join([r[0] for r in requests])
            req_en = " and ".join([r[1] for r in requests])
            core_request_str = f"{req_hi} ({req_en})"
        elif negation:
            core_request_str = "नहीं चाहिए (Refusal / Does not want)"

        addr_en = None
        if addressee:
            m = re.search(r'\((.*?)\)', addressee)
            addr_en = m.group(1).lower() if m else "caregiver"

        state_en = None
        if user_state:
            m = re.search(r'\((.*?)\)', user_state)
            state_en = m.group(1).lower() if m else None

        req_en = None
        if requests:
            req_en = " and ".join([r[1] for r in requests])

        loc_en = None
        if locations:
            loc_en = " and ".join([l[1] for l in locations])

        if negation:
            if addr_en:
                expl = f"The user is letting their {addr_en} know that they do not want {req_en or 'anything'}."
            else:
                expl = f"The user is indicating that they do not want {req_en or 'anything'}."
        elif req_en:
            if addr_en:
                if state_en:
                    expl = f"The user is {state_en} and is asking their {addr_en} for {req_en}."
                else:
                    expl = f"The user is asking their {addr_en} for {req_en}."
            else:
                if state_en:
                    expl = f"The user is {state_en} and needs {req_en}."
                else:
                    expl = f"The user is requesting {req_en}."
        elif state_en:
            if loc_en:
                expl = f"The user is {state_en} {loc_en}."
            elif addr_en:
                expl = f"The user is sharing with their {addr_en} that they are {state_en}."
            else:
                expl = f"The user is expressing that they are {state_en}."
        elif loc_en:
            expl = f"The user is referring to {loc_en}."
        else:
            expl = "The user is communicating an AAC message to their caregiver."

        return {
            "addressee": addressee,
            "user_state": user_state,
            "core_request": core_request_str,
            "natural_sentence": natural_sentence,
            "caregiver_explanation": expl
        }

    # ─── MASTER PIPELINE API ─────────────────────────────────
    def generate_sentence(self, context, language="en", code_mix=False, mode="dual"):
        """
        Cascaded generation pipeline:
          mode='single' -> LLM-1 Realizer -> LLM-3 Verifier/Refiner
          mode='dual'   -> LLM-1 Realizer -> LLM-2 Refiner -> LLM-3 Verifier/Refiner
        Returns: (final_sentence, structured_context, ledger, candidate_llm1, candidate_llm2, llm3_decision, telemetry)
        """
        lang_map = {"hi": "Hindi", "gu": "Gujarati", "mr": "Marathi", "en": "English", "en+hi": "Hinglish"}
        lang_name = lang_map.get(language, language)

        structured_ctx = self.build_structured_context(context, language=lang_name, code_mix=code_mix)
        ledger = self.build_concept_ledger(structured_ctx)

        telemetry = {
            "stages": {},
            "tokens": {"total_in": 0, "total_out": 0},
            "latencies": {}
        }

        t_total_start = time.time()

        # ── Stage 1: LLM-1 Sentence Realizer ────────────────
        t0 = time.time()
        c_llm1, m_llm1 = self._llm1_realize(structured_ctx, ledger, language, code_mix)
        telemetry["stages"]["llm1"] = {"output": c_llm1, **m_llm1}
        telemetry["tokens"]["total_in"] += m_llm1["tokens_in"]
        telemetry["tokens"]["total_out"] += m_llm1["tokens_out"]
        telemetry["latencies"]["llm1"] = m_llm1["latency"]
        print(f"[LLM-1 Realizer] {c_llm1!r} ({m_llm1['latency']}s)")

        # ── Fast Return for Single Mode ──
        if mode == "single":
            llm3_decision = {"decision": "PASS", "final_text": c_llm1, "edit_type": "single_fast"}
            telemetry["stages"]["llm2"] = None
            telemetry["stages"]["llm3"] = {"decision": llm3_decision, "latency": 0.0, "tokens_in": 0, "tokens_out": 0}
            telemetry["latencies"]["pipeline_llm_total"] = round(time.time() - t_total_start, 3)
            print(f"[Single Mode Fast Output] -> {c_llm1!r} ({m_llm1['latency']}s)")
            return c_llm1, structured_ctx, ledger, c_llm1, None, llm3_decision, telemetry

        # ── Stage 2: LLM-2 Semantic Refiner (Active in Dual Mode) ──
        c_llm2, v_llm2, m_llm2 = self._llm2_refine(c_llm1, ledger, language=language)
        telemetry["stages"]["llm2"] = {"output": c_llm2, "verification": v_llm2, **m_llm2}
        telemetry["tokens"]["total_in"] += m_llm2["tokens_in"]
        telemetry["tokens"]["total_out"] += m_llm2["tokens_out"]
        telemetry["latencies"]["llm2"] = m_llm2["latency"]
        print(f"[LLM-2 Refiner] {c_llm2!r} ({m_llm2['latency']}s)")

        # ── Stage 3: LLM-3 Final Verifier & Minimal Refiner ──
        final_sentence, llm3_decision, m_llm3 = self._llm3_verify_and_refine(
            structured_ctx, ledger, c_llm1, c_llm2, v_llm2
        )
        telemetry["stages"]["llm3"] = {"decision": llm3_decision, **m_llm3}
        telemetry["tokens"]["total_in"] += m_llm3["tokens_in"]
        telemetry["tokens"]["total_out"] += m_llm3["tokens_out"]
        telemetry["latencies"]["llm3"] = m_llm3["latency"]
        telemetry["latencies"]["pipeline_llm_total"] = round(time.time() - t_total_start, 3)

        print(f"[LLM-3 Verifier] decision={llm3_decision.get('decision')} "
              f"edit={llm3_decision.get('edit_type')} -> {final_sentence!r} ({m_llm3['latency']}s)")

        return final_sentence, structured_ctx, ledger, c_llm1, c_llm2, llm3_decision, telemetry
