#!/usr/bin/env python3
"""Browser-to-speech path and demonstration captures on the LIVE revised server (http://localhost:8000, started with `python app.py`).
Measures, per locale and scenario, the time from pressing 'AI Polish & Speak' to the first playback event (audio element 'playing' for the backend audio, or
SpeechSynthesis 'start' for the browser voice) and records what kind of audio it was (placeholder tone vs IndicF5), the browser voices present per locale and the peak GPU
memory sampled with nvidia-smi.  It also captures the three demo states (successful render, correct rejection + fallback, clarification) and the offline literal-preview state.
Output: results/audit/B_speech_path.json, reviewer_packet/demo_captures/*.png.
Run mode: python speech_and_demo_check.py [--repeats 3]"""
import argparse, asyncio, json, pathlib, re, statistics, subprocess, threading, time
from playwright.async_api import async_playwright
from common import *
from browser_capture import CAT_OF, CAT_LABEL

URL = "http://localhost:8000/"
BOARD = json.loads((ARCH / "fixtures/board_vocab.json").read_text(encoding="utf-8"))["vocab"]
LAB = {s["id"]: s for c in BOARD.values() for s in c}
INIT = """
window.__ev = []; window.__t0 = null;
const _play = HTMLMediaElement.prototype.play;
HTMLMediaElement.prototype.play = function () { window.__ev.push({t: performance.now(), type: 'audio.play', bytes: (this.src||'').length});
  this.addEventListener('playing', () => window.__ev.push({t: performance.now(), type: 'audio.playing'}), {once: true}); return _play.apply(this, arguments); };
if (window.speechSynthesis) { const _s = window.speechSynthesis.speak.bind(window.speechSynthesis);
  window.speechSynthesis.speak = function (u) { window.__ev.push({t: performance.now(), type: 'speech.speak', lang: u.lang, voice: (u.voice && u.voice.name) || null});
    u.addEventListener('start', () => window.__ev.push({t: performance.now(), type: 'speech.start'})); return _s(u); }; }
"""
SCEN = [("water", ["WATER"]), ("no_pizza", ["NO", "PIZZA"]), ("tired", ["TIRED"]), ("help_teacher", ["HELP", "TEACHER"])]


class GpuSampler(threading.Thread):
    def __init__(self): super().__init__(daemon=True); self.stop = False; self.peak = 0
    def run(self):
        while not self.stop:
            try:
                o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout.strip()
                self.peak = max(self.peak, int(o.splitlines()[0]))
            except Exception: pass
            time.sleep(0.5)


async def click_seq(pg, lang, ids):
    await pg.locator('button[title="Clear entire sentence canvas"]').click(force=True); await pg.wait_for_timeout(100)
    cur = None
    for cid in ids:
        cat = CAT_OF[cid]
        if cat != cur:
            await pg.locator("button.flex-shrink-0.font-bold").filter(has_text=CAT_LABEL[cat][lang]).last.click(); await pg.wait_for_timeout(150); cur = cat
        lab = LAB[cid][lang]
        card = pg.locator("button").filter(has_text=re.compile(rf"^\s*\S*\s*{re.escape(lab)}\s*$", re.S))
        await card.nth(await card.count() - 1).click(); await pg.wait_for_timeout(100)


async def run_one(pg, lang, ids, shot=None):
    await click_seq(pg, lang, ids)
    await pg.evaluate("window.__ev = []; window.__t0 = performance.now();")
    async with pg.expect_response(lambda r: r.url.endswith("/generate"), timeout=300000) as ri:
        await pg.get_by_role("button", name=re.compile("AI Polish")).click()
    resp = await (await ri.value).json()
    t_resp = await pg.evaluate("performance.now() - window.__t0")
    await pg.wait_for_timeout(1500)
    ev = await pg.evaluate("window.__ev"); t0 = await pg.evaluate("window.__t0")
    first = next((e for e in ev if e["type"] in ("audio.playing", "speech.start")), None)
    if shot: await pg.screenshot(path=str(shot), full_page=False)
    return dict(outcome=resp.get("outcome"), route=resp.get("route"), text=resp.get("text"), audio_kind=resp.get("audio_kind"), t_response_ms=round(t_resp),
                t_text_s=resp["metrics"].get("t_total"), t_tts_s=resp["metrics"].get("t_tts"),
                t_first_playback_ms=(round(first["t"] - t0) if first else None), first_event=(first or {}).get("type"), events=[e["type"] for e in ev])


