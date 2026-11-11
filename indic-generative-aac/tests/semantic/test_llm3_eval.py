"""
test_llm3_eval.py — Comprehensive Evaluation of LLM-3 as Final Verifier & Minimal Refiner
Tests all Section 17 & Section 18 test cases against the live localhost system.
Avoids VRAM collision by calling the live running FastAPI backend.
"""
import urllib.request
import json
import time
import os

API_URL = "http://localhost:8000/generate"

EVAL_DATASET = [
    {
        "id": "case_1_feel_pizza",
        "name": "Example 1: I FEEL + PIZZA (Minimal Realization)",
        "payload": {
            "intent": "FEELING",
            "actor": "USER",
            "entities": ["pizza"],
            "negation": False,
            "temporal_state": None,
            "language": "en",
            "generation_mode": "dual"
        },
        "banned_words": ["breakfast", "today", "morning", "planning", "tonight", "restaurant"],
        "required_entities": ["pizza"],
        "expected_intent": "FEELING"
    },
    {
        "id": "case_2_want_pizza",
        "name": "Example 2: I WANT + PIZZA",
        "payload": {
            "intent": "WANT",
            "actor": "USER",
            "entities": ["pizza"],
            "negation": False,
            "temporal_state": None,
            "language": "en",
            "generation_mode": "dual"
        },
        "banned_words": ["buy", "store", "restaurant", "planning"],
        "required_entities": ["pizza"],
        "expected_intent": "WANT"
    },
    {
        "id": "case_3_neg_want_pizza",
        "name": "Example 3: DON'T WANT + PIZZA (Negation Preservation)",
        "payload": {
            "intent": "WANT",
            "actor": "USER",
            "entities": ["pizza"],
            "negation": True,
            "temporal_state": None,
            "language": "en",
            "generation_mode": "dual"
        },
        "banned_words": ["breakfast", "lunch", "dinner", "today"],
        "required_entities": ["pizza"],
        "require_negation": True
    },
    {
        "id": "case_4_feel_sad",
        "name": "Example 4: I FEEL + SAD (Emotion Preservation)",
        "payload": {
            "intent": "FEELING",
            "actor": "USER",
            "entities": ["sad"],
            "negation": False,
            "temporal_state": None,
            "language": "en",
            "generation_mode": "dual"
        },
        "banned_words": ["happy", "homework", "today"],
        "required_entities": ["sad"],
        "expected_intent": "FEELING"
    },
    {
        "id": "case_5_feel_happy",
        "name": "Example 5: I FEEL + HAPPY",
        "payload": {
            "intent": "FEELING",
            "actor": "USER",
            "entities": ["happy"],
            "negation": False,
            "temporal_state": None,
            "language": "en",
            "generation_mode": "dual"
        },
        "banned_words": ["weather", "outside", "today"],
        "required_entities": ["happy"],
        "expected_intent": "FEELING"
    },
    {
        "id": "case_6_want_water",
        "name": "Example 6: I WANT + WATER (Omission of cold/now/drink)",
        "payload": {
            "intent": "WANT",
            "actor": "USER",
            "entities": ["water"],
            "negation": False,
            "temporal_state": None,
            "language": "en",
            "generation_mode": "dual"
        },
        "banned_words": ["cold", "now", "bottle", "store"],
        "required_entities": ["water"],
        "expected_intent": "WANT"
    },
    {
        "id": "case_7_feel_pizza_hungry",
        "name": "Example 7: I FEEL + PIZZA (Omission of hungry/eat/tonight)",
        "payload": {
            "intent": "FEELING",
            "actor": "USER",
            "entities": ["pizza"],
            "negation": False,
            "temporal_state": None,
            "language": "en",
            "generation_mode": "dual"
        },
        "banned_words": ["hungry", "tonight", "restaurant", "order"],
        "required_entities": ["pizza"],
        "expected_intent": "FEELING"
    },
    {
        "id": "case_8_neg_school",
        "name": "Example 8: I DON'T WANT + SCHOOL (Negation + School)",
        "payload": {
            "intent": "WANT",
            "actor": "USER",
            "entities": ["school"],
            "negation": True,
            "temporal_state": None,
            "language": "en",
            "generation_mode": "dual"
        },
        "banned_words": ["tomorrow", "morning", "today"],
        "required_entities": ["school"],
        "require_negation": True
    },
    {
        "id": "indic_hindi_want_water",
        "name": "Indic Language: Hindi WANT + water",
        "payload": {
            "intent": "WANT",
            "actor": "USER",
            "entities": ["पानी"],
            "negation": False,
            "temporal_state": None,
            "language": "hi",
            "generation_mode": "dual"
        },
        "banned_words": ["सुबह", "आज"],
        "required_entities": ["पानी"],
        "expected_intent": "WANT"
    },
    {
        "id": "indic_hindi_neg_milk",
        "name": "Indic Language: Hindi NEGATED WANT + milk",
        "payload": {
            "intent": "WANT",
            "actor": "USER",
            "entities": ["दूध"],
            "negation": True,
            "temporal_state": None,
            "language": "hi",
            "generation_mode": "dual"
        },
        "banned_words": ["आज", "सुबह"],
        "required_entities": ["दूध"],
        "require_negation": True
    }
]

