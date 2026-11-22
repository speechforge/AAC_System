#!/usr/bin/env python3
"""Capture the three panels of Figure 2 from the RUNNING build (backend on :8000), signed-out default profile.
Viewport 520x1000 CSS px @2x (consistent for all panels). Writes original/panel_{a,b,c}.png and original/panel_boxes.json
(bounding boxes, CSS px) used by make_panel.py to place the numbered callouts. Needs the GPU backend for 'AI Polish & Speak'.
Usage: python capture_panels.py"""
import asyncio, json, pathlib, re
from playwright.async_api import async_playwright
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "original"; OUT.mkdir(exist_ok=True)
URL = "http://localhost:8000/"
VP = dict(width=520, height=1000)

async def sym(pg, label):
    loc = pg.locator("button").filter(has_text=re.compile(rf"^\s*\S*\s*{re.escape(label)}\s*$", re.S))
    n = await loc.count(); await loc.nth(n - 1).click(); await pg.wait_for_timeout(400)
    return label

async def cat(pg, name):
    loc = pg.get_by_role("button", name=re.compile(name)); n = await loc.count()
    await loc.nth(n - 1).click(); await pg.wait_for_timeout(500)

async def fresh(ctx, lang=None):
    pg = await ctx.new_page(); await pg.goto(URL, wait_until="networkidle", timeout=60000)
    await pg.evaluate("localStorage.clear()"); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(1500)
    if lang: await pg.select_option("select", lang); await pg.wait_for_timeout(800)
    return pg

async def card_box(pg, label):
    loc = pg.locator("button").filter(has_text=re.compile(rf"^\s*\S*\s*{re.escape(label)}\s*$", re.S))
    n = await loc.count(); return await loc.nth(n - 1).bounding_box()

async def boxes(pg):
    async def bb(loc):
        try: return await loc.first.bounding_box()
        except Exception: return None
    b = {}
    b["canvas_label"] = await bb(pg.get_by_text("SENTENCE CANVAS"))
    b["chips"] = await bb(pg.get_by_placeholder(re.compile("Add word|word")))
    b["shelf"] = await bb(pg.get_by_text(re.compile("NEXT WORD PREDICTIONS")))
    b["polish_btn"] = await bb(pg.get_by_role("button", name=re.compile("AI Polish")))
    b["output_card"] = await bb(pg.locator("xpath=//span[contains(., 'Natural Realization')]/ancestor::div[contains(@class,'border-emerald-500')][1]"))
    b["output_text"] = await bb(pg.locator("xpath=//span[contains(., 'Natural Realization')]/ancestor::div[contains(@class,'border-emerald-500')][1]//div[contains(@class,'font-black')]"))
    b["tabs_bar"] = await bb(pg.get_by_role("button", name=re.compile("^Standard$|Standard")))
    b["page_scroll_y"] = await pg.evaluate("window.scrollY")
    b["page_height"] = await pg.evaluate("document.documentElement.scrollHeight")
    return b

async def run_panel(ctx, name, lang, steps, record):
    pg = await fresh(ctx, lang)
    last = None
    for kind, arg in steps:
        if kind == "cat": await cat(pg, arg)
        else: last = await sym(pg, arg)
    await pg.wait_for_timeout(1000)
    await pg.get_by_role("button", name=re.compile("AI Polish")).click()
    await pg.wait_for_selector("text=Natural Realization", timeout=180000); await pg.wait_for_timeout(900)
    await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(400)
    record[name] = await boxes(pg); record[name]["selected_card"] = await card_box(pg, last); record[name]["selected_label"] = last
    record[name]["text"] = await pg.evaluate("""(()=>{const e=[...document.querySelectorAll('div')].find(d=>d.className&&String(d.className).includes('font-black')&&d.innerText&&d.innerText.startsWith('"'));return e?e.innerText:null})()""")
    await pg.screenshot(path=str(OUT / f"panel_{name}_full.png"), full_page=True)
    await pg.close()

async def main():
    rec = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
        ctx = await b.new_context(viewport=VP, device_scale_factor=2, locale="en-US")
        await run_panel(ctx, "a", None, [("cat", "Food & Drink"), ("sym", "Water")], rec)
        await run_panel(ctx, "b", "gu", [("cat", "મુખ્ય"), ("sym", "ના"), ("cat", "ખોરાક"), ("sym", "પાણી")], rec)
        await run_panel(ctx, "c", None, [("cat", "Feelings"), ("sym", "Tired")], rec)
        await b.close()
    (OUT / "panel_boxes.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v.get("text") for k, v in rec.items()}, ensure_ascii=False))

asyncio.run(main())