async def main(repeats):
    cap_dir = V2 / "reviewer_packet/demo_captures"; cap_dir.mkdir(parents=True, exist_ok=True)
    gs = GpuSampler(); gs.start(); res = dict(measured_at=now_utc(), runs=[])
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"])
        ctx = await b.new_context(viewport=dict(width=1100, height=1000)); pg = await ctx.new_page()
        await pg.add_init_script(INIT)
        await pg.goto(URL, wait_until="load", timeout=90000); await pg.evaluate("localStorage.clear()"); await pg.reload(wait_until="load"); await pg.wait_for_timeout(2500)
        res["browser_voices"] = await pg.evaluate("(() => { const v = window.speechSynthesis ? window.speechSynthesis.getVoices() : []; return {n: v.length, langs: [...new Set(v.map(x => x.lang))]}; })()")
        res["user_agent"] = await pg.evaluate("navigator.userAgent")
        first = True
        for lang in LANGS:
            await pg.locator("select").first.select_option(lang); await pg.wait_for_timeout(600)
            for name, ids in SCEN:
                for rep in range(repeats):
                    r = await run_one(pg, lang, ids)
                    r.update(lang=lang, scenario=name, repeat=rep, cold=first); first = False
                    res["runs"].append(r); print(lang, name, rep, r["outcome"], r["route"], r["t_response_ms"], r["t_first_playback_ms"], r["audio_kind"], flush=True)
        # ---- demo captures (English UI): success, rejection + fallback, clarification, offline literal preview
        await pg.locator("select").first.select_option("en"); await pg.wait_for_timeout(500)
        demo = {}
        for tag, ids in (("1_successful_render", ["WATER"]), ("2_rejection_and_fallback", ["NO", "PIZZA"]), ("3_clarification", ["NOSE"])):
            await pg.evaluate("window.scrollTo(0,0)")
            demo[tag] = await run_one(pg, "en", ids, shot=cap_dir / f"{tag}.png")
        # clarification -> user picks a type
        await pg.locator("#clarify-feeling").click(); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(cap_dir / "3b_clarification_resolved.png"))
        demo["3b_after_user_choice"] = dict(text=await pg.locator("body").inner_text())
        demo["3b_after_user_choice"]["text"] = demo["3b_after_user_choice"]["text"][:400]
        res["demo"] = demo
        # ---- offline / server-unreachable state
        await pg.route("**/generate", lambda r: r.abort())
        await click_seq(pg, "en", ["WATER"])
        await pg.get_by_role("button", name=re.compile("AI Polish")).click(); await pg.wait_for_timeout(1500)
        await pg.screenshot(path=str(cap_dir / "4_server_unreachable_literal_preview.png"))
        res["demo"]["4_server_unreachable_has_literal_card"] = await pg.locator("#result-literal").count() > 0
        await b.close()
    gs.stop = True
    runs = res["runs"]; warm = [r for r in runs if not r["cold"] and r["t_first_playback_ms"] is not None]
    def stats(v): return dict(n=len(v), median_ms=round(statistics.median(v)) if v else None, p95_ms=round(sorted(v)[int(0.95 * (len(v) - 1))]) if v else None)
    res["summary"] = dict(n_runs=len(runs), n_cold=sum(r["cold"] for r in runs), n_warm=sum(not r["cold"] for r in runs),
                          click_to_first_playback_warm=stats([r["t_first_playback_ms"] for r in warm]),
                          click_to_response_warm=stats([r["t_response_ms"] for r in runs if not r["cold"]]),
                          by_lang={l: stats([r["t_first_playback_ms"] for r in warm if r["lang"] == l]) for l in LANGS},
                          by_route={k: stats([r["t_first_playback_ms"] for r in warm if r["route"] == k]) for k in sorted({r["route"] for r in runs if r["route"]})},
                          audio_kinds={str(k): sum(1 for r in runs if r["audio_kind"] == k) for k in {r["audio_kind"] for r in runs}},
                          failures_sentence_without_playback_event=sum(1 for r in runs if r["t_first_playback_ms"] is None and r["outcome"] and r["outcome"].startswith("sentence")),
                          peak_gpu_mem_mib_system_wide=gs.peak,
                          tts_engine_mapping="backend IndicF5Engine.generate_speech: lang en (not code-mixed) -> prompt 'english_female', hi/gu/mr -> prompt 'indic_female'; no IndicF5 checkpoint present -> every locale returns a 440 Hz placeholder tone; browser fallback speak(): en en-US/en-IN/en-GB, hi hi-IN, gu gu-IN->hi-IN->en-IN, mr mr-IN->hi-IN->en-IN")
    (V2 / "results/audit/B_speech_path.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["summary"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--repeats", type=int, default=3); a = ap.parse_args()
    asyncio.run(main(a.repeats))
