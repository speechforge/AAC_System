#!/usr/bin/env python3
"""Tiny diagram toolkit: ONE spec -> editable draw.io XML  +  SVG  (+ PDF/PNG via rsvg-convert).
Nodes/groups/edges use absolute coordinates in a W x H viewBox. Colours are colour-blind-safe (Okabe-Ito tints) and every
node class also differs in outline style (solid / dashed) so the figure survives grayscale printing."""
import html, subprocess, pathlib
from xml.sax.saxutils import escape

FONT = "Noto Sans, DejaVu Sans, sans-serif"
INDIC = "Noto Sans Devanagari, Noto Sans Gujarati, Noto Sans, DejaVu Sans, sans-serif"
MONO = "DejaVu Sans Mono, monospace"

PALETTE = {  # fill, stroke
    "client":   ("#E8F1FA", "#0072B2"),
    "server":   ("#FDF3E1", "#B26B00"),
    "model":    ("#E3F4EC", "#007A5A"),
    "gate":     ("#FBE9E6", "#B03A2E"),
    "artifact": ("#F1F1F1", "#555555"),
    "optional": ("#FFFFFF", "#777777"),
    "data":     ("#FFFFFF", "#0072B2"),
    "group_client": ("#F6FAFD", "#0072B2"),
    "group_server": ("#FFFBF3", "#B26B00"),
    "group_art":    ("#FAFAFA", "#666666"),
    "group_ext":    ("#FFFFFF", "#888888"),
}


