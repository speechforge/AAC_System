#!/usr/bin/env python3
"""UI reliability / accessibility probes that do NOT call the LLM (CPU only).
Each probe records what was observed; no probe is interpreted as 'accessibility coverage' beyond the tested interaction."""
import asyncio, json, pathlib, re, urllib.request, urllib.error
from playwright.async_api import async_playwright
HERE = pathlib.Path(__file__).resolve().parent
SHOT = HERE.parent / "screenshots/original"
URL = "http://localhost:8000/"
out = {}

def http(method, path, body=None):
    req = urllib.request.Request("http://localhost:8000" + path, data=(json.dumps(body).encode() if body is not None else None), method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req, timeout=30); return r.status, r.read()[:300].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:300].decode("utf-8", "replace")

async def tokens(pg):
    t = await pg.evaluate("document.body.innerText")
    m = re.search(r"(\d+)\s*words?", t)
    return int(m.group(1)) if m else 0

async def main():
    # ---- API-level failure paths ----
    out["api_invalid_request"] = dict(zip(("status", "body"), http("POST", "/generate", {"intent": "REQUEST"})))          # missing entities
    out["api_empty_entities"] = dict(zip(("status", "body"), http("POST", "/predict_next", {"current_words": [], "language": "gu"})))
    out["api_unknown_voice_delete"] = dict(zip(("status", "body"), http("DELETE", "/api/voice/preset_x")))
    out["api_clone_non_audio"] = None
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
        # ---- 1. CDN blocked: everything except localhost aborted ----
        ctx = await b.new_context(viewport=dict(width=720, height=1000))
        pg = await ctx.new_page()
        await pg.route("**/*", lambda route: route.continue_() if route.request.url.startswith("http://localhost") else route.abort())
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:160])); pg.on("console", lambda m: errs.append(m.text[:160]) if m.type == "error" else None)
        await pg.goto(URL, wait_until="load", timeout=60000); await pg.wait_for_timeout(2500)
        body = (await pg.evaluate("document.body.innerText")).strip()
        out["frontend_with_external_hosts_blocked"] = dict(visible_text_chars=len(body), rendered_app=("Sentence" in body or "SENTENCE" in body), first_errors=errs[:3])
        await pg.screenshot(path=str(SHOT / "20_offline_cdn_blocked.png")); await ctx.close()
        # ---- 2. keyboard-only selection ----
        ctx = await b.new_context(viewport=dict(width=720, height=1000)); pg = await ctx.new_page()
        await pg.goto(URL, wait_until="networkidle"); await pg.evaluate("localStorage.clear()"); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(1200)
        before = await tokens(pg); seen = []
        for i in range(60):
            await pg.keyboard.press("Tab")
            d = await pg.evaluate("(()=>{const e=document.activeElement;return {tag:e.tagName,txt:(e.innerText||e.getAttribute('aria-label')||'').trim().slice(0,30)}})()")
            seen.append(d)
        # try activating the currently focused control with Enter and Space and see whether the word count changes
        await pg.keyboard.press("Enter"); await pg.wait_for_timeout(500); after_enter = await tokens(pg)
        out["keyboard"] = dict(words_before=before, words_after_enter_on_focused=after_enter, tab_stops_sampled=[s["txt"] for s in seen[:25]],
                               focus_reaches_symbol_cards=any(s["txt"] in ("Yes", "No", "Want", "Help") for s in seen), distinct_tab_stops=len({s["txt"] for s in seen}))
        # does Tab reach a symbol card AND does Enter select it?  Focus a known core card explicitly via keyboard sequence:
        await pg.evaluate("document.activeElement && document.activeElement.blur()")
        cards = pg.locator("button").filter(has_text=re.compile(r"^\s*\S*\s*Yes\s*$"))
        n = await cards.count(); await cards.nth(n - 1).focus(); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(500)
        out["keyboard"]["words_after_enter_on_focused_Yes_card"] = await tokens(pg)
        await pg.keyboard.press("Space"); await pg.wait_for_timeout(500)
        out["keyboard"]["words_after_space_on_focused_Yes_card"] = await tokens(pg)
        # ---- 3. ARIA tree ----
        snap = await pg.locator("body").aria_snapshot()
        roles = {}
        for line in snap.splitlines():
            m = re.match(r"\s*-\s*(\w+)", line)
            if m: roles[m.group(1)] = roles.get(m.group(1), 0) + 1
        unnamed_btn = len(re.findall(r"- button(?!\s+\")", snap))
        out["aria"] = dict(role_counts=roles, buttons_with_empty_accessible_name=unnamed_btn, aria_label_attrs=await pg.evaluate("document.querySelectorAll('[aria-label]').length"),
                           html_lang=await pg.evaluate("document.documentElement.lang"), live_regions=await pg.evaluate("document.querySelectorAll('[aria-live],[role=status],[role=alert]').length"))
        # ---- 4. Un-Jumble with HMM-2 absent ----
        await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(1000)
        for lab in ("Yes", "Help"):
            loc = pg.locator("button").filter(has_text=re.compile(rf"^\s*\S*\s*{lab}\s*$")); await loc.nth(await loc.count() - 1).click(); await pg.wait_for_timeout(300)
        await pg.get_by_role("button", name=re.compile("Un-Jumble")).click(); await pg.wait_for_timeout(1500)
        toast = await pg.evaluate("document.body.innerText")
        out["unjumble_without_HMM2"] = dict(toast_text_found=("Un-Jumble unavailable" in toast), snippet=[l for l in toast.splitlines() if "Jumble" in l][:3])
        await ctx.close()
        # ---- 5. touch (emulated) ----
        ctx = await b.new_context(viewport=dict(width=720, height=1000), has_touch=True, is_mobile=True, device_scale_factor=2); pg = await ctx.new_page()
        await pg.goto(URL, wait_until="networkidle"); await pg.evaluate("localStorage.clear()"); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(1200)
        loc = pg.locator("button").filter(has_text=re.compile(r"^\s*\S*\s*Yes\s*$")); await loc.nth(await loc.count() - 1).tap(); await pg.wait_for_timeout(500)
        out["touch_emulated"] = dict(words_after_tap=await tokens(pg), note="Chromium touch emulation, not a physical device")
        await ctx.close(); await b.close()
    (HERE / "results/reliability_ui.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1)[:3500])

asyncio.run(main())
