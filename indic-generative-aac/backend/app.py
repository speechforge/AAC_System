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
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from llm import IndicLLM
from tts import IndicTTSEngine
from hmm import hmm_engine
from semantic import SemanticValidator
from aac_lexicon import BOARD, resolve_label
import concept_predict
from word_order import LANGUAGES, split_context, suggest_word_order
import pipeline
import torch

import personal_service

app = FastAPI()
personal_service.install(app)
import local_accounts
app.include_router(local_accounts.router)
import voice_profiles
app.include_router(voice_profiles.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000",
                   "http://localhost:8001", "http://127.0.0.1:8001"],
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
    intent: str = "REQUEST"        # legacy field (REQUEST / STATEMENT / QUESTION / NEGATION) kept for older clients
    # act and polarity are separate fields (repaired protocol).  `act_source`: 'client' (inferred by the browser),
    # 'user' (explicit choice, never overridden) or omitted for legacy payloads.
    act: str | None = None         # REQUEST | FEELING | FEELING_REQUEST | QUESTION | GREETING | UNKNOWN
    act_source: str | None = None
    polarity: str | None = None    # optional alias: 'negative' == negation true
    concept_ids: list[str | None] = []   # board concept IDs aligned with `entities` (null for typed / personal words)
    actor: str = "USER"
    entities: list[str]
    attributes: list[str] = []
    relations: list[str] = []
    temporal_state: str | None = None
    location: str | None = None
    people: list[str] = []
    actions: list[str] = []
    negation: bool | None = None
    speaker_role: str = "USER"
    language: str = "hi"
    code_mix: bool = False
    generation_mode: str = "dual"  # 'single' or 'dual'
    voice_id: str | None = None   # hi, gu, or mr; must match language
    debug: bool = False
    # evaluation switches (the web client never sends them)
    policy: str = "hybrid"          # hybrid | ungated | template_only
    seed: int | None = None         # seeds the sampling path (English / code-mixed realiser); attempt k uses seed + 1000 * k
    reconcile_legacy: bool = True
    skip_deterministic_retry: bool = False
    include_audio: bool = True      # False: text-only suggestion (Polish); the client speaks explicitly through /api/tts


class ContextRequest(BaseModel):
    context: str = ""
    current_words: list[str] = []
    language: str = "hi"
    intent: str = "REQUEST"


class UnjumbleRequest(ContextRequest):
    language: str = "en"


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


class SpeechRequest(BaseModel):
    text: str
    language: str = "hi"
    voice_id: str | None = None


def synthesize(text, language, voice_id=None, session=None):
    reference=voice_profiles.resolve(session,language) if session else None
    try:
        audio, sr = tts.generate_speech(text, lang=language, speaker_name=voice_id, voice_reference=reference)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"IndicF5 speech unavailable: {exc}")
    buf = io.BytesIO()
    scipy.io.wavfile.write(buf, sr, audio)
    return {"audio_b64": base64.b64encode(buf.getvalue()).decode("ascii"),
            "voice_source":"personal" if reference else "default", "voice_id":reference["voice_id"] if reference else language,
            "audio_kind": tts.last_audio_kind, "cache_hit": getattr(tts,"last_cache_hit",False), "sample_rate": sr, "language": language}


@app.post("/api/tts")
def speech(req: SpeechRequest, session=Depends(personal_service.require_session)):
    return synthesize(req.text, req.language, req.voice_id, session)


@app.get("/api/audio-cache")
def audio_cache_status(session=Depends(personal_service.require_session)):
    import audio_cache
    return audio_cache.stats()

@app.delete("/api/audio-cache")
def clear_audio_cache(session=Depends(personal_service.require_write)):
    import audio_cache
    return audio_cache.clear()

@app.get("/api/voice/list")
def list_voices():
    return {"voices": tts.list_voices(), "engine_ready": tts.ready,
            "engine": "local-f5", "error": tts.init_error,
            "supported_languages": list(tts.LANG_PROMPT_CONFIGS)}



