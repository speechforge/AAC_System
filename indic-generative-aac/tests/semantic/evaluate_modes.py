import sys
import os
import time
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
from llm import IndicLLM
from semantic import SemanticValidator

llm = IndicLLM()
validator = SemanticValidator(llm)

dataset = [
    {
        "name": "Basic Request",
        "context": {"intent": "WANT", "actor": "USER", "entities": ["water"], "negation": False, "temporal_state": "PRESENT"},
        "language": "en"
    },
    {
        "name": "Basic Feeling",
        "context": {"intent": "FEELING", "actor": "USER", "entities": ["happy"], "negation": False, "temporal_state": "PRESENT"},
        "language": "en"
    },
    {
        "name": "Hallucination Trap",
        "context": {"intent": "FEELING", "actor": "USER", "entities": ["pizza"], "negation": False, "temporal_state": "PRESENT"},
        "language": "en"
    },
    {
        "name": "Negation",
        "context": {"intent": "WANT", "actor": "USER", "entities": ["milk"], "negation": True, "temporal_state": "PRESENT"},
        "language": "en"
    },
    {
        "name": "Multiple Entities",
        "context": {"intent": "WANT", "actor": "USER", "entities": ["pizza", "mother"], "negation": False, "temporal_state": "PRESENT"},
        "language": "en"
    },
    {
        "name": "Relations",
        "context": {"intent": "WANT", "actor": "USER", "entities": ["go", "school", "mother"], "negation": False, "temporal_state": "PRESENT"},
        "language": "en"
    },
    {
        "name": "Temporal Explicit",
        "context": {"intent": "WANT", "actor": "USER", "entities": ["go", "school", "tomorrow"], "temporal_state": "FUTURE", "negation": False},
        "language": "en"
    },
    {
        "name": "Question",
        "context": {"intent": "QUESTION", "actor": "USER", "entities": ["water"], "negation": False, "temporal_state": "PRESENT"},
        "language": "en"
    },
    {
        "name": "Hindi Code-Mixed",
        "context": {"intent": "WANT", "actor": "USER", "entities": ["school", "go"], "negation": False, "temporal_state": "PRESENT"},
        "language": "hi",
        "code_mix": True
    }
]

def run_eval(mode):
    print(f"\n--- Running Evaluation: {mode.upper()} ---")
    results = []
    
    total_latency_llm = 0
    total_latency_sem = 0
    total_violations = 0
    
    for case in dataset:
        ctx = case["context"]
        lang = case["language"]
        cm = case.get("code_mix", False)
        
        t0 = time.time()
        gen, ledger, candidate = llm.generate_sentence(ctx, lang, cm, mode=mode)
        t_llm = time.time() - t0
        
        t1 = time.time()
        valid, val_data = validator.validate(ctx, ledger, gen, lang)
        t_sem = time.time() - t1
        
        violation = val_data.get("unsupported_additions", True) or not valid
        if violation:
            total_violations += 1
            
        total_latency_llm += t_llm
        total_latency_sem += t_sem
        
        res = {
            "name": case["name"],
            "generated": gen,
            "candidate": candidate,
            "valid": valid,
            "score": val_data.get("semantic_score", 0),
            "violation": violation,
            "t_llm": round(t_llm, 2),
            "t_sem": round(t_sem, 2)
        }
        results.append(res)
        print(f"[{case['name']}] Gen: {gen} | Valid: {valid} | Score: {res['score']}")

    avg_llm = total_latency_llm / len(dataset)
    avg_sem = total_latency_sem / len(dataset)
    cvr = total_violations / len(dataset)
    
    print(f"\n[SUMMARY {mode.upper()}]")
    print(f"Avg LLM Latency: {avg_llm:.2f}s")
    print(f"Avg Validator Latency: {avg_sem:.2f}s")
    print(f"Constraint Violation Rate (CVR): {cvr*100:.1f}%")
    
    return {
        "mode": mode,
        "avg_llm": round(avg_llm, 2),
        "avg_sem": round(avg_sem, 2),
        "cvr": round(cvr, 2),
        "results": results
    }

print("Loading complete. Starting Evaluation...")
res_single = run_eval("single")
res_dual = run_eval("dual")

final_report = {
    "single": res_single,
    "dual": res_dual
}

with open('/home/linux/Documents/2026/aac_system_demo_track/indic-generative-aac/tests/semantic/eval_report.json', 'w') as f:
    json.dump(final_report, f, indent=2)

print("\nEvaluation completed and saved to eval_report.json")
