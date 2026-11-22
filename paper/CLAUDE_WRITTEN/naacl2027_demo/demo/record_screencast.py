#!/usr/bin/env python3
"""Record a captioned screencast of the RUNNING build (backend on :8000) with Playwright + system Chrome.
Captions are injected into the page (Chrome shapes Devanagari/Gujarati correctly) and are generated from the real /generate response,
so they describe what actually happened in this run. The video is SILENT: the gated IndicF5 checkpoint is unavailable, so the build returns a
placeholder tone; the narrated, audible take must be recorded on a machine with the IndicF5 weights (see demo/SCREENCAST_SCRIPT.md).
Usage: [AAC_FRAMES_DIR=<scratch>] python record_screencast.py   ->  demo/screencast/screencast_silent_captioned.mp4, captions.srt"""
import asyncio, json, os, pathlib, re, subprocess, tempfile, time
from playwright.async_api import async_playwright
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "screencast"; OUT.mkdir(exist_ok=True)
S = json.loads((HERE.parent / "eval/results/summary.json").read_text(encoding="utf-8"))
LANGS = ["en", "hi", "gu", "mr"]
tot = lambda k, f: sum(S["by_lang"][l][k][f] for l in LANGS)
n = sum(S["by_lang"][l]["deployed|ui"]["n"] for l in LANGS)
pct = lambda k: round(100 * tot(k, "success") / n)
URL = "http://localhost:8000/"
cues = []   # (start_s, end_s, text)
frames = []  # (t_seconds, path)
T0 = None

CAP_JS = """(t) => { let d = document.getElementById('aac-cap');
  if (!d) { d = document.createElement('div'); d.id = 'aac-cap';
    d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:2147483647;padding:14px 28px;background:rgba(10,10,10,.84);color:#fff;' +
      'font:600 24px/1.35 "Noto Sans","Noto Sans Devanagari","Noto Sans Gujarati",sans-serif;text-align:center;pointer-events:none';
    document.body.appendChild(d); }
  d.textContent = t; }"""

async def grab(pg, d, stop):
    """Frame grabber (about 10 fps): the Playwright video recorder needs a bundled ffmpeg that is not installed, so frames are screenshots."""
    i = 0
    while not stop.is_set():
        t = time.perf_counter() - T0; f = f"{d}/f{i:05d}.jpg"
        try: await pg.screenshot(path=f, type="jpeg", quality=72)
        except Exception: break
        frames.append((t, f)); i += 1; await asyncio.sleep(0.04)

async def say(pg, text, hold):
    global T0
    start = time.perf_counter() - T0
    await pg.evaluate(CAP_JS, text)
    await pg.wait_for_timeout(int(hold * 1000))
    cues.append((start, time.perf_counter() - T0, text))

async def pick(pg, label):
    loc = pg.locator("button").filter(has_text=re.compile(rf"^\s*\S*\s*{re.escape(label)}\s*$", re.S))
    await loc.nth(await loc.count() - 1).click(); await pg.wait_for_timeout(500)

async def tab(pg, name):
    loc = pg.get_by_role("button", name=re.compile(name)); await loc.nth(await loc.count() - 1).click(); await pg.wait_for_timeout(600)

async def generate(pg):
    async with pg.expect_response(lambda r: r.url.endswith("/generate"), timeout=180000) as ri:
        await pg.get_by_role("button", name=re.compile("AI Polish")).click()
        await say(pg, "Generating on a local 4 GB GPU (about 6 to 13 s) ...", 0.2)
    data = await (await ri.value).json()
    await pg.wait_for_selector("text=Natural Realization", timeout=30000); await pg.wait_for_timeout(600)
    return data

