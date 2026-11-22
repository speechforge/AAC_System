#!/usr/bin/env python3
"""Drive the REAL web client in headless Chrome: click the board symbols of each scenario (and type personal words), press
"AI Polish & Speak" and capture the POST /generate payload (the endpoint response is stubbed so no model is needed).
Two clients are captured with the same procedure:
  original : archived_system/indic-generative-aac/frontend/index.html  (commit fe4e185)
  revised  : indic-generative-aac/frontend/index.html                  (working tree)
Optional per-row user act (revised client only): rows with "user_act" set the Message-type control before pressing the button.
Usage: python browser_capture.py --client original|revised --split legacy|dev|holdout [--workers 3] [--limit N]"""
import argparse, asyncio, json, pathlib, re, subprocess, sys, time
from playwright.async_api import async_playwright
from common import *

BOARD = json.loads((ARCH / "fixtures/board_vocab.json").read_text(encoding="utf-8"))["vocab"]
CAT_OF = {s["id"]: cat for cat, syms in BOARD.items() for s in syms}
CAT_LABEL = {  # CATEGORIES in index.html
    "core": dict(en="Core Words", hi="मुख्य शब्द", gu="મુખ્ય શબ્દો", mr="मुख्य शब्द"), "actions": dict(en="Actions", hi="क्रियाएं", gu="ક્રિયાઓ", mr="कृती"),
    "food": dict(en="Food & Drink", hi="खान-पान", gu="ખોરાક", mr="अन्न"), "feelings": dict(en="Feelings", hi="भावनाएं", gu="લાગણીઓ", mr="भावना"),
    "people": dict(en="People", hi="लोग", gu="લોકો", mr="व्यक्ती"), "places": dict(en="Places", hi="स्थान", gu="સ્થળો", mr="ठिकाणे"),
    "body": dict(en="Health & Body", hi="शरीर व सेहत", gu="શરીર", mr="शरीर"), "chat": dict(en="Social", hi="संवाद", gu="સંવાદ", mr="संवाद"),
    "emergency": dict(en="Urgent", hi="आपातकालीन", gu="તાત્કાલિક", mr="तातडीचे")}
PORT = dict(original=8101, revised=8102)
DIRS = dict(original=ARCH_SYS / "frontend", revised=REPO / "frontend")
STUB = json.dumps(dict(text="", outcome="failure", audio_b64=None, metrics={}))


def start_server(client):
    return subprocess.Popen([sys.executable, "-m", "http.server", str(PORT[client]), "--bind", "127.0.0.1"], cwd=str(DIRS[client]),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


async def worker(browser, client, rows, out, wid):
    ctx = await browser.new_context(viewport=dict(width=1100, height=1000), locale="en-US")
    pg = await ctx.new_page()
    cap = {}
    async def on_gen(route):
        cap["payload"] = route.request.post_data_json
        await route.fulfill(status=200, content_type="application/json", body=STUB)
    await pg.route("**/generate", on_gen)
    await pg.route("**/predict_next", lambda r: r.fulfill(status=200, content_type="application/json", body='{"predictions": []}'))
    await pg.route("**/api/**", lambda r: r.fulfill(status=200, content_type="application/json", body="{}"))
    await pg.goto(f"http://127.0.0.1:{PORT[client]}/index.html", wait_until="load", timeout=90000)
    await pg.evaluate("localStorage.clear()"); await pg.reload(wait_until="load"); await pg.wait_for_timeout(2500)
    cur_lang = "en"
    for r in rows:
        t0 = time.time(); status = "ok"; cap.clear()
        try:
            if r["lang"] != cur_lang:
                await pg.locator("select").first.select_option(r["lang"]); await pg.wait_for_timeout(500); cur_lang = r["lang"]
            await pg.locator('button[title="Clear entire sentence canvas"]').click(timeout=3000, force=True)
            await pg.wait_for_timeout(80)
            if client == "revised":
                await pg.locator("#message-type-select").select_option(r.get("user_act") or "auto")
            lang = r["lang"]; cur_cat = None
            for el, lab in zip(r["seq"], r["labels"]):
                if "typed" in el:
                    inp = pg.locator('input[type="text"]').first
                    await inp.fill(el["typed"]); await inp.press("Enter"); await pg.wait_for_timeout(120); continue
                cat = CAT_OF[el["cid"]]
                if cat != cur_cat:
                    tab = pg.locator("button.flex-shrink-0.font-bold").filter(has_text=CAT_LABEL[cat][lang])
                    await tab.last.click(); await pg.wait_for_timeout(150); cur_cat = cat   # last: Quick Express buttons above the board can share a label
                card = pg.locator("button").filter(has_text=re.compile(rf"^\s*\S*\s*{re.escape(lab)}\s*$", re.S))
                n = await card.count()
                if n == 0:
                    raise RuntimeError(f"card not found: {lab} in {cat}")
                await card.nth(n - 1).click(); await pg.wait_for_timeout(100)
            btn = pg.get_by_role("button", name=re.compile("AI Polish"))
            cap.clear()                      # drop anything captured before the real button press (e.g. a Quick Express tap)
            await btn.click(timeout=3000)
            for _ in range(60):
                if cap.get("payload"): break
                await pg.wait_for_timeout(50)
            if not cap.get("payload"): status = "no_request"
        except Exception as e:
            status = f"error: {str(e)[:120]}"
        out.append(dict(id=r["id"], lang=r["lang"], client=client, user_act=r.get("user_act"), status=status, payload=cap.get("payload"), seconds=round(time.time() - t0, 2)))
        if len(out) % 25 == 0:
            print(f"[{client}] {len(out)} captured", flush=True)
    await ctx.close()


async def main(client, split, workers, limit, rows_path=None, out_path=None):
    rows = jl(rows_path or V2 / "fixtures" / split / "scenarios.jsonl")
    if limit: rows = rows[:limit]
    srv = start_server(client); time.sleep(1.5)
    out = []
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", headless=True, args=["--no-sandbox"])
            chunks = [rows[i::workers] for i in range(workers)]
            await asyncio.gather(*[worker(b, client, ch, out, i) for i, ch in enumerate(chunks) if ch])
            await b.close()
    finally:
        srv.terminate()
    order = {r["id"]: i for i, r in enumerate(rows)}
    out.sort(key=lambda o: order[o["id"]])
    dest = pathlib.Path(out_path) if out_path else V2 / "results/payloads" / f"{client}_{split}.jsonl"
    dest.parent.mkdir(parents=True, exist_ok=True)
    write_jl(dest, out)
    bad = [o for o in out if o["status"] != "ok"]
    print(f"{client}/{split}: {len(out)} captured, {len(bad)} not ok -> {dest}")
    for o in bad[:8]: print("  ", o["id"], o["status"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--client", required=True, choices=["original", "revised"]); ap.add_argument("--split", required=True)
    ap.add_argument("--workers", type=int, default=3); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    asyncio.run(main(a.client, a.split, a.workers, a.limit))
