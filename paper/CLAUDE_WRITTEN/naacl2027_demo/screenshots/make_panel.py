#!/usr/bin/env python3
"""Compose Figure 2 from the ORIGINAL full-page screenshots (never altered except by cropping and overlaying numbered callouts).
Each panel = [canvas ... output card] stacked over [category bar + selected symbol card]; callouts: 1 board, 2 canvas, 3 suggestion shelf,
4 'AI Polish & Speak', 5 output card.  Output: figures/ui_panel.pdf/.png and screenshots/annotated/*.png."""
import json, pathlib
from PIL import Image, ImageDraw, ImageFont
HERE = pathlib.Path(__file__).resolve().parent
ORIG = HERE / "original"; ANN = HERE / "annotated"; ANN.mkdir(exist_ok=True)
FIG = HERE.parent / "figures"; FIG.mkdir(exist_ok=True)
S = 2  # device scale factor used by capture_panels.py
B = json.loads((ORIG / "panel_boxes.json").read_text(encoding="utf-8"))
font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
lab = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)

def callout(d, x, y, n):
    r = 24
    d.ellipse([x - r, y - r, x + r, y + r], fill=(213, 94, 0), outline="white", width=3)
    w = d.textlength(str(n), font=font)
    d.text((x - w / 2, y - 18), str(n), fill="white", font=font)

panels = {}
panels_top = {}
for name in "abc":
    im = Image.open(ORIG / f"panel_{name}_full.png").convert("RGB"); b = B[name]
    W = im.width
    y0 = int((b["canvas_label"]["y"] - 26) * S); y1 = int((b["output_card"]["y"] + b["output_card"]["height"] + 10) * S)
    card = b["selected_card"]; tabs = b["tabs_bar"]
    by0 = int((tabs["y"] - 10) * S); by1 = int((card["y"] + card["height"] + 10) * S)
    top = im.crop((0, y0, W, y1)); bot = im.crop((0, by0, W, by1))
    sep = 16
    out = Image.new("RGB", (W, top.height + sep + bot.height), "white")
    out.paste(top, (0, 0)); out.paste(bot, (0, top.height + sep))
    d = ImageDraw.Draw(out)
    d.rectangle([0, top.height, W, top.height + sep], fill=(220, 220, 220))
    def tp(box, dx=0, dy=0): return (int((box["x"]) * S + dx), int((box["y"]) * S - y0 + dy))
    def bt(box, dx=0, dy=0): return (int((box["x"]) * S + dx), int((box["y"]) * S - by0 + top.height + sep + dy))
    callout(d, *bt(card, 22, 22), 1)
    callout(d, *tp(b["chips"], 20, 8), 2)
    callout(d, *tp(b["shelf"], -6, 6), 3)
    callout(d, *tp(b["polish_btn"], -4, 4), 4)
    callout(d, *tp(b["output_text"], -8, -2), 5)
    out.save(ANN / f"panel_{name}_annotated.png")
    panels[name] = out
    panels_top[name] = out.crop((0, 0, W, top.height))

def compose(names, stem):
    ps = [panels[n] for n in names]; gap = 30; H = max(p.height for p in ps); W = sum(p.width for p in ps) + gap * (len(ps) - 1)
    fig = Image.new("RGB", (W, H + 70), "white"); x = 0; d = ImageDraw.Draw(fig)
    for p, n in zip(ps, names):
        fig.paste(p, (x, 0)); d.text((x + p.width // 2 - 40, H + 12), f"({n})", fill="black", font=lab); x += p.width + gap
    fig.save(FIG / f"{stem}.png"); fig.save(FIG / f"{stem}.pdf", "PDF", resolution=250.0)
    print(stem, fig.size)

compose("ab", "ui_panel")      # main text, Figure 2
t = panels_top["c"]; t.save(FIG / "ui_failure.png"); t.save(FIG / "ui_failure.pdf", "PDF", resolution=250.0); print("ui_failure (canvas+output only)", t.size)