def run_evaluation():
    print("=" * 65)
    print("   LLM-3 VERIFIER & MINIMAL REFINER BENCHMARK SUITE")
    print("=" * 65)

    stats = {
        "total": len(EVAL_DATASET),
        "valid_count": 0,
        "intent_preserved": 0,
        "entity_preserved": 0,
        "negation_preserved": 0,
        "unsupported_avoided": 0,
        "tts_audio_generated": 0,
        "fallbacks_used": 0,
        "decisions": {"PASS": 0, "REFINE": 0, "REJECT": 0},
        "edit_types": {},
        "latencies": {
            "t_llm1": [],
            "t_llm2": [],
            "t_llm3": [],
            "t_sem": [],
            "t_tts": [],
            "t_total": []
        }
    }

    results = []

    for test in EVAL_DATASET:
        print(f"\n--- Running: {test['name']} ---")
        clean_payload = {k: v for k, v in test["payload"].items() if v is not None}
        req_data = json.dumps(clean_payload).encode('utf-8')
        req = urllib.request.Request(API_URL, data=req_data, headers={'Content-Type': 'application/json'})

        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"  FAILED HTTP: {e}")
            continue

        text = data.get("text", "")
        text_lower = text.lower()
        validated = data.get("validated", False)
        l3 = data.get("llm3_decision", {})
        dec = l3.get("decision", "REFINE")
        edit = l3.get("edit_type", "unknown")
        audio_ok = bool(data.get("audio_b64"))
        metrics = data.get("metrics", {})

        stats["decisions"][dec] = stats["decisions"].get(dec, 0) + 1
        stats["edit_types"][edit] = stats["edit_types"].get(edit, 0) + 1

        if validated:
            stats["valid_count"] += 1
        if audio_ok:
            stats["tts_audio_generated"] += 1
        if data.get("fallback_used"):
            stats["fallbacks_used"] += 1

        # Check entity preservation
        ent_ok = all(e.lower() in text_lower for e in test["required_entities"])
        if ent_ok: stats["entity_preserved"] += 1

        # Check negation preservation
        if test.get("require_negation"):
            neg_words = ["not", "no", "n't", "don't", "नहीं", "ना", "नको", "નથી"]
            neg_ok = any(nw in text_lower for nw in neg_words)
        else:
            neg_words = ["not", "no", "n't", "don't", "नहीं", "ना", "नको", "નથી"]
            neg_ok = not any(nw in text_lower for nw in neg_words)
        if neg_ok: stats["negation_preserved"] += 1

        # Check unsupported / banned words
        unsupported = [bw for bw in test.get("banned_words", []) if bw.lower() in text_lower]
        if not unsupported: stats["unsupported_avoided"] += 1

        # Check intent
        exp_intent = test.get("expected_intent")
        if exp_intent == "FEELING":
            intent_ok = "feel" in text_lower or "महसूस" in text
        elif exp_intent == "WANT":
            intent_ok = "want" in text_lower or "चाहिए" in text
        else:
            intent_ok = True
        if intent_ok: stats["intent_preserved"] += 1

        for k in ["t_llm1", "t_llm2", "t_llm3", "t_sem", "t_tts", "t_total"]:
            if k in metrics:
                stats["latencies"][k].append(metrics[k])

        print(f"  LLM-1 Draft   : {data.get('candidate_llm1')}")
        print(f"  LLM-2 Refined : {data.get('candidate_llm2')}")
        print(f"  LLM-3 Decision: {dec} (edit: {edit}, removed: {l3.get('violations_removed')})")
        print(f"  Final Sentence: {text}")
        print(f"  Validated     : {validated} (Score: {data.get('semantic_score')}) | TTS Audio: {audio_ok}")
        if unsupported:
            print(f"  ⚠️ Warning: Unsupported words found: {unsupported}")

        results.append({
            "id": test["id"],
            "name": test["name"],
            "llm1": data.get("candidate_llm1"),
            "llm2": data.get("candidate_llm2"),
            "llm3_decision": l3,
            "final_text": text,
            "validated": validated,
            "score": data.get("semantic_score"),
            "audio_ok": audio_ok,
            "entity_ok": ent_ok,
            "negation_ok": neg_ok,
            "unsupported": unsupported,
            "metrics": metrics
        })

    N = stats["total"]
    print("\n" + "=" * 65)
    print("                FINAL BENCHMARK RESULTS")
    print("=" * 65)
    report = {
        "dataset_size": N,
        "semantic_metrics": {
            "overall_validity_rate": f"{(stats['valid_count']/N)*100:.1f}%",
            "entity_preservation_rate": f"{(stats['entity_preserved']/N)*100:.1f}%",
            "negation_preservation_rate": f"{(stats['negation_preserved']/N)*100:.1f}%",
            "intent_preservation_rate": f"{(stats['intent_preserved']/N)*100:.1f}%",
            "unsupported_avoidance_rate": f"{(stats['unsupported_avoided']/N)*100:.1f}%",
            "tts_audio_synthesis_rate": f"{(stats['tts_audio_generated']/N)*100:.1f}%",
            "fallbacks_triggered": stats["fallbacks_used"]
        },
        "llm3_decisions": {
            "breakdown": stats["decisions"],
            "edit_types": stats["edit_types"]
        },
        "latency_profile_seconds": {
            k: round(sum(v)/len(v), 2) if v else 0.0 for k, v in stats["latencies"].items()
        },
        "cases": results
    }

    out_path = os.path.join(os.path.dirname(__file__), "llm3_eval_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps(report["semantic_metrics"], indent=2))
    print(json.dumps(report["llm3_decisions"], indent=2))
    print(json.dumps(report["latency_profile_seconds"], indent=2))
    print(f"\nReport written to: {out_path}")

if __name__ == "__main__":
    run_evaluation()