@app.get("/api/health")
def read_root():
    try:
        storage_ready = personal_service.store.redis.ping()
    except personal_service.redis.RedisError:
        storage_ready = False
    return {"status": "ok" if tts.ready and storage_ready else "degraded",
            "message": "Indic Generative AAC Backend Running",
            "tts_engine": "local-f5", "tts_ready": tts.ready, "tts_error": tts.init_error,
            "personal_storage": "redis", "personal_storage_ready": storage_ready}

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
def predict_next(req: ContextRequest, request: Request):
    if req.current_words:
        words = req.current_words
    else:
        words = req.context.strip().split() if req.context.strip() else []

    if req.language not in tts.LANG_PROMPT_CONFIGS:
        raise HTTPException(status_code=400, detail="Supported languages: en, hi, gu, mr")
    lang = req.language
    # 1) Concept grammar: reacts to every selected word, identical in all four languages.
    context_preds = concept_predict.predict(words, lang, top_k=10)
    # 2) Statistical model (infinity-gram / Markov), localised and script-filtered.
    try:
        preds = hmm_engine.predict_next(words, language=lang, top_k=10)
    except Exception:
        preds = []
    stat, seen_stat = [], set()
    native = r"[A-Za-z]" if lang == "en" else (r"[\u0a80-\u0aff]" if lang == "gu" else r"[\u0900-\u097f]")
    foreign = r"[\u0900-\u0aff]" if lang == "en" else r"[A-Za-z]"
    for pred in preds:
        label = pred.get("word", "")
        cid = resolve_label(label)
        if cid:
            label = BOARD[cid][lang]
        if not re.search(native, label) or re.search(foreign, label) or label in seen_stat:
            continue
        seen_stat.add(label)
        stat.append({**pred, "word": label, "source": pred.get("source", "model")})
    # 3) Merge: with a sentence in progress context leads (interleaved with the model so both show);
    #    with an empty sentence the user's own frequent words lead.
    personalized = []
    token = request.cookies.get(personal_service.COOKIE)
    if token:
        try:
            session = personal_service.store.read(token)
            personalized = [{**item, "source": "personal", "emoji": "⭐"}
                            for item in personal_service.store.frequent(session, lang, 7)]
        except (HTTPException, personal_service.redis.RedisError):
            pass
    selected, used = [], set()
    def push(item):
        if item["word"] not in used and item["word"] not in {w.strip() for w in words}:
            used.add(item["word"]); selected.append(item)
    if words:
        for i in range(max(len(context_preds), len(stat))):
            if i < len(context_preds): push(context_preds[i])
            if i < len(stat) and i % 2 == 1: push(stat[i])
        for item in personalized[:2]:      # personal words only fill spare slots once context is known
            push(item)
    else:
        for item in personalized[:4]: push(item)
        for item in context_preds: push(item)
        for item in stat: push(item)
    selected = selected[:10]
    return {"predictions": selected, "suggestions": selected, "personalized": bool(personalized)}

@app.post("/api/unjumble")
def unjumble(req: UnjumbleRequest):
    if req.language not in LANGUAGES:
        raise HTTPException(status_code=400, detail="Supported languages: en, hi, gu, mr")
    words = req.current_words or split_context(req.context)
    return suggest_word_order(words, req.language, llm._call_llm, hmm_engine.unjumble_model)

