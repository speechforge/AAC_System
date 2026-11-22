#!/usr/bin/env python3
"""Client for the guarded server on :8010. Records which paths work without external network."""
import json, sys, time, urllib.request, urllib.error
def post(p, b, to=300):
    r = urllib.request.Request("http://localhost:8010" + p, data=json.dumps(b, ensure_ascii=False).encode(), headers={"Content-Type": "application/json"})
    t = time.perf_counter(); x = json.loads(urllib.request.urlopen(r, timeout=to).read()); return x, round(time.perf_counter() - t, 2)
out = {}
for _ in range(60):
    try: urllib.request.urlopen("http://localhost:8010/api/health", timeout=2); break
    except Exception: time.sleep(3)
out["health"] = json.loads(urllib.request.urlopen("http://localhost:8010/api/health", timeout=10).read())
x, dt = post("/predict_next", {"current_words": ["i", "want"], "language": "en"}); out["predict_next_en"] = dict(top3=[p["word"] for p in x["predictions"][:3]], s=dt)
x, dt = post("/api/transliterate", {"text": "paani", "language": "hi"}); out["translit_mapped_word"] = dict(r=x, s=dt)
x, dt = post("/api/transliterate", {"text": "kursi", "language": "hi"}); out["translit_unmapped_word"] = dict(r=x, s=dt)
for lang, ents in (("en", ["Water"]), ("hi", ["पानी"])):
    x, dt = post("/generate", dict(intent="REQUEST", negation=False, entities=ents, language=lang, code_mix=False, generation_mode="dual"))
    out[f"generate_{lang}"] = dict(text=x["text"], fallback_used=x["fallback_used"], audio_b64_len=len(x["audio_b64"] or ""), wall_s=dt)
print(json.dumps(out, ensure_ascii=False, indent=1))
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "results/offline_check.json", "w"), ensure_ascii=False, indent=1)
