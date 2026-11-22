#!/usr/bin/env python3
"""Run a gate (archived or revised) on the dev gate probes and report false acceptances / rejections."""
import json, sys, collections
from common import ROOT, V2, jl, load_module
sys.path.insert(0, str(ROOT / "indic-generative-aac/backend"))
def run(which):
    if which == "archived":
        sem = load_module("semantic_archived", V2 / "archived_system/indic-generative-aac/backend/semantic.py")
        v = sem.SemanticValidator(None); mk = lambda r, ents: dict(intent=("STATEMENT" if r["act"] == "FEELING" else "REQUEST"), negation=r["negation"], entities=ents)
        led = lambda c: {"forbidden": ["breakfast","lunch","dinner","today","tomorrow","yesterday","morning","night","evening","tonight","planning","going to","restaurant","store","shop","buying","eating out","hungry","delicious","future","past"]}
    else:
        import semantic; v = semantic.SemanticValidator(None); mk = lambda r, ents: dict(act=r["act"], negation=r["negation"], entities=ents, concept_ids=[c for c in r["concept_ids"] if c != "NO"])
        led = lambda c: {}
    import aac_lexicon as L
    out = []
    for r in jl(V2 / "fixtures/dev/gate_probes.jsonl"):
        ents = [L.BOARD[c][r["lang"]] for c in r["concept_ids"] if c != "NO"]
        ok, d = v.validate(mk(r, ents), led(None), r["text"], r["lang"])
        out.append(dict(r, gate_accept=ok, reasons=d.get("violations_detected")))
    return out
if __name__ == "__main__":
    for which in ("archived", "revised"):
        rows = run(which)
        fa = [r for r in rows if r["gate_accept"] and not r["gold_accept"]]; fr = [r for r in rows if not r["gate_accept"] and r["gold_accept"]]
        print(f"{which}: n={len(rows)} false_accept={len(fa)}/{sum(not r['gold_accept'] for r in rows)} false_reject={len(fr)}/{sum(r['gold_accept'] for r in rows)}")
        if which == "revised" or "-v" in sys.argv:
            for r in fa + fr: print("  ", "FA" if r in fa else "FR", r["lang"], r["category"], r["text"], r["reasons"])
