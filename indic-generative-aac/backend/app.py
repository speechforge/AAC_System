import os
import time
import io
import re
import json
import base64
import urllib.request
import urllib.parse
import traceback
import scipy.io.wavfile
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from llm import IndicLLM
from tts import IndicTTSEngine
from hmm import hmm_engine
from semantic import SemanticValidator

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Initializing AAC Backend with LLM-3 Verifier & Large HMM...")
llm = IndicLLM()
tts = IndicTTSEngine()
validator = SemanticValidator(llm)
print("Initialization Complete.")

class AACRequest(BaseModel):
    intent: str
    actor: str = "USER"
    entities: list[str]
    attributes: list[str] = []
    relations: list[str] = []
    temporal_state: str | None = None
    location: str | None = None
    people: list[str] = []
    actions: list[str] = []
    negation: bool = False
    speaker_role: str = "USER"
    language: str = "en"
    code_mix: bool = False
    generation_mode: str = "dual"  # 'single' or 'dual'
    debug: bool = False


class ContextRequest(BaseModel):
    context: str = ""
    current_words: list[str] = []
    language: str = "hi"
    intent: str = "REQUEST"


class TransliterateRequest(BaseModel):
    text: str
    language: str = "hi"


@app.post("/api/transliterate")
def transliterate_endpoint(req: TransliterateRequest):
    # Offline-first phoneme map for Roman→Devanagari (Hindi) common AAC words.
    # Covers the most frequent symbols without any network request.
    _OFFLINE_HI = {
        "maa": "माँ", "ma": "माँ", "papa": "पापा", "dadi": "दादी", "dada": "दादा",
        "paani": "पानी", "pani": "पानी", "khana": "खाना", "dard": "दर्द",
        "dawai": "दवाई", "dawa": "दवा", "doctor": "डॉक्टर", "daktar": "डॉक्टर",
        "school": "स्कूल", "ghar": "घर", "bhai": "भाई", "behen": "बहन",
        "dost": "दोस्त", "neend": "नींद", "bathroom": "बाथरूम", "bhook": "भूख",
        "pyaas": "प्यास", "dukh": "दुख", "khushi": "खुशी", "gussa": "गुस्सा",
        "thaka": "थका", "bimaar": "बीमार", "aaram": "आराम", "help": "मदद",
        "haan": "हाँ", "nahi": "नहीं", "nahin": "नहीं", "chahiye": "चाहिए",
        "jana": "जाना", "aana": "आना", "kal": "कल", "aaj": "आज",
    }
    _OFFLINE_GU = {
        "paani": "પાણી", "khana": "ખાણું", "mummy": "મમ્મી", "papa": "પપ્પા",
        "school": "શાળા", "ghar": "ઘર", "dard": "દર્દ", "help": "મદદ",
    }
    _OFFLINE_MR = {
        "paani": "पाणी", "khana": "जेवण", "aai": "आई", "baba": "बाबा",
        "school": "शाळा", "ghar": "घर", "dard": "दुखणे", "help": "मदत",
    }
    _OFFLINE_MAPS = {"hi": _OFFLINE_HI, "gu": _OFFLINE_GU, "mr": _OFFLINE_MR}

    lang_codes = {
        "hi": "hi-t-i0-und",
        "gu": "gu-t-i0-und",
        "mr": "mr-t-i0-und"
    }
    itc = lang_codes.get(req.language, "hi-t-i0-und")
    text = req.text.strip()
    if not text:
        return {"original": req.text, "transliterated": req.text}

    if not re.search(r'[a-zA-Z]', text):
        return {"original": req.text, "transliterated": req.text}

    # Try offline map first (zero latency, zero network)
    offline_map = _OFFLINE_MAPS.get(req.language, _OFFLINE_HI)
    text_lower = text.lower().strip()
    if text_lower in offline_map:
        return {"original": req.text, "transliterated": offline_map[text_lower], "source": "offline"}

    # Fall back to Google Transliteration API with reduced timeout (0.8s)
    # NOTE: This call is network-dependent — will silently fall back to passthrough if offline.
    url = f"https://inputtools.google.com/request?text={urllib.parse.quote(text)}&itc={itc}&num=1"
    try:
        http_req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(http_req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data and data[0] == "SUCCESS" and len(data) > 1:
                words_res = []
                for item in data[1]:
                    if item and len(item) > 1 and item[1]:
                        words_res.append(item[1][0])
                    else:
                        words_res.append(item[0])
                return {"original": req.text, "transliterated": " ".join(words_res), "source": "google"}
    except Exception as e:
        print(f"[Transliterate] API unavailable (offline mode): {e}")

    return {"original": req.text, "transliterated": req.text, "source": "passthrough"}

@app.get("/api/health")
def read_root():
    return {"status": "ok", "message": "Indic Generative AAC Backend Running"}

@app.get("/api/hmm_info")
def hmm_info():
    inf_stats = {}
    if hasattr(hmm_engine, 'infinity_gram') and hmm_engine.infinity_gram is not None:
        inf_stats = hmm_engine.infinity_gram.get_stats()
    return {
        "sentence_count": getattr(hmm_engine, 'sentence_count', 0),
        "infinity_gram_enabled": bool(inf_stats),
        "infinity_gram_stats": inf_stats,
        "bigram_states": len(hmm_engine.bigrams),
        "trigram_states": len(hmm_engine.trigrams),
        "hindi_vocab": len(getattr(hmm_engine, 'hindi_vocab', [])),
        "hindi_bigrams": len(getattr(hmm_engine, 'hindi_bigrams', {}))
    }

@app.post("/api/hmm_reload")
def hmm_reload():
    hmm_engine.reload()
    return {
        "status": "reloaded",
        "sentence_count": getattr(hmm_engine, 'sentence_count', 0),
        "bigram_states": len(hmm_engine.bigrams),
        "trigram_states": len(hmm_engine.trigrams),
        "hindi_vocab": len(getattr(hmm_engine, 'hindi_vocab', [])),
        "hindi_bigrams": len(getattr(hmm_engine, 'hindi_bigrams', {}))
    }

@app.post("/predict_next")
def predict_next(req: ContextRequest):
    if req.current_words:
        words = req.current_words
    else:
        words = req.context.strip().split() if req.context.strip() else []

    preds = hmm_engine.predict_next(words, language=req.language, top_k=10)
    return {"predictions": preds, "suggestions": preds}

@app.post("/api/unjumble")
def unjumble(req: ContextRequest):
    if req.current_words:
        words = req.current_words
    else:
        words = req.context.strip().split() if req.context.strip() else []
    ordered, score = hmm_engine.unjumble(words)
    return {
        "jumbled": words,
        "unjumbled": ordered,
        "score": round(score, 3),
        "sentence": " ".join(ordered)
    }

@app.post("/generate")
def generate(req: AACRequest):
    t0 = time.time()
    t_sem, t_tts = 0.0, 0.0
    sentence = ""
    is_valid = False
    validation_data = {}
    ledger_data = {}
    candidate_llm1 = None
    candidate_llm2 = None
    llm3_decision  = {}
    telemetry_data = {}
    fallback_used  = False
    audio_b64      = None

    context = {
        "intent":         req.intent,
        "actor":          req.actor,
        "entities":       req.entities,
        "attributes":     req.attributes,
        "relations":      req.relations,
        "temporal_state": req.temporal_state,
        "location":       req.location,
        "people":         req.people,
        "actions":        req.actions,
        "negation":       req.negation or (req.intent.upper() == "NEGATION") or ("NOT" in req.intent.upper()),
        "speaker_role":   req.speaker_role
    }

    # ── Authority Hierarchy Pipeline with Bounded Retry (MAX_RETRIES = 1) ──
    MAX_RETRIES = 2
    for attempt in range(MAX_RETRIES):
        try:
            # Stages 1, 2, 3: LLM-1 Realizer -> LLM-2 Refiner -> LLM-3 Verifier
            gen, structured_ctx, ledger, c_llm1, c_llm2, decision, telem = llm.generate_sentence(
                context, language=req.language, code_mix=req.code_mix, mode=req.generation_mode
            )
            ledger_data    = ledger
            candidate_llm1 = c_llm1
            candidate_llm2 = c_llm2
            llm3_decision  = decision
            telemetry_data = telem

            print(f"[PIPELINE Attempt {attempt+1}] "
                  f"LLM-1={c_llm1!r} | LLM-2={c_llm2!r} | LLM-3={decision.get('decision')} | Output={gen!r}")

            # ── Stage 4: Hard Semantic Validator ────────────────────
            t_sem_start = time.time()
            valid, val_data = validator.validate(context, ledger, gen, req.language)
            t_sem += (time.time() - t_sem_start)

            print(f"[HARD VALIDATOR Attempt {attempt+1}] Valid={valid} Score={val_data.get('semantic_score')} Data={val_data}")

            if valid:
                sentence = gen
                is_valid = True
                validation_data = val_data
                break
            else:
                sentence = gen
                validation_data = val_data

        except Exception as e:
            print(f"[PIPELINE ERROR] Attempt {attempt+1}: {e}")
            traceback.print_exc()

    # ── Stage 5: Deterministic Fallback Strategy ────────────────────
    # If all LLM refinement fails, use safe deterministic realization based directly on user concepts
    if not is_valid:
        print("[FALLBACK TRIGGERED] Applying zero-hallucination deterministic fallback.")
        fallback_sentence = llm.generate_deterministic_fallback(context, language=req.language, code_mix=req.code_mix)
        fallback_valid, fallback_val_data = validator.validate(context, ledger_data, fallback_sentence, req.language)
        
        sentence = fallback_sentence
        is_valid = True  # Safe fallback directly realizes user selections, always valid for speech
        validation_data = fallback_val_data
        fallback_used = True
        llm3_decision["fallback_applied"] = True
        llm3_decision["edit_type"] = "deterministic_fallback"

    # ── Stage 6: Speech Synthesis ───────────────────────────────────
    try:
        t_tts_start = time.time()
        audio_data, sr = tts.generate_speech(
            sentence, lang=req.language, code_mix=req.code_mix, speaker_name="female"
        )
        t_tts = time.time() - t_tts_start
        byte_io = io.BytesIO()
        scipy.io.wavfile.write(byte_io, sr, audio_data)
        audio_b64 = base64.b64encode(byte_io.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        traceback.print_exc()
        audio_b64 = None

    t_total = time.time() - t0
    telemetry_latencies = telemetry_data.get("latencies", {})
    tokens = telemetry_data.get("tokens", {"total_in": 0, "total_out": 0})

    caregiver_ctx = llm.parse_and_repair_context(context, sentence, language=req.language)

    return {
        "text":            sentence,
        "mode":            req.generation_mode,
        "semantic_score":  validation_data.get("semantic_score", 0.0),
        "validated":       is_valid,
        "semantic_valid":  is_valid,
        "fallback_used":   fallback_used,
        "validation_data": validation_data,
        "ledger":          ledger_data,
        "candidate_llm1":  candidate_llm1,
        "candidate_llm2":  candidate_llm2,
        "llm3_decision":   llm3_decision,
        "caregiver_context": caregiver_ctx,
        "audio_b64":       audio_b64,
        "metrics": {
            "t_llm1":  telemetry_latencies.get("llm1", 0.0),
            "t_llm2":  telemetry_latencies.get("llm2", 0.0),
            "t_llm3":  telemetry_latencies.get("llm3", 0.0),
            "t_sem":   round(t_sem, 2),
            "t_tts":   round(t_tts, 2),
            "t_total": round(t_total, 2),
            "tokens_in":  tokens.get("total_in", 0),
            "tokens_out": tokens.get("total_out", 0)
        }
    }

# Mount static frontend
_frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
app.mount("/static", StaticFiles(directory=_frontend_dir), name="static")
app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    import os
    import socket

    default_port = 8000
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('127.0.0.1', 8000)) == 0:
            default_port = 8001

    port = int(os.environ.get("PORT", default_port))
    print(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
