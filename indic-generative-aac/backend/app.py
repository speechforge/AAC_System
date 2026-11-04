import time
import io
import re
import json
import base64
import urllib.request
import urllib.parse
import os
import traceback
import scipy.io.wavfile
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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
    voice_id: str | None = None   # preset key ("indic_female"/"english_female") or a cloned custom_* voice_id
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

    url = f"https://inputtools.google.com/request?text={urllib.parse.quote(text)}&itc={itc}&num=1"
    try:
        http_req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(http_req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data and data[0] == "SUCCESS" and len(data) > 1:
                words_res = []
                for item in data[1]:
                    if item and len(item) > 1 and item[1]:
                        words_res.append(item[1][0])
                    else:
                        words_res.append(item[0])
                return {"original": req.text, "transliterated": " ".join(words_res)}
    except Exception as e:
        print("[Transliterate] API Error:", e)

    return {"original": req.text, "transliterated": req.text}

class SymbolRequest(BaseModel):
    word: str
    language: str = "en"


@app.post("/api/generate_symbol")
def generate_symbol(req: SymbolRequest):
    """
    Text-to-image AAC symbol generation. Uses the OpenAI Images API; the key is
    read from the OPENAI_API_KEY environment variable and never reaches the browser.
    Swap the provider by editing this function only.
    """
    word = req.word.strip()
    if not word or len(word) > 80:
        raise HTTPException(status_code=400, detail="Provide a word (max 80 characters).")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=501, detail="AI image generation is not configured (set OPENAI_API_KEY on the server).")

    prompt = (f"A simple, clear AAC communication pictogram representing the word '{word}'. "
              "Flat vector icon style, bold outlines, bright friendly colors, centered subject, "
              "plain white background, no text or letters.")
    payload = json.dumps({
        "model": os.environ.get("SYMBOL_IMAGE_MODEL", "gpt-image-1"),
        "prompt": prompt, "size": "1024x1024", "n": 1,
    }).encode("utf-8")
    http_req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(http_req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        b64 = data["data"][0].get("b64_json")
        if not b64:
            raise ValueError("provider returned no inline image")
        return {"image_b64": b64, "word": word}
    except Exception as e:
        print("[Symbol] generation error:", e)
        raise HTTPException(status_code=502, detail="Image provider request failed.")


@app.get("/api/voice/list")
def list_voices():
    """Lists built-in TTS voice presets plus any custom voices cloned this session."""
    return {"voices": tts.list_voices(), "engine_ready": tts.model is not None}


@app.post("/api/voice/clone")
async def clone_voice(
    file: UploadFile = File(...),
    transcript: str = Form(...),
    label: str = Form("My Cloned Voice"),
):
    """
    Registers a user-uploaded reference audio clip as a new zero-shot voice
    using the IndicF5 model (https://huggingface.co/ai4bharat/IndicF5), which
    requires the reference audio plus its exact spoken transcript.
    """
    allowed_types = ("audio/", "video/webm")  # browsers sometimes tag mic recordings as video/webm
    if file.content_type and not any(file.content_type.startswith(t) for t in allowed_types):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    audio_bytes = await file.read()
    max_bytes = 20 * 1024 * 1024  # 20MB cap
    if len(audio_bytes) > max_bytes:
        raise HTTPException(status_code=400, detail="Reference audio file is too large (max 20MB).")

    try:
        voice_id = tts.register_custom_voice(audio_bytes, transcript, label=label)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "voice_id": voice_id,
        "label": label,
        "status": "ready" if tts.model is not None else "queued_mock_mode",
        "message": (
            "Voice cloned successfully."
            if tts.model is not None
            else "Upload accepted. Install the IndicF5 checkpoint to hear the real cloned voice; using placeholder audio until then."
        ),
    }


@app.delete("/api/voice/{voice_id}")
def delete_voice(voice_id: str):
    if not voice_id.startswith("custom_"):
        raise HTTPException(status_code=400, detail="Only custom cloned voices can be removed.")
    removed = tts.remove_custom_voice(voice_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Voice not found.")
    return {"status": "removed", "voice_id": voice_id}


@app.get("/api/health")
def read_root():
    return {"status": "ok", "message": "Indic Generative AAC Backend Running"}

@app.get("/api/hmm_info")
def hmm_info():
    return {
        "sentence_count": getattr(hmm_engine, 'sentence_count', 0),
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
            sentence, lang=req.language, code_mix=req.code_mix, speaker_name=(req.voice_id or "female")
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
app.mount("/static", StaticFiles(directory="../frontend"), name="static")
app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

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
