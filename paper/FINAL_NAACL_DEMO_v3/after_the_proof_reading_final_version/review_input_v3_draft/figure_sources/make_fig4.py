#!/usr/bin/env python3
"""Figure 4 of the v3 manuscript: one message ("No" + "Water") through the deployed pipeline in four languages.

English is the baseline language (the language the pipeline was first built for); Hindi, Gujarati and Marathi are the
proposed Indic extension.  Every cascade candidate and every spoken sentence is a RECORDED output of the frozen
evaluation (raw_pipeline.jsonl, web-client payload); the gate verdicts are recomputed with the deployed (archived)
deterministic validator on the recorded candidate.  Only the English glosses are typed by hand.

Run:  python3 make_fig4.py     (writes out/fig4_languages.{svg,drawio,pdf,png}; copies the PDF to ../latex_source_v3/figures/)
"""
import json, pathlib, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]                                                       # repository root
RAW = ROOT / "paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results/raw_pipeline.jsonl"
BACKEND = ROOT / "udpated_version_context_of_papers/v2/archived_system/indic-generative-aac/backend"   # the evaluated (archived) system
OUT = HERE / "out"
FIG = HERE.parent / "latex_source_v3/figures"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(BACKEND))
from diagramlib import Diagram, FONT, INDIC, PALETTE

RED, GREEN, BLUE, GREY = "#AC252B", "#17674A", "#155B8A", "#5A5A5A"
PALETTE["base"] = ("#F4F4F4", "#6B6B6B")
PALETTE["ok"] = ("#EAF6F0", "#17674A")
PALETTE["bad"] = ("#FBEAEA", "#AC252B")
PALETTE["tmpl"] = ("#E9F1F8", "#155B8A")
PALETTE["group_base"] = ("#FAFAFA", "#6B6B6B")
PALETTE["group_prop"] = ("#F6FAFD", "#155B8A")

