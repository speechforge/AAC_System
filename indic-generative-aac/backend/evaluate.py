import time
import os
import psutil
import torch
import json
import numpy as np
from transformers import pipeline
import evaluate as hf_evaluate

# Load models safely
try:
    import llm
    import tts
    import semantic
    from llm import IndicLLM
    from tts import IndicTTSEngine
    from semantic import SemanticValidator

    print("Initializing components for Evaluation...")
    language_model = IndicLLM()
    tts_engine = IndicTTSEngine()
    validator = SemanticValidator(language_model)
    asr_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-tiny", device=0 if torch.cuda.is_available() else -1)
    
    print("Components loaded.")
except Exception as e:
    print(f"Error loading components: {e}")
    exit(1)

import soundfile as sf

def compute_metrics(test_cases, run_name):
    results = []
    
    # Track RAM/VRAM
    process = psutil.Process(os.getpid())
    ram_mb = process.memory_info().rss / (1024 * 1024)
    vram_mb = torch.cuda.memory_allocated() / (1024 * 1024) if torch.cuda.is_available() else 0

    for i, tc in enumerate(test_cases):
        context = tc['context']
        ref_text = tc['reference']
        lang = tc['language']
        code_mix = tc.get('code_mix', False)
        
        # Measure LLM + Semantics
        t0 = time.time()
        gen, structured_ctx, ledger, c_llm1, c_llm2, decision, telem = language_model.generate_sentence(context, lang, code_mix)
        sentence = gen
        valid, val_data = validator.validate(context, ledger, sentence, lang)
        
        # Fail/Regeneration loop
        if not valid:
            for _ in range(2):
                gen, structured_ctx, ledger, c_llm1, c_llm2, decision, telem = language_model.generate_sentence(context, lang, code_mix)
                sentence = gen
                valid, val_data = validator.validate(context, ledger, sentence, lang)
                if valid: break
                
        t_llm = time.time() - t0
        
        # Measure TTS
        t1 = time.time()
        try:
            audio_data, sr = tts_engine.generate_speech(sentence, lang, code_mix, speaker_name="female")
        except:
            audio_data, sr = np.zeros(22050), 22050
        t_tts = time.time() - t1
        
        duration = len(audio_data) / sr if sr > 0 else 0
        rtf = t_tts / duration if duration > 0 else 0
        
        # Save temp audio for ASR
        tmp_wav = f"tmp_eval_{i}.wav"
        sf.write(tmp_wav, audio_data, sr)
        
        # Run ASR
        asr_out = asr_pipeline(tmp_wav)["text"].strip()
        os.remove(tmp_wav)
        
        # Compute WER
        # (For simplicity, we compute approximate WER manually if evaluate library fails, but we'll try evaluate)
        # Using a simple Levenshtein word distance
        def edit_distance(r, h):
            r = r.lower().split()
            h = h.lower().split()
            d = np.zeros((len(r)+1)*(len(h)+1), dtype=np.uint8).reshape((len(r)+1, len(h)+1))
            for i in range(len(r)+1): d[i][0] = i
            for j in range(len(h)+1): d[0][j] = j
            for i in range(1, len(r)+1):
                for j in range(1, len(h)+1):
                    if r[i-1] == h[j-1]:
                        d[i][j] = d[i-1][j-1]
                    else:
                        d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+1)
            return d[len(r)][len(h)] / max(len(r), 1)

        wer = edit_distance(sentence, asr_out)
        
        results.append({
            "id": i,
            "context": context,
            "generated": sentence,
            "asr_transcription": asr_out,
            "semantic_pass": valid,
            "latency_llm_s": t_llm,
            "latency_tts_s": t_tts,
            "duration_s": duration,
            "rtf": rtf,
            "wer": wer
        })
        print(f"[{run_name}] Finished {i+1}/{len(test_cases)}: WER={wer:.2f}, Valid={valid}")

    # Summary
    sem_acc = sum(1 for r in results if r['semantic_pass']) / len(results)
    avg_wer = sum(r['wer'] for r in results) / len(results)
    avg_llm = sum(r['latency_llm_s'] for r in results) / len(results)
    avg_tts = sum(r['latency_tts_s'] for r in results) / len(results)
    avg_rtf = sum(r['rtf'] for r in results) / len(results)
    
    summary = {
        "system": run_name,
        "samples": len(results),
        "semantic_fidelity": sem_acc,
        "wer": avg_wer,
        "avg_llm_latency": avg_llm,
        "avg_tts_latency": avg_tts,
        "avg_rtf": avg_rtf,
        "ram_mb": ram_mb,
        "vram_mb": vram_mb
    }
    
    with open(f"../experiments/{run_name}_results.json", "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    return summary

if __name__ == "__main__":
    os.makedirs("../experiments", exist_ok=True)
    
    test_cases = [
        {
            "context": {"intent": "REQUEST", "entities": ["water"], "negation": False, "temporal_state": "PRESENT"},
            "reference": "I want water.",
            "language": "en"
        },
        {
            "context": {"intent": "STATEMENT", "entities": ["milk"], "negation": True, "temporal_state": "PRESENT"},
            "reference": "I do not want milk.",
            "language": "en"
        },
        {
            "context": {"intent": "REQUEST", "entities": ["school", "mother"], "negation": False, "temporal_state": "PRESENT"},
            "reference": "I want to go to school with mother.",
            "language": "en"
        },
        {
            "context": {"intent": "STATEMENT", "entities": ["doctor"], "negation": True, "temporal_state": "PRESENT"},
            "reference": "I do not want to go to the doctor.",
            "language": "en"
        },
        {
            "context": {"intent": "REQUEST", "entities": ["school", "mother"], "negation": False, "temporal_state": "PRESENT"},
            "reference": "मुझे school जाना है mother के साथ।",
            "language": "hi",
            "code_mix": True
        }
    ]
    
    print("Running Baseline Eval...")
    summary = compute_metrics(test_cases, "Optimized_System")
    print("\nEVALUATION COMPLETE:")
    print(json.dumps(summary, indent=2))