@app.post("/generate")
def generate(req: AACRequest, session=Depends(personal_service.require_session)):
    t0 = time.time()
    t_sem, t_tts = 0.0, 0.0
    audio_b64 = None
    audio_kind = "none"
    audio_error = None
    if req.language not in tts.LANG_PROMPT_CONFIGS:
        raise HTTPException(status_code=400, detail="Supported languages: en, hi, gu, mr")
    if req.voice_id not in (None, req.language):
        raise HTTPException(status_code=400, detail="Voice must match the selected language.")
    reference=voice_profiles.resolve(session,req.language)
    ctx = pipeline.normalize_request(req.model_dump(), reconcile=req.reconcile_legacy)
    lang = req.language
    live_attempts = []

    def get_attempt(k):
        """Generate the k-th candidate (LLM-1 -> LLM-2 -> LLM-3); seeds the sampling path when requested."""
        if req.seed is not None:
            torch.manual_seed(req.seed + 1000 * k)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(req.seed + 1000 * k)
        try:
            gen, sctx, ledger, c1, c2, decision, telem = llm.generate_sentence(ctx, language=lang, code_mix=req.code_mix, mode=req.generation_mode)
            at = dict(text=gen, llm1=c1, llm2=c2, llm3_text=decision.get("final_text"), llm3_decision=decision.get("decision"),
                      edit_type=decision.get("edit_type"), latency=telem.get("latencies", {}).get("pipeline_llm_total"), ledger=ledger, telemetry=telem)
        except Exception as e:                                # technical failure of a stage: recorded, never hidden
            print(f"[PIPELINE ERROR] attempt {k + 1}: {e}")
            traceback.print_exc()
            at = dict(text=None, error=repr(e), latency=None)
        live_attempts.append(at)
        return at

    res = pipeline.decide(ctx, lang, get_attempt, validator, llm, policy=req.policy, skip_deterministic_retry=req.skip_deterministic_retry)
    sentence = res.get("text") or ""
    outcome = res["outcome"]
    last = live_attempts[-1] if live_attempts else {}
    telemetry_data = last.get("telemetry", {}) if isinstance(last, dict) else {}
    ledger_data = last.get("ledger", {}) if isinstance(last, dict) else {}

    # ── Speech: only a complete sentence is spoken; clarification and literal previews wait for the user ──
    speak_ok = outcome in ("sentence_model", "sentence_template", "sentence_ungated")
    if speak_ok and req.include_audio:
        try:
            t_tts_start = time.time()
            audio_data, sr = tts.generate_speech(sentence, lang=req.language, code_mix=req.code_mix, speaker_name=(req.voice_id or "female"), voice_reference=reference)
            t_tts = time.time() - t_tts_start
            audio_kind = getattr(tts, "last_audio_kind", "none")
            byte_io = io.BytesIO()
            scipy.io.wavfile.write(byte_io, sr, audio_data)
            audio_b64 = base64.b64encode(byte_io.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"[TTS ERROR] {e}")
            traceback.print_exc()
            audio_b64 = None
            audio_kind = "error"
            audio_error = str(e)

    t_total = time.time() - t0
    telemetry_latencies = telemetry_data.get("latencies", {})
    tokens = telemetry_data.get("tokens", {"total_in": 0, "total_out": 0})
    caregiver_ctx = llm.parse_and_repair_context(ctx, sentence, language=req.language) if outcome != "clarification" else None
    n_att = len(res["attempts"])
    sem_score = (res["attempts"][-1].get("score") if res["attempts"] else None)
    if outcome in ("sentence_template",):
        sem_score = 1.0 if res.get("validated") else 0.0

    return {
        "text":            sentence,
        "outcome":         outcome,                      # sentence_model | sentence_template | clarification | literal_preview | failure | sentence_ungated
        "route":           res.get("route"),
        "act":             res.get("act"),
        "negation":        res.get("negation"),
        "act_source":      res.get("act_source"),
        "clarification":   ({"options": res.get("options", []), "literal": res.get("literal")} if outcome == "clarification" else None),
        "literal_preview": (res.get("literal") if outcome == "literal_preview" else None),
        "mode":            req.generation_mode,
        "semantic_score":  sem_score,
        "validated":       bool(res.get("validated")),
        "semantic_valid":  bool(res.get("validated")),
        "fallback_used":   outcome in ("sentence_template", "literal_preview"),
        "gate":            {"version": res.get("gate_version"), "attempts": [
                               {k2: v2 for k2, v2 in at.items() if k2 in ("k", "text", "accepted", "reasons", "latency", "error")} for at in res["attempts"]],
                            "template_status": res.get("template_status"), "template_gate": res.get("template_gate"),
                            "rejected_template_text": res.get("rejected_template_text")},
        "validation_data": {"violations_detected": [x for at in res["attempts"] for x in at.get("reasons", [])] if outcome not in ("sentence_model",) else []},
        "ledger":          ledger_data,
        "candidate_llm1":  last.get("llm1") if isinstance(last, dict) else None,
        "candidate_llm2":  last.get("llm2") if isinstance(last, dict) else None,
        "llm3_decision":   {"decision": last.get("llm3_decision"), "final_text": last.get("llm3_text"), "edit_type": last.get("edit_type"),
                            "fallback_applied": outcome in ("sentence_template", "literal_preview")} if isinstance(last, dict) else {},
        "caregiver_context": caregiver_ctx,
        "audio_b64":       audio_b64,
        "audio_kind":      audio_kind,
        "voice_source":    "personal" if reference else "default",
        "voice_id":        reference["voice_id"] if reference else req.language,
        "audio_error":     audio_error,
        "metrics": {
            "t_llm1":  telemetry_latencies.get("llm1", 0.0),
            "t_llm2":  telemetry_latencies.get("llm2", 0.0),
            "t_llm3":  telemetry_latencies.get("llm3", 0.0),
            "t_sem":   round(t_sem, 2),
            "t_tts":   round(t_tts, 2),
            "t_total": round(t_total, 2),
            "n_attempts": n_att,
            "tokens_in":  tokens.get("total_in", 0),
            "tokens_out": tokens.get("total_out", 0)
        }
    }

# Dedicated account pages and authenticated AAC entry.
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse

@app.middleware("http")
async def account_gate(request, call_next):
    import posixpath
    path = posixpath.normpath('/' + request.url.path.lstrip('/'))
    protected = (path in ('/generate', '/predict_next')
                 or path.startswith('/api/') and not path.startswith(('/api/auth/', '/api/session'))
                 and path != '/api/health')
    if protected:
        try:
            session = personal_service.store.read(request.cookies.get(personal_service.COOKIE))
            if session['service'] not in ('local', 'google'):
                raise HTTPException(401, 'Sign in to open AAC Studio.')
        except HTTPException:
            if path in ('/', '/index.html', '/static/index.html'):
                return RedirectResponse('/welcome', status_code=303, headers={'Cache-Control':'no-store'})
            return JSONResponse({'detail':'Sign in to continue.'}, status_code=401)
        except personal_service.redis.RedisError:
            return JSONResponse({'detail':'Account storage is unavailable. Please retry.'},status_code=503)
    response = await call_next(request)
    if path in ('/', '/index.html', '/static/index.html', '/login', '/signup', '/welcome') or path.startswith('/api/auth/'):
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.get('/aac-sw.js', include_in_schema=False)
def public_service_worker():
    return FileResponse(os.path.join(os.path.dirname(__file__), '../frontend/aac-sw.js'), media_type='application/javascript', headers={'Service-Worker-Allowed':'/','Cache-Control':'no-cache'})

@app.get('/welcome', include_in_schema=False)
def welcome_page():
    return FileResponse(os.path.join(os.path.dirname(__file__), '../frontend/welcome.html'))

@app.get('/login', include_in_schema=False)
def login_page():
    return FileResponse(os.path.join(os.path.dirname(__file__), '../frontend/login.html'))

@app.get('/signup', include_in_schema=False)
def signup_page():
    return FileResponse(os.path.join(os.path.dirname(__file__), '../frontend/signup.html'))

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
