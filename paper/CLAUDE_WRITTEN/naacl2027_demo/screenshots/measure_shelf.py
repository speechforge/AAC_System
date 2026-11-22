#!/usr/bin/env python3
"""Add the missing 'shelf' bounding box to original/panel_boxes.json WITHOUT regenerating any output:
re-select the same symbols (CPU only, no /generate call) and measure the next-word shelf header (CSS text-transform makes it uppercase, so match case-insensitively)."""
import asyncio, json, pathlib, re
from playwright.async_api import async_playwright
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "original"; B = json.loads((OUT / "panel_boxes.json").read_text(encoding="utf-8"))
URL = "http://localhost:8000/"
STEPS = {"a": (None, [("cat", "Food & Drink"), ("sym", "Water")]), "b": ("gu", [("cat", "મુખ્ય"), ("sym", "ના"), ("cat", "ખોરાક"), ("sym", "પાણી")]), "c": (None, [("cat", "Feelings"), ("sym", "Tired")])}
async def main():
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
        ctx = await br.new_context(viewport=dict(width=520, height=1000), device_scale_factor=2, locale="en-US")
        for name, (lang, steps) in STEPS.items():
            pg = await ctx.new_page(); await pg.goto(URL, wait_until="networkidle"); await pg.evaluate("localStorage.clear()"); await pg.reload(wait_until="networkidle"); await pg.wait_for_timeout(1200)
            if lang: await pg.select_option("select", lang); await pg.wait_for_timeout(600)
            for kind, arg in steps:
                if kind == "cat":
                    loc = pg.get_by_role("button", name=re.compile(arg)); await loc.nth(await loc.count() - 1).click()
                else:
                    loc = pg.locator("button").filter(has_text=re.compile(rf"^\s*\S*\s*{re.escape(arg)}\s*$", re.S)); await loc.nth(await loc.count() - 1).click()
                await pg.wait_for_timeout(450)
            await pg.wait_for_timeout(800); await pg.evaluate("window.scrollTo(0,0)")
            bb = await pg.get_by_text(re.compile("next word predictions", re.I)).first.bounding_box()
            B[name]["shelf"] = bb; print(name, bb and (round(bb["y"]), round(bb["height"]))); await pg.close()
        await br.close()
    (OUT / "panel_boxes.json").write_text(json.dumps(B, ensure_ascii=False, indent=1), encoding="utf-8")
asyncio.run(main())
