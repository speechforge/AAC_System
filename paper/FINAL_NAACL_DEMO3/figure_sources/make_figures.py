#!/usr/bin/env python3
"""Figures of the v2 manuscript (teaser, architecture, interaction trace).

Evidence figures (teaser, trace) are built from the recorded raw outputs of the frozen evaluation; the gate verdicts are
recomputed with the deployed deterministic validator on the recorded candidates. Nothing in them is typed by hand except
the glosses. The architecture figure is a concept figure and carries no evidence.

Run:  python3 make_figures.py          (writes figure_sources/out/*.{svg,drawio,pdf,png} and copies the PDFs to ../latex_source_v2/figures)
"""
import json, pathlib, shutil, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]                                   # repository root
RAW = HERE.parent.parent / "CLAUDE_WRITTEN/naacl2027_demo/eval/results/raw_pipeline.jsonl"
BACKEND = ROOT / "indic-generative-aac/backend"
OUT = HERE / "out"
FIG = HERE.parent / "latex_source_v2/figures"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(BACKEND))
from diagramlib import Diagram, FONT, INDIC, PALETTE

PALETTE["warn"] = ("#FFF4D6", "#B26B00")
recs = [json.loads(l) for l in RAW.read_text(encoding="utf-8").splitlines() if l.strip()]
NAMES = {"en": "English", "hi": "Hindi", "gu": "Gujarati", "mr": "Marathi"}


def find(lang, ents, intent, neg):
    for r in recs:
        p = r["payload"]
        if p["language"] == lang and p["entities"] == ents and p["intent"] == intent and bool(p["negation"]) == neg and not p["code_mix"]:
            return r
    raise LookupError((lang, ents, intent, neg))


def verdict(r):
    """Recompute the gate verdict of the recorded last cascade candidate with the deployed validator."""
    from llm import IndicLLM
    from semantic import SemanticValidator
    p = r["payload"]
    ctx = dict(intent=p["intent"], actor="USER", entities=p["entities"], attributes=[], relations=[], temporal_state=None, location=None,
               people=[], actions=[], negation=bool(p["negation"]) or p["intent"].upper() == "NEGATION" or "NOT" in p["intent"].upper(), speaker_role="USER")
    led = IndicLLM.build_concept_ledger(None, IndicLLM.build_structured_context(None, ctx, language=NAMES[p["language"]], code_mix=False))
    cand = r["response"]["llm3_final_text"] or r["response"]["candidate_llm1"]
    ok, d = SemanticValidator(None).validate(ctx, led, cand, p["language"])
    return cand, ok, d, led


def pretty(item):
    """Ledger entries in words (the ledger itself stores upper-case tags)."""
    tags = {"ACTOR:USER": "speaker", "NEGATION (MUST BE NEGATIVE)": "negative polarity"}
    if item in tags:
        return tags[item]
    if item.startswith("INTENT:"):
        return item.split(":", 1)[1].lower() + " intent"
    return item.capitalize() if item.isascii() else item


def reason(ok, d):
    if ok:
        return "all checks pass"
    bad = []
    if not d.get("entity_match", True):
        bad.append("selected concept missing")
    if not d.get("negation_match", True):
        bad.append("negation mismatch")
    if not d.get("intent_match", True):
        bad.append("wrong act")
    if d.get("unsupported_additions"):
        bad.append("unrequested content")
    return ", ".join(bad)