class Diagram:
    def __init__(self, W, H, name):
        self.W, self.H, self.name = W, H, name
        self.groups, self.nodes, self.edges, self.notes = [], {}, [], []

    # ---- spec ----
    def group(self, id, x, y, w, h, title, kind, dashed=False):
        self.groups.append(dict(id=id, x=x, y=y, w=w, h=h, title=title, kind=kind, dashed=dashed))

    def node(self, id, x, y, w, h, lines, kind="client", dashed=False, shape="rect", fs=12, bold_first=True, font=FONT, align="middle"):
        self.nodes[id] = dict(id=id, x=x, y=y, w=w, h=h, lines=lines, kind=kind, dashed=dashed, shape=shape, fs=fs,
                              bold_first=bold_first, font=font, align=align)

    def edge(self, id, pts, src=None, dst=None, label=None, lpos=None, dashed=False, fs=10.5, arrow=True, lanchor="middle"):
        self.edges.append(dict(id=id, pts=pts, src=src, dst=dst, label=label, lpos=lpos, dashed=dashed, fs=fs, arrow=arrow, lanchor=lanchor))

    def note(self, x, y, text, fs=10.5, anchor="start", bold=False, font=FONT, fill="#222"):
        self.notes.append(dict(x=x, y=y, text=text, fs=fs, anchor=anchor, bold=bold, font=font, fill=fill))

    # ---- SVG ----
    def svg(self):
        o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" width="{self.W}" height="{self.H}" font-family="{FONT}">',
             '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker></defs>',
             f'<rect width="{self.W}" height="{self.H}" fill="#fff"/>']
        for g in self.groups:
            f, s = PALETTE[g["kind"]]
            o.append(f'<rect x="{g["x"]}" y="{g["y"]}" width="{g["w"]}" height="{g["h"]}" rx="9" fill="{f}" stroke="{s}" stroke-width="1.4"' + (' stroke-dasharray="6 4"' if g["dashed"] else '') + '/>')
            o.append(f'<text x="{g["x"]+9}" y="{g["y"]+16}" font-size="12" font-weight="700" fill="{s}">{escape(g["title"])}</text>')
        for n in self.nodes.values():
            f, s = PALETTE[n["kind"]]
            dash = ' stroke-dasharray="5 3"' if n["dashed"] else ''
            if n["shape"] == "diamond":
                cx, cy = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
                o.append(f'<polygon points="{cx},{n["y"]} {n["x"]+n["w"]},{cy} {cx},{n["y"]+n["h"]} {n["x"]},{cy}" fill="{f}" stroke="{s}" stroke-width="1.6"{dash}/>')
            else:
                o.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" rx="6" fill="{f}" stroke="{s}" stroke-width="1.5"{dash}/>')
            lh = n["fs"] * 1.22
            total = lh * len(n["lines"])
            y0 = n["y"] + (n["h"] - total) / 2 + n["fs"] * 0.95
            tx = n["x"] + n["w"] / 2 if n["align"] == "middle" else n["x"] + 7
            for i, ln in enumerate(n["lines"]):
                w = ' font-weight="700"' if (i == 0 and n["bold_first"]) else ''
                o.append(f'<text x="{tx}" y="{y0 + i*lh:.1f}" text-anchor="{n["align"]}" font-size="{n["fs"]}"{w} font-family="{n["font"]}" fill="#111">{escape(ln)}</text>')
        for e in self.edges:
            p = " ".join(f"{x},{y}" for x, y in e["pts"])
            dash = ' stroke-dasharray="5 3"' if e["dashed"] else ''
            mk = ' marker-end="url(#ah)"' if e["arrow"] else ''
            o.append(f'<polyline points="{p}" fill="none" stroke="#333" stroke-width="1.4"{dash}{mk}/>')
            if e["label"]:
                lx, ly = e["lpos"] or e["pts"][len(e["pts"]) // 2]
                tw = len(e["label"]) * e["fs"] * 0.55
                ax = lx if e["lanchor"] == "middle" else (lx if e["lanchor"] == "start" else lx)
                x0 = lx - tw / 2 if e["lanchor"] == "middle" else (lx if e["lanchor"] == "start" else lx - tw)
                o.append(f'<rect x="{x0-2:.1f}" y="{ly-e["fs"]*0.95:.1f}" width="{tw+4:.1f}" height="{e["fs"]*1.25:.1f}" fill="#fff" fill-opacity="0.85"/>')
                o.append(f'<text x="{lx}" y="{ly}" text-anchor="{e["lanchor"]}" font-size="{e["fs"]}" font-family="{FONT}" fill="#222">{escape(e["label"])}</text>')
        for t in self.notes:
            o.append(f'<text x="{t["x"]}" y="{t["y"]}" text-anchor="{t["anchor"]}" font-size="{t["fs"]}" font-family="{t["font"]}"' + (' font-weight="700"' if t["bold"] else '') + f' fill="{t["fill"]}">{escape(t["text"])}</text>')
        o.append('</svg>')
        return "\n".join(o)

    # ---- draw.io ----
    def drawio(self):
        cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
        def style(kind, dashed, extra=""):
            f, s = PALETTE[kind]
            return f"rounded=1;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};strokeWidth=1.5;{'dashed=1;' if dashed else ''}{extra}"
        for g in self.groups:
            f, s = PALETTE[g["kind"]]
            st = f"rounded=1;whiteSpace=wrap;html=1;fillColor={f};strokeColor={s};strokeWidth=1.4;verticalAlign=top;align=left;spacingLeft=8;spacingTop=2;fontStyle=1;fontColor={s};fontSize=12;{'dashed=1;' if g['dashed'] else ''}"
            cells.append(f'<mxCell id="g_{g["id"]}" value="{html.escape(g["title"], quote=True)}" style="{st}" vertex="1" parent="1"><mxGeometry x="{g["x"]}" y="{g["y"]}" width="{g["w"]}" height="{g["h"]}" as="geometry"/></mxCell>')
        for n in self.nodes.values():
            ls = [html.escape(x) for x in n["lines"]]
            if n["bold_first"] and ls:
                ls[0] = f"<b>{ls[0]}</b>"
            val = html.escape("<br>".join(ls), quote=True)
            shape = "rhombus;" if n["shape"] == "diamond" else ""
            node_style = style(n["kind"], n["dashed"], shape + "fontSize=%s;" % n["fs"])
            cells.append(f'<mxCell id="{n["id"]}" value="{val}" style="{node_style}" vertex="1" parent="1"><mxGeometry x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" as="geometry"/></mxCell>')
        for e in self.edges:
            inner = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in e["pts"][1:-1])
            sp = f'<mxPoint x="{e["pts"][0][0]}" y="{e["pts"][0][1]}" as="sourcePoint"/>'
            tp = f'<mxPoint x="{e["pts"][-1][0]}" y="{e["pts"][-1][1]}" as="targetPoint"/>'
            arr = "endArrow=block;endFill=1;" if e["arrow"] else "endArrow=none;"
            st = f"edgeStyle=none;html=1;{arr}strokeWidth=1.4;strokeColor=#333333;{'dashed=1;' if e['dashed'] else ''}fontSize={e['fs']};fontFamily=Courier New;labelBackgroundColor=#FFFFFF;"
            geo = f'<mxGeometry relative="1" as="geometry">{sp}{tp}' + (f'<Array as="points">{inner}</Array>' if inner else '') + '</mxGeometry>'
            src = f' source="{e["src"]}"' if e["src"] else ''
            dst = f' target="{e["dst"]}"' if e["dst"] else ''
            cells.append(f'<mxCell id="e_{e["id"]}" value="{html.escape(e["label"] or "", quote=True)}" style="{st}" edge="1" parent="1"{src}{dst}>{geo}</mxCell>')
        for i, t in enumerate(self.notes):
            st = f"text;html=1;align={'center' if t['anchor']=='middle' else 'left'};verticalAlign=middle;fontSize={t['fs']};{'fontStyle=1;' if t['bold'] else ''}"
            cells.append(f'<mxCell id="note_{i}" value="{html.escape(t["text"], quote=True)}" style="{st}" vertex="1" parent="1"><mxGeometry x="{t["x"]-(0 if t["anchor"]!="middle" else 100)}" y="{t["y"]-t["fs"]}" width="200" height="{t["fs"]*1.6:.0f}" as="geometry"/></mxCell>')
        return ('<mxfile host="app.diagrams.net"><diagram id="%s" name="%s"><mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="%d" pageHeight="%d" math="0" shadow="0"><root>%s</root></mxGraphModel></diagram></mxfile>'
                % (self.name, self.name, self.W, self.H, "".join(cells)))

    # ---- write + render ----
    def write(self, outdir):
        outdir = pathlib.Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
        (outdir / f"{self.name}.svg").write_text(self.svg(), encoding="utf-8")
        (outdir / f"{self.name}.drawio").write_text(self.drawio(), encoding="utf-8")
        import shutil; rs = shutil.which("rsvg-convert") or "rsvg-convert"
        subprocess.run([rs, "-f", "pdf", "-o", str(outdir / f"{self.name}.pdf"), str(outdir / f"{self.name}.svg")], check=True)
        subprocess.run([rs, "-f", "png", "-z", "2.5", "-o", str(outdir / f"{self.name}.png"), str(outdir / f"{self.name}.svg")], check=True)
