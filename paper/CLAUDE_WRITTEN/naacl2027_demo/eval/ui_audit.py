#!/usr/bin/env python3
"""Deterministic audit of the web client's intent/polarity inference (index.html, handleGenerate ~L1332-1342)
over every single-symbol selection on the board, in all four locales. No model, no network.
Gold for a single content symbol: polarity = not negated; question only for the chat symbol 'HOW'."""
import json, pathlib
from build_scenarios import ui_infer
HERE = pathlib.Path(__file__).resolve().parent
V = json.loads((HERE / "fixtures/board_vocab.json").read_text(encoding="utf-8"))["vocab"]
rows = []
for cat, syms in V.items():
    for s in syms:
        for lang in ("en", "hi", "gu", "mr"):
            intent, neg = ui_infer([s[lang]])
            rows.append(dict(category=cat, id=s["id"], lang=lang, label=s[lang], ui_intent=intent, ui_negation=neg))
false_neg = [r for r in rows if r["ui_negation"] and r["id"] != "NO"]
q = [r for r in rows if r["ui_intent"] == "QUESTION" and r["id"] != "HOW"]
stmt = [r for r in rows if r["ui_intent"] == "STATEMENT"]
summary = dict(n_single_selections=len(rows), n_symbols=sum(len(v) for v in V.values()),
               false_negation=[(r["id"], r["lang"], r["label"]) for r in false_neg],
               false_question=[(r["id"], r["lang"], r["label"]) for r in q],
               statement_intent_symbols=sorted({(r["id"]) for r in stmt}),
               feelings_sent_as_REQUEST=[(r["id"], r["lang"]) for r in rows if r["category"] == "feelings" and r["ui_intent"] == "REQUEST"])
summary["n_false_negation"] = len(false_neg); summary["n_feelings_sent_as_REQUEST"] = len(summary["feelings_sent_as_REQUEST"])
(HERE / "results/ui_audit.json").write_text(json.dumps(dict(summary=summary, rows=rows), ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in summary.items() if k != "feelings_sent_as_REQUEST"}, ensure_ascii=False, indent=1))
print("feelings (8 symbols x 4 locales = 32 selections) sent as REQUEST:", summary["n_feelings_sent_as_REQUEST"])