# ------------------------------------------------------------------------------------------------ Figure 1: teaser
def teaser():
    A = find("en", ["Water"], "REQUEST", False)            # client payload
    B = find("mr", ["पाणी"], "REQUEST", True)              # explicit negation field ('No' is not an entity)
    C = find("en", ["Tired"], "REQUEST", False)            # client payload
    cA, okA, dA, _ = verdict(A); cB, okB, dB, _ = verdict(B); cC, okC, dC, _ = verdict(C)
    assert (not okA) and (not okB) and okC, "unexpected gate verdicts"
    assert A["response"]["fallback_used"] and B["response"]["fallback_used"] and not C["response"]["fallback_used"]
    W = 640
    d = Diagram(W, 236, "teaser")
    cols = [(6, 104, "1  Selection"), (126, 196, "2  Cascade output (last attempt)"), (338, 140, "3  Concept gate"), (494, 142, "4  Spoken")]
    for x, w, t in cols:
        d.note(x + w / 2, 16, t, 11.5, "middle", True)
    rows = [
        (["English", "Water"], [f"“{cA}”", "a selected concept is replaced"], ["Rejected twice:", reason(okA, dA)],
         [f"“{A['response']['text']}”", "template floor"], False, False),
        (["Marathi", "नाही + पाणी", "(‘no’ + ‘water’)"], [f"“{cB}”", "= “I want water”: polarity inverted"],
         ["Rejected twice:", reason(okB, dB)], [f"“{B['response']['text']}”", "= “I do not want water”"], True, False),
        (["English", "Tired"], ["“The user is tired of waiting for", "their meal and wants to go out to eat.”"],
         ["Accepted:", reason(okC, dC)], [f"same sentence is spoken", "gate miss: third person,", "content added"], False, True),
    ]
    y, RH, GAP = 26, 58, 8
    for i, (c1, c2, c3, c4, indic, miss) in enumerate(rows):
        f = INDIC if indic else FONT
        d.node(f"a{i}", cols[0][0], y, cols[0][1], RH, c1, "client", fs=10.5, font=INDIC if i == 1 else FONT)
        d.node(f"b{i}", cols[1][0], y, cols[1][1], RH, c2, "model", fs=10, bold_first=False, font=INDIC if i == 1 else FONT)
        d.node(f"c{i}", cols[2][0], y, cols[2][1], RH, c3, "gate", fs=10.5)
        d.node(f"d{i}", cols[3][0], y, cols[3][1], RH, c4, "warn" if miss else "data", dashed=miss, fs=10.5 if not miss else 10, bold_first=not miss, font=INDIC if i == 1 else FONT)
        cy = y + RH / 2
        for j in range(3):
            xa = cols[j][0] + cols[j][1]; xb = cols[j + 1][0]
            d.edge(f"e{i}{j}", [(xa, cy), (xb, cy)])
        y += RH + GAP
    return d, (A, B, C)


# ------------------------------------------------------------------------------------------------ Figure 2: architecture
def architecture():
    d = Diagram(640, 290, "architecture")
    d.group("client", 4, 4, 132, 272, "Browser", "group_client")
    d.group("server", 170, 4, 290, 272, "Server (local)", "group_server")
    d.group("art", 494, 4, 142, 272, "Models and data", "group_art")
    d.group("pred", 176, 24, 278, 58, "Prediction", "group_server")
    d.group("gen", 176, 90, 278, 180, "Realization and speech", "group_server")
    d.node("c1", 10, 26, 120, 44, ["1  Symbol board", "69 symbols, 9 categories"], "client", fs=10)
    d.node("c2", 10, 78, 120, 44, ["2  Sentence canvas", "ordered labels, intent"], "client", fs=10)
    d.node("c3", 10, 130, 120, 36, ["3  Next-word shelf", "suggestions"], "client", fs=10)
    d.node("c4", 10, 174, 120, 44, ["4  Output card", "text, replay, audio"], "client", fs=10)
    d.node("c5", 10, 226, 120, 42, ["Browser speech", "raw labels; fallback"], "optional", dashed=True, fs=10)
    d.node("s1", 182, 46, 100, 32, ["Suffix trie", "English, Hindi"], "model", fs=10)
    d.node("s2", 288, 46, 78, 32, ["N-gram", "fallback"], "server", fs=10)
    d.node("s3", 372, 46, 76, 32, ["Un-Jumble", "HMM-2"], "optional", dashed=True, fs=10)
    d.node("g1", 186, 110, 258, 34, ["Concept ledger", "required and forbidden concepts"], "server", fs=10)
    d.node("g2", 186, 152, 258, 34, ["Qwen2.5-0.5B-Instruct cascade", "realize, refine, verify; one retry"], "model", fs=10)
    d.node("g3", 186, 194, 258, 34, ["Concept gate", "polarity, concepts, intent, extra content"], "gate", fs=10)
    d.node("g4", 186, 238, 118, 28, ["Template floor"], "gate", fs=10, bold_first=False)
    d.node("g5", 330, 238, 114, 28, ["Speech synthesis"], "model", fs=10, bold_first=False)
    d.node("a1", 500, 28, 130, 32, ["Dialogue data", "English, Hindi"], "artifact", fs=10)
    d.node("a4", 500, 68, 130, 32, ["HMM-1, HMM-2", "optional"], "optional", dashed=True, fs=10)
    d.node("a2", 500, 152, 130, 34, ["Qwen weights", "local copy"], "artifact", fs=10)
    d.node("ext", 500, 190, 130, 44, ["Optional services", "sign-in, symbol art,", "transliteration"], "optional", dashed=True, fs=9.5)
    d.node("a3", 500, 238, 130, 28, ["IndicF5 + reference clips"], "artifact", fs=9.5, bold_first=False)
    d.edge("k1", [(70, 70), (70, 78)])
    d.edge("p1", [(130, 94), (144, 94), (144, 62), (182, 62)])
    d.edge("p2", [(182, 72), (154, 72), (154, 146), (130, 146)])
    d.edge("r0", [(130, 108), (164, 108), (164, 127), (186, 127)])
    d.edge("r1", [(315, 144), (315, 152)])
    d.edge("r2", [(315, 186), (315, 194)])
    d.edge("r3", [(245, 228), (245, 238)], label="rejected twice", lpos=(250, 234), lanchor="start", fs=9)
    d.edge("r4", [(387, 228), (387, 238)], label="accepted", lpos=(392, 234), lanchor="start", fs=9)
    d.edge("r5", [(304, 252), (330, 252)])
    d.edge("r6", [(387, 266), (387, 282), (158, 282), (158, 196), (130, 196)])
    d.edge("x1", [(500, 169), (444, 169)], dashed=True)
    d.edge("x2", [(500, 252), (444, 252)], dashed=True)
    d.edge("x3", [(70, 218), (70, 226)], dashed=True, arrow=False)
    return d