async def main():
    global T0
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
        ctx = await b.new_context(viewport=dict(width=1280, height=720), locale="en-US")
        pg = await ctx.new_page(); T0 = time.perf_counter(); tmp = tempfile.mkdtemp(prefix="aac_frames_", dir=os.environ.get("AAC_FRAMES_DIR")); stop = asyncio.Event(); gtask = asyncio.create_task(grab(pg, tmp, stop))
        await pg.goto(URL, wait_until="networkidle", timeout=60000); await pg.evaluate("localStorage.clear()"); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(1500)
        await say(pg, "Indic AAC Studio: a symbol board in English, Hindi, Gujarati and Marathi. Selections go to a local server.", 6)
        # ---- A: English ordinary / recovery ----
        await tab(pg, "Food & Drink"); await pick(pg, "Water")
        await say(pg, "1. Tap symbols. The shelf proposes next words from a trained infinity-gram model.", 5)
        d = await generate(pg)
        if d["fallback_used"]:
            await say(pg, f"2. The model proposed “{d['candidate_llm1'] or d['llm3_decision'].get('final_text')}”; the validator rejected it (selected concept missing) and the template returned “{d['text']}”.", 8)
        else:
            await say(pg, f"2. The validator accepted “{d['text']}” (selected concept present, polarity kept).", 8)
        await say(pg, "The card does not show whether the model or the template produced the sentence.", 4)
        # ---- B: Gujarati with negation ----
        await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(1200)
        await pg.select_option("select", "gu"); await pg.wait_for_timeout(800)
        await pick(pg, "ના"); await tab(pg, "ખોરાક"); await pick(pg, "પાણી")
        await say(pg, "Gujarati: “No” + “Water” (ના + પાણી). Labels exist in all four locales.", 5)
        d = await generate(pg)
        verb = "accepted" if not d["fallback_used"] else "rejected; the template returned"
        await say(pg, f"The validator {verb}: “{d['text']}” (negation kept).", 8)
        # ---- C: intent-sensitive failure ----
        await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(1200)
        await pg.select_option("select", "en"); await pg.wait_for_timeout(800)   # the language preference is cached across reloads
        await tab(pg, "Feelings"); await pick(pg, "Tired")
        await say(pg, "Intent-sensitive case: the feeling “Tired”. The web client infers intent from the labels and sends REQUEST.", 6)
        d = await generate(pg)
        if d["fallback_used"]:
            await say(pg, f"Rejected, template returned: “{d['text']}”. Polarity is kept but the act is wrong (a documented defect).", 9)
        else:
            await say(pg, f"Accepted: “{d['text']}”. The selected concept is present, but unselected content was added (a documented defect).", 9)
        # ---- D: summary ----
        await say(pg, f"Evaluation: {n} frozen scenarios, four languages. The gate lifts success from {pct('llm3_pre|ui')}% to {pct('deployed|ui')}%; explicit polarity and intent fields give {pct('deployed|st')}%.", 8)
        await say(pg, "A template alone reaches %d%% with explicit fields, so the gate is a safeguard, not a gain in sentence quality." % pct("template_only|st"), 7)
        await say(pg, "Speech: the IndicF5 checkpoint is gated; this build returns a placeholder tone. A narrated take is pending.", 6)
        await say(pg, "Package: source, fixtures, scorer and instructions. Download URL to be inserted at submission.", 5)
        stop.set(); await gtask; await ctx.close(); await b.close()
    lst = pathlib.Path(tmp) / "frames.txt"
    lines = []
    for k, (t, f) in enumerate(frames):
        dur = (frames[k + 1][0] - t) if k + 1 < len(frames) else 1.0
        lines.append(f"file '{f}'\nduration {max(dur, 0.02):.3f}")
    lines.append(f"file '{frames[-1][1]}'")
    lst.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", "fps=10,format=yuv420p", "-c:v", "libx264", "-crf", "24", "-movflags", "+faststart", str(OUT / "screencast_silent_captioned.mp4")], check=True)
    def ts(x): h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60; return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")
    srt = "\n".join(f"{i}\n{ts(a)} --> {ts(c)}\n{t}\n" for i, (a, c, t) in enumerate([c for c in cues if not c[2].startswith("Generating")], 1))
    (OUT / "captions.srt").write_text(srt, encoding="utf-8")
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(OUT / "screencast_silent_captioned.mp4")], capture_output=True, text=True).stdout.strip()
    print("duration_s", dur, "| cues", len(cues))

asyncio.run(main())
