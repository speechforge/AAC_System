#!/usr/bin/env python3
"""Capture authentic screenshots of the running build (signed-out, default profile, no private data).
Viewport 720x1000 CSS px @2x. Originals -> screenshots/original/*.png ; box metadata -> screenshots/original/boxes.json
Requires: backend on :8000 (python app.py), Playwright + system Chrome.  Usage: python capture.py"""
import asyncio, json, pathlib, re, sys
from playwright.async_api import async_playwright
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "original"; OUT.mkdir(exist_ok=True)
URL = "http://localhost:8000/"
VP = dict(width=720, height=1000)
boxes = {}

async def box(pg, loc, name, key):
    try:
        b = await loc.first.bounding_box()
        if b: boxes.setdefault(name, {})[key] = b
    except Exception as e:
        print("no box", name, key, e)

async def sym(pg, label):
    """click the board grid card (last match; Quick Express duplicates come first)."""
    loc = pg.locator("button").filter(has_text=re.compile(rf"^\s*\S*\s*{re.escape(label)}\s*$", re.S))
    n = await loc.count()
    await loc.nth(n - 1).click()
    await pg.wait_for_timeout(400)

async def cat(pg, name):
    # category tabs come after the Quick Express buttons that may share a label -> take the last match
    loc = pg.get_by_role("button", name=re.compile(name)); n = await loc.count()
    await loc.nth(n - 1).click(); await pg.wait_for_timeout(500)

async def generate(pg, wait_s=120):
    await pg.get_by_role("button", name=re.compile("AI Polish")).click()
    await pg.wait_for_selector("text=Natural Realization", timeout=wait_s * 1000)
    await pg.wait_for_timeout(800)

async def fresh(ctx, lang_value=None):
    pg = await ctx.new_page()
    await pg.goto(URL, wait_until="networkidle", timeout=60000)
    await pg.evaluate("localStorage.clear()")
    await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(1500)
    if lang_value:
        await pg.select_option("select", lang_value); await pg.wait_for_timeout(800)
    return pg

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
        ctx = await b.new_context(viewport=VP, device_scale_factor=2, locale="en-US")
        errs = []
        # ---------- reference: desktop home (1440x900) ----------
        ctxd = await b.new_context(viewport=dict(width=1440, height=900), device_scale_factor=1)
        pgd = await fresh(ctxd); await pgd.screenshot(path=str(OUT / "00_desktop_home_1440x900.png")); await ctxd.close()
        # ---------- English: Water ----------
        pg = await fresh(ctx)
        pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
        await pg.screenshot(path=str(OUT / "01_en_home.png"))
        await cat(pg, "Food & Drink"); await sym(pg, "Water")
        await pg.wait_for_timeout(1200)
        await pg.screenshot(path=str(OUT / "02_en_compose_water.png"))
        await generate(pg)
        await pg.screenshot(path=str(OUT / "03_en_output_water.png"), full_page=False)
        await pg.evaluate("window.scrollTo(0, 0)")
        txt = await pg.evaluate("document.body.innerText")
        (OUT / "03_en_output_water.txt").write_text(txt[:2500], encoding="utf-8")
        await pg.close()
        # ---------- English: No + Pizza (negation; known awkward fallback text; kept as an original) ----------
        pg = await fresh(ctx)
        await pg.get_by_role("button", name=re.compile("^🙅 No$|^\\s*🙅\\s*No\\s*$")).first.click() if False else None
        await cat(pg, "Core Words"); await sym(pg, "No"); await cat(pg, "Food & Drink"); await sym(pg, "Pizza")
        await pg.wait_for_timeout(1000); await pg.screenshot(path=str(OUT / "04_en_compose_no_pizza.png"))
        await generate(pg); await pg.screenshot(path=str(OUT / "05_en_output_no_pizza.png")); await pg.close()
        # ---------- Gujarati: ના + પાણી ----------
        pg = await fresh(ctx, "gu")
        await cat(pg, "મુખ્ય"); await sym(pg, "ના"); await cat(pg, "ખોરાક"); await sym(pg, "પાણી")
        await pg.wait_for_timeout(1200); await pg.screenshot(path=str(OUT / "06_gu_compose_no_water.png"))
        await generate(pg); await pg.screenshot(path=str(OUT / "07_gu_output_no_water.png")); await pg.close()
        # ---------- Hindi: पानी ----------
        pg = await fresh(ctx, "hi")
        await cat(pg, "खान"); await sym(pg, "पानी")
        await pg.wait_for_timeout(1200); await pg.screenshot(path=str(OUT / "08_hi_compose_water.png"))
        await generate(pg); await pg.screenshot(path=str(OUT / "09_hi_output_water.png")); await pg.close()
        # ---------- English: Tired (feeling; the web client infers REQUEST) ----------
        pg = await fresh(ctx)
        await cat(pg, "Feelings"); await sym(pg, "Tired"); await pg.wait_for_timeout(1000)
        await pg.screenshot(path=str(OUT / "10_en_compose_tired.png"))
        await generate(pg); await pg.screenshot(path=str(OUT / "11_en_output_tired.png")); await pg.close()
        # ---------- existing architecture/audit dashboard shipped in the repo ----------
        ctxa = await b.new_context(viewport=dict(width=1440, height=900), device_scale_factor=1)
        pga = await ctxa.new_page()
        await pga.goto("file://" + str(HERE.parents[2] / "aac_system_dashboard.html"), wait_until="networkidle", timeout=60000)
        await pga.wait_for_timeout(1500)
        await pga.screenshot(path=str(OUT / "12_repo_dashboard_viewport.png"))
        await pga.screenshot(path=str(OUT / "13_repo_dashboard_fullpage.png"), full_page=True)
        await ctxa.close()
        print("page errors:", errs)
        await b.close()

asyncio.run(main())