recs = [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
NAMES = {"en": "English", "hi": "Hindi", "gu": "Gujarati", "mr": "Marathi"}
LABELS = {"en": ["No", "Water"], "hi": ["नहीं", "पानी"], "gu": ["ના", "પાણી"], "mr": ["नाही", "पाणी"]}


def find(lang):
    for r in recs:
        p = r["payload"]
        if p["language"] == lang and p["entities"] == LABELS[lang] and p["intent"] == "NEGATION" and not p["code_mix"]:
            return r
    raise LookupError(lang)


def verdict(r):
    """Recompute the gate verdict of the recorded last cascade candidate with the deployed validator."""
    from llm import IndicLLM
    from semantic import SemanticValidator
    p = r["payload"]
    ctx = dict(intent=p["intent"], actor="USER", entities=p["entities"], attributes=[], relations=[], temporal_state=None, location=None,
               people=[], actions=[], negation=bool(p["negation"]) or p["intent"].upper() == "NEGATION", speaker_role="USER")
    led = IndicLLM.build_concept_ledger(None, IndicLLM.build_structured_context(None, ctx, language=NAMES[p["language"]], code_mix=False))
    cand = r["response"]["llm3_final_text"] or r["response"]["candidate_llm1"]
    ok, d = SemanticValidator(None).validate(ctx, led, cand, p["language"])
    return cand, ok, d


def reason(ok, d):
    if ok:
        return "all checks pass"
    bad = []
    if not d.get("entity_match", True): bad.append("selected concept missing")
    if not d.get("negation_match", True): bad.append("negation missing")
    if not d.get("intent_match", True): bad.append("wrong act")
    if d.get("unsupported_additions"): bad.append("unrequested content")
    # 'negation missing' implies the negator label is also absent; report the polarity failure first
    return bad[1] if (len(bad) == 2 and bad[1] == "negation missing") else bad[0]


def line(t, c="#111", i=False, b=False, f=None, s=1.0):
    d = dict(t=t, c=c, i=i, b=b, s=s)
    if f: d["f"] = f
    return d


# Hand-set line breaks and glosses (English glosses are the authors'; they are not native-reviewed).
WRAP = {"en": ["“I am not and will", "eat at.”"], "hi": ["“नहीं, मैं नहीं चाहिए।”"], "gu": ["“મને પાણી ના જોઈએ છે.”"], "mr": ["“मला पाणी हवे आहे.”"]}
CAND_NOTE = {"en": "", "hi": "", "gu": "gloss: “I do not want water”", "mr": "gloss: “I want water”"}
SPK_NOTE = {"en": "template; stilted", "hi": "gloss: “I do not want water”", "gu": "gloss: “I do not want water”", "mr": "gloss: “I do not want water”"}
SPK_WRAP = {"en": ["“I want No Water.”"], "hi": ["“मुझे नहीं पानी चाहिए।”"], "gu": ["“મને પાણી ના જોઈએ છે.”"], "mr": ["“मला नाही पाणी हवे आहे.”"]}


def build():
    d = Diagram(640, 300, "fig4_languages")
    X0, CW, GAP = 78, 134, 7
    xs = [X0 + i * (CW + GAP) for i in range(4)]
    y_hdr, HH = 24, 34                                          # header node: language and selection
    y1 = y_hdr + HH + 10
    H2, H3, H4 = 56, 38, 56
    RG = 10                                                     # row gap (room for the arrow heads)
    ys = [y_hdr, y1, y1 + H2 + RG, y1 + H2 + H3 + 2 * RG]
    hs = [HH, H2, H3, H4]
    gh = ys[3] + H4 + 6 - 2
    d.group("base", xs[0] - 4, 2, CW + 8, gh, "Baseline", "group_base")
    d.group("prop", xs[1] - 4, 2, 3 * CW + 2 * GAP + 8, gh, "Proposed Indic extension", "group_prop")
    labels = ["1  Selection", "2  Cascade\noutput", "3  Gate\ncheck", "4  Spoken\nsentence"]
    kinds = ["client", "model", "gate", "data"]
    for k, (lab, y, h, kd) in enumerate(zip(labels, ys, hs, kinds)):
        d.node(f"lab{k}", 4, y, 66, h, lab.split("\n"), kd, fs=10, align="start")
    info = {}
    for i, lang in enumerate(["en", "hi", "gu", "mr"]):
        r = find(lang)
        cand, ok, dd = verdict(r)
        fb = r["response"]["fallback_used"]
        assert ok == (not fb), (lang, ok, fb)            # recorded route and recomputed verdict agree
        spoken = r["response"]["text"]
        info[lang] = (cand, ok, reason(ok, dd), spoken)
        f = FONT if lang == "en" else INDIC
        x = xs[i]
        sel = " + ".join(LABELS[lang])
        d.node(f"h{i}", x, ys[0], CW, HH, [line(NAMES[lang], b=True, c="#111"), line(sel, b=True, f=f, s=0.95)], "base" if lang == "en" else "client", fs=11, bold_first=False)
        col = GREEN if ok else RED
        cl = [line(t, c=col, f=f) for t in WRAP[lang]]
        if CAND_NOTE[lang]:
            cl.append(line(CAND_NOTE[lang], c=GREY, i=True, s=0.86))
        d.node(f"c{i}", x, ys[1], CW, H2, cl, "ok" if ok else "bad", fs=10, font=f, bold_first=False)
        gl = [line("Accepted" if ok else "Rejected twice", c=GREEN if ok else RED, b=True), line(reason(ok, dd), c="#111", s=0.95)]
        d.node(f"g{i}", x, ys[2], CW, H3, gl, "ok" if ok else "bad", fs=10.5, bold_first=False)
        sc = GREEN if ok else BLUE
        sl = [line(t, c=sc, f=f) for t in SPK_WRAP[lang]]
        sl.append(line("model sentence" if ok else "template floor", c=sc, b=True, s=0.86))
        sl.append(line(SPK_NOTE[lang] if not ok else "gloss: \u201cI do not want water\u201d", c=GREY, i=True, s=0.86))
        d.node(f"p{i}", x, ys[3], CW, H4, sl, "ok" if ok else "tmpl", fs=10, font=f, bold_first=False)
        for k in range(3):
            d.edge(f"e{i}{k}", [(x + CW / 2, ys[k] + hs[k]), (x + CW / 2, ys[k + 1])])
    yl = ys[3] + H4 + 8
    d.H = yl + 10
    d.vscale(0.9)
    return d, info


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    dg, info = build()
    dg.write(OUT)
    shutil.copy(OUT / f"{dg.name}.pdf", FIG / f"{dg.name}.pdf")
    for k, v in info.items():
        print(k, v)