# ------------------------------------------------------------------------------------------------ Appendix figure: trace
def ledger_lines(led):
    items = [pretty(x) for x in led["required"]]
    half = 2 if len(items) > 3 else len(items)
    lines = ["required: " + ", ".join(items[:half])]
    if items[half:]:
        lines.append(", ".join(items[half:]))
    lines.append(f"forbidden: {len(led['forbidden'])} default words")
    return lines


def trace(A, B):
    cA, okA, dA, ledA = verdict(A); cB, okB, dB, ledB = verdict(B)
    pa, pb = A["payload"], B["payload"]
    yn = lambda v: "yes" if v else "no"
    ents = lambda p: ", ".join(p["entities"])
    W = 640
    d = Diagram(W, 440, "workflow")
    X0, WS, XA, XB, WD = 4, 108, 120, 382, 254
    d.note(XA + WD / 2, 16, "Trace A: English, cascade rejected, template spoken", 11, "middle", True)
    d.note(XB + WD / 2, 16, "Trace B: Gujarati, cascade accepted", 11, "middle", True)
    glB = "I do not want water"
    rows = [
        ("1  Selection", ["Water", "(food and drink category)"], [ents(pb), "(‘no’ + ‘water’; informal negation)"]),
        ("2  Request", [f"intent: {pa['intent'].lower()}; negation: {yn(pa['negation'])}", f"selected: {ents(pa)}"], [f"intent: {pb['intent'].lower()}; negation: {yn(pb['negation'])}", f"selected: {ents(pb)}"]),
        ("3  Ledger", ledger_lines(ledA), ledger_lines(ledB)),
        ("4  Cascade", [f"“{cA}”", "last of two attempts"], [f"“{cB}”", "few-shot prompt, greedy decoding"]),
        ("5  Gate check", [("fail: " + reason(okA, dA)) if not okA else "all checks pass", f"agreement score {dA['semantic_score']:.2f}"], [("fail: " + reason(okB, dB)) if not okB else "all checks pass", f"agreement score {dB['semantic_score']:.2f}; no threshold applied"]),
        ("6  Decision", ["rejected twice: template floor", "(returned without re-validation)"], ["accepted; no retry", ""]),
        ("7  Spoken text", [f"“{A['response']['text']}”", "polarity kept; wording from template"], [f"“{B['response']['text']}”", f"gloss: “{glB}”"]),
    ]
    y, RH, GAP = 26, 50, 8
    prev = None
    for i, (lab, a, b) in enumerate(rows):
        kind = "gate" if i in (4, 5) else ("model" if i in (3, 6) else "client")
        d.node(f"s{i}", X0, y, WS, RH, [lab], kind, fs=10.5, align="start")
        d.node(f"a{i}", XA, y, WD, RH, a, "data", fs=10, bold_first=False, align="start")
        d.node(f"b{i}", XB, y, WD, RH, b, "data", fs=10, bold_first=False, align="start", font=INDIC)
        if prev is not None:
            for cx in (X0 + WS / 2, XA + WD / 2, XB + WD / 2):
                d.edge(f"v{i}_{int(cx)}", [(cx, prev), (cx, y)])
        prev = y + RH; y += RH + GAP
    d.H = y
    return d, (cA, okA, cB, okB)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
    t, (A, B, C) = teaser()
    ar = architecture()
    wf_A = find("en", ["Water"], "REQUEST", False)
    wf_B = find("gu", ["ના", "પાણી"], "NEGATION", True)
    wf, info = trace(wf_A, wf_B)
    for dg in (t, ar, wf):
        dg.write(OUT)
        shutil.copy(OUT / f"{dg.name}.pdf", FIG / f"{dg.name}.pdf")
    print("teaser rows:", [(r["payload"]["language"], r["payload"]["entities"], r["response"]["text"]) for r in (A, B, C)])
    print("trace verdicts:", info)
