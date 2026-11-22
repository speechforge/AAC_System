#!/usr/bin/env python3
"""Appendix figure: interaction flow for two REAL traces taken from eval/results/raw_pipeline.jsonl (not typed by hand):
 A = an English request whose cascade output is rejected twice and replaced by the template; B = a Gujarati request accepted by the gate.
The validator verdict is recomputed with the backend's own deterministic SemanticValidator on the recorded candidate.
Output: workflow.drawio (editable), .svg, .pdf, .png."""
import sys, json, hashlib, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "indic-generative-aac/backend"))
from diagramlib import Diagram, FONT
from llm import IndicLLM
from semantic import SemanticValidator

recs = [json.loads(l) for l in (HERE.parent / "eval/results/raw_pipeline.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
def ctx_of(p):
    return dict(intent=p["intent"], actor="USER", entities=p["entities"], attributes=[], relations=[], temporal_state=None, location=None, people=[], actions=[],
                negation=bool(p["negation"]) or p["intent"].upper() == "NEGATION" or "NOT" in p["intent"].upper(), speaker_role="USER")
def pick(lang, ents, want_fallback):
    for r in recs:
        p = r["payload"]
        if p["language"] == lang and p["entities"] == ents and r.get("response") and bool(r["response"]["fallback_used"]) == want_fallback:
            return r
    return None
A = pick("en", ["Water"], True) or next(r for r in recs if r["payload"]["language"] == "en" and not r["payload"]["code_mix"] and r["response"]["fallback_used"] and len(r["payload"]["entities"]) == 1 and r["payload"]["intent"] == "REQUEST")
B = pick("gu", ["ના", "પાણી"], False) or next(r for r in recs if r["payload"]["language"] == "gu" and r["payload"]["negation"] and not r["response"]["fallback_used"])
def verdict(r):
    p = r["payload"]; c = ctx_of(p)
    lang_name = {"en": "English", "hi": "Hindi", "gu": "Gujarati", "mr": "Marathi"}[p["language"]]
    led = IndicLLM.build_concept_ledger(None, IndicLLM.build_structured_context(None, c, language=lang_name, code_mix=False))
    cand = r["response"]["llm3_final_text"] or r["response"]["candidate_llm1"]
    ok, d = SemanticValidator(None).validate(c, led, cand, p["language"])
    return cand, ok, d, led
candA, okA, dA, ledA = verdict(A); candB, okB, dB, ledB = verdict(B)
def vline(d):
    bad = [k for k in ("negation_match", "entity_match", "intent_match") if not d.get(k, True)]
    if d.get("unsupported_additions"): bad.append("no_unsupported")
    return ("fail: " + ", ".join(bad)) if bad else "all checks pass"

W, H = 700, 562
d = Diagram(W, H, "workflow")
X0, XA, XB, WS, WD = 8, 150, 428, 134, 266
d.note(XA + WD / 2, 20, "Trace A: English, rejected → template", 12, "middle", True)
d.note(XB + WD / 2, 20, "Trace B: Gujarati, accepted", 12, "middle", True)
gl = "I do not want water"
rows = [
    ("1  Select language,\n    tap symbols", ["board: Water", ""], ["board: " + B["payload"]["entities"][0] + " (No) + " + B["payload"]["entities"][1] + " (Water)", "(core + food categories)"]),
    ("2  Client request", [f"intent={A['payload']['intent']}  negation={str(A['payload']['negation']).lower()}", f"entities={json.dumps(A['payload']['entities'], ensure_ascii=False)}  language=en"],
                          [f"intent={B['payload']['intent']}  negation={str(B['payload']['negation']).lower()}", f"entities={json.dumps(B['payload']['entities'], ensure_ascii=False)}  language=gu"]),
    ("3  Concept ledger", ["required: " + ", ".join(ledgerA for ledgerA in ledA["required"][:3]), f"forbidden: {len(ledA['forbidden'])} default words"],
                          ["required: " + ", ".join(ledB["required"][:2]) + ", …", f"forbidden: {len(ledB['forbidden'])} default words"]),
    ("4  Cascade output\n    (last attempt)", [f"“{candA}”", ""], [f"“{candB}”", "(few-shot prompt, greedy)"]),
    ("5  Hard validator", [vline(dA), f"score {dA['semantic_score']:.2f}; " + (f"missing {dA.get('missing_entities')}" if dA.get('missing_entities') else "")],
                          [vline(dB), f"score {dB['semantic_score']:.2f}; no numeric threshold"]),
    ("6  Decision", ["reject × 2 → template fallback", "(returned even if it fails the gate)"], ["accept; no retry", ""]),
    ("7  Text returned", [f"“{A['response']['text']}”", "polarity kept; wording is template"], [f"“{B['response']['text']}”", f"gloss: “{gl}” (informal negation)"]),
    ("8  Speech + output card", ["IndicF5 + Vocos, 24 kHz WAV (placeholder tone here)", "card: text, Replay, Copy, bookmark"], ["IndicF5 + Vocos, 24 kHz WAV (placeholder tone here)", "card: text, Replay, Copy, bookmark"]),
]
y = 34; RH = 56; GAPY = 10
prev = None
for i, (lab, a, b) in enumerate(rows):
    kind = "gate" if i in (4, 5) else ("model" if i in (3, 7) else "client")
    d.node(f"s{i}", X0, y, WS, RH, lab.split("\n"), kind, fs=11, bold_first=True, align="start")
    d.node(f"a{i}", XA, y, WD, RH, a, "data", fs=10.5, bold_first=False, align="start")
    d.node(f"b{i}", XB, y, WD, RH, b, "data", fs=10.5, bold_first=False, align="start")
    if prev is not None:
        for cx in (X0 + WS / 2, XA + WD / 2, XB + WD / 2):
            d.edge(f"v{i}_{int(cx)}", [(cx, prev), (cx, y)], None, None)
    prev = y + RH; y += RH + GAPY
# decision annotation arrows

if __name__ == "__main__":
    d.write(HERE)
    print("trace A:", A["payload"]["entities"], "->", repr(A["response"]["text"]), "| cand:", repr(candA), "|", vline(dA))
    print("trace B:", B["payload"]["entities"], "->", repr(B["response"]["text"]), "| cand:", repr(candB), "|", vline(dB))
