#!/usr/bin/env python3
"""PHASE A -- reproduce and audit the archived run. Loads no model; modifies no archived file.

Inputs  (read only): paper/CLAUDE_WRITTEN/naacl2027_demo/eval/{fixtures,results}, original scorer score.py,
                     archived_system/ (backend and client at the pinned commit).
Outputs (v2/results/audit/): A1_recomputed.json, A1_claims_check.csv, A1_subtotals.csv, A2_exclusion_log.csv,
                     A2_all184_sensitivity.json, A3_cohorts_explicit.json, A3_failures.csv, A4_naive_baseline.json,
                     A4_naive_outputs.csv, A6_feeling_denominator.json, A7_paired_ci_recomputed.json.
Usage:  python3 audit_archived.py
"""
import ast, collections, json, pathlib, re, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *

S1 = load_module("score_v1", ARCH / "score.py")                       # the ORIGINAL scorer, unmodified
ORIG = load_module("orig_llm", ARCH_SYS / "backend/llm.py")          # ORIGINAL backend (imports torch, loads no weights)
OUT = V2 / "results/audit"; OUT.mkdir(parents=True, exist_ok=True)

scs = jl(ARCH / "fixtures/scenarios.jsonl")
raw = {r["key"]: r for r in jl(ARCH / "results/raw_pipeline.jsonl")}
naive = {r["id"]: r for r in jl(ARCH / "results/raw_naive.jsonl")}
archived_csv = {}
import csv as _csv
for r in _csv.DictReader(open(ARCH / "results/scored.csv", encoding="utf-8")):
    archived_csv[(r["id"], r["system"], r["cond"])] = r
archived_summary = json.loads((ARCH / "results/summary.json").read_text(encoding="utf-8"))

# ------------------------------------------------------------------ few-shot overlap, from the ORIGINAL prompt source
tree = ast.parse((ARCH_SYS / "backend/llm.py").read_text(encoding="utf-8"))
FEW = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "FEW_SHOT" for t in node.targets):
        FEW = ast.literal_eval(node.value)
EXAMPLES = {lang: {ex_in: ex_out for ex_in, ex_out in cfg["examples"]} for lang, cfg in FEW.items()}
_src = (ARCH_SYS / "backend/llm.py").read_text(encoding="utf-8")
_HEADS = re.findall(r'q = f"(.*?)\{', _src)            # query headers copied from the source, in the order hi, gu, mr
assert len(_HEADS) == 3, _HEADS
PREFIX = {   # (negation) / REQUEST,WANT / STATEMENT,FEEL / else / header / empty-entity placeholder  -- values read from llm.py _llm1_realize
    "hi": ("नहीं चाहिए", "मुझे चाहिए", "मैं कह रहा हूँ", "क्या मुझे मिल सकता है", _HEADS[0], "यह"),
    "gu": ("નથી જોઈતું", "મને જોઈએ છે", "હું કહું છું", "શું મને મળી શકે", _HEADS[1], "આ"),
    "mr": ("नको आहे", "मला हवे आहे", "मी सांगत आहे", "मला मिळू शकेल का", _HEADS[2], "हे"),
}


def api_negation(p):
    return bool(p["negation"]) or p["intent"].upper() == "NEGATION" or "NOT" in p["intent"].upper()


def query(p):
    """Query string that llm._llm1_realize builds for hi/gu/mr (few-shot path); None for English / code-mixed."""
    lang = p["language"]
    if p["code_mix"] or lang not in FEW:
        return None
    neg, req, stmt, ques, head, empty = PREFIX[lang]
    I = p["intent"].upper()
    pre = neg if api_negation(p) else (req if I in ("REQUEST", "WANT") else (stmt if I in ("STATEMENT", "FEEL") else ques))
    ents = p["entities"]
    return head + " + ".join([pre] + ents if ents else [pre, empty])


# ------------------------------------------------------------------ rebuild every output and re-score with the original scorer
def api_ctx(p):
    return dict(intent=p["intent"], actor="USER", entities=p["entities"], negation=api_negation(p))


rows = []
overlap_log = []
for sc in scs:
    reasons = []
    for cond in ("ui", "structured"):
        q = query(sc["payload_" + cond])
        if q is not None and q in EXAMPLES[sc["payload_" + cond]["language"]]:
            reasons.append(dict(cond=cond, query=q, example_output=EXAMPLES[sc["payload_" + cond]["language"]][q]))
    sc["_overlap"] = bool(reasons)
    if reasons:
        overlap_log.append(dict(id=sc["id"], lang=sc["lang"], type=sc["type"], conds="+".join(r["cond"] for r in reasons),
                                matching_prompt_input=reasons[0]["query"], prompt_example_output=reasons[0]["example_output"],
                                rule="query string built by llm.py equals a few-shot example input (exact string)"))


def add(sc, system, cond, text, extra=None):
    r = dict(id=sc["id"], lang=sc["lang"], code_mix=sc["code_mix"], type=sc["type"], system=system, cond=cond, text=text, overlap=sc["_overlap"])
    if text is None:
        r.update(retention=0.0, n_concepts=len(sc["content_concepts"]), n_present=0, polarity_ok=False, polarity_drop=sc["gold_neg"], polarity_spur=False,
                 act_ok=False, act_wrong=False, act_missing=True, unsupported=False, unsupported_hits=[], offtask=True, script_ok=False, success=False)
    else:
        r.update(S1.score(sc, text))
    r.update(extra or {})
    rows.append(r)


for sc in scs:
    add(sc, "literal_join", "any", " ".join(sc["labels"]))
    nv = naive.get(sc["id"]); add(sc, "naive_qwen", "ui", nv["text"] if nv else None)
    for cond, tag in (("ui", "ui"), ("structured", "st")):
        p = sc["payload_" + cond]
        add(sc, "template_only", tag, ORIG.IndicLLM.generate_deterministic_fallback(None, api_ctx(p), language=p["language"], code_mix=p["code_mix"]))
        rec = raw.get(payload_key(p)); resp = rec.get("response") if rec else None
        for stage, fld in (("llm1", "candidate_llm1"), ("llm2", "candidate_llm2"), ("llm3_pre", "llm3_final_text"), ("deployed", "text")):
            extra = {}
            if stage == "deployed":
                extra = dict(fallback=bool(resp and resp.get("fallback_used")), validated=bool(resp and resp.get("validated")))
            add(sc, stage, tag, resp.get(fld) if resp else None, extra)

# ---- consistency of my re-scoring with the archived scored.csv (row by row)
mism = []
for r in rows:
    a = archived_csv.get((r["id"], r["system"], r["cond"]))
    if a is None or (a["success"] == "True") != bool(r["success"]) or (a["text"] != (r["text"] or "")) or (a["overlap"] == "True") != r["overlap"]:
        mism.append(dict(id=r["id"], system=r["system"], cond=r["cond"], mine=r["success"], archived=a and a["success"], same_text=bool(a) and a["text"] == (r["text"] or "")))
consistency = dict(n_rows_rescored=len(rows), n_rows_archived=len(archived_csv), n_mismatches=len(mism), mismatches=mism[:20])

# ------------------------------------------------------------------ aggregates
FLAGS = ["success", "polarity_ok", "polarity_drop", "polarity_spur", "act_ok", "act_wrong", "act_missing", "unsupported", "offtask", "script_ok"]


def agg(rs):
    n = len(rs); ci = sum(r["n_concepts"] for r in rs); cp = sum(r["n_present"] for r in rs)
    o = dict(n=n, concept_instances=ci, concepts_present=cp)
    for f in FLAGS:
        o[f] = sum(bool(r[f]) for r in rs)
    o["polarity_errors"] = n - o["polarity_ok"]
    return o


def sel(system, cond, lang=None, family=None, primary=True, code_mix=False):
    return [r for r in rows if r["system"] == system and r["cond"] == cond and r["code_mix"] == code_mix
            and (lang is None or r["lang"] == lang) and (family is None or r["type"] == family) and (not primary or not r["overlap"])]


SYSTEMS = [("literal_join", "any"), ("naive_qwen", "ui"), ("template_only", "ui"), ("llm3_pre", "ui"), ("deployed", "ui"),
           ("template_only", "st"), ("llm3_pre", "st"), ("deployed", "st")]
A1 = dict(pooled={}, by_lang={}, by_family={}, all184={})
for s, c in SYSTEMS:
    A1["pooled"][f"{s}|{c}"] = agg(sel(s, c))
    A1["all184"][f"{s}|{c}"] = agg(sel(s, c, primary=False))
    A1["by_lang"][f"{s}|{c}"] = {l: agg(sel(s, c, lang=l)) for l in LANGS}
    A1["by_family"][f"{s}|{c}"] = {f: agg(sel(s, c, family=f)) for f in sorted({sc["type"] for sc in scs if not sc["code_mix"]})}
fam_n = {f: len(sel("deployed", "ui", family=f)) for f in A1["by_family"]["deployed|ui"]}
A1["n_primary"] = len(sel("deployed", "ui")); A1["n_primary_by_lang"] = {l: len(sel("deployed", "ui", lang=l)) for l in LANGS}
A1["n_all_monolingual"] = len(sel("deployed", "ui", primary=False)); A1["n_excluded_overlap"] = len(overlap_log)
A1["n_hinglish"] = len([sc for sc in scs if sc["code_mix"]]); A1["family_sizes_primary"] = fam_n
A1["concept_instances_primary"] = A1["pooled"]["deployed|ui"]["concept_instances"]
A1["consistency_with_archived_scored_csv"] = consistency
A1["overlap_flag_matches_archived"] = sorted(sc["id"] for sc in scs if sc["_overlap"]) == sorted(archived_summary["meta"]["overlap_ids"])

# ---- gate routing
route = {}
for cond in ("ui", "st"):
    for lang in LANGS + ["all"]:
        rs = sel("deployed", cond) if lang == "all" else sel("deployed", cond, lang=lang)
        acc = [r for r in rs if not r["fallback"]]; fb = [r for r in rs if r["fallback"]]
        route[f"{cond}|{lang}"] = dict(n=len(rs), accepted=len(acc), accepted_success=sum(r["success"] for r in acc), accepted_fail=sum(not r["success"] for r in acc),
                                       fallback=len(fb), fallback_success=sum(r["success"] for r in fb), fallback_fail=sum(not r["success"] for r in fb))
A1["gate_routing"] = route
(OUT / "A1_recomputed.json").write_text(json.dumps(A1, ensure_ascii=False, indent=1), encoding="utf-8")

# ---- claims check (manuscript v2 values vs recomputed)
P = A1["pooled"]
claims = [
    ("unconstrained Qwen success (single prompt)", "8/175", f"{P['naive_qwen|ui']['success']}/{A1['n_primary']}"),
    ("cascade before gate, browser input", "65/175", f"{P['llm3_pre|ui']['success']}/{A1['n_primary']}"),
    ("deployed, browser input", "97/175", f"{P['deployed|ui']['success']}/{A1['n_primary']}"),
    ("template alone, browser input", "118/175", f"{P['template_only|ui']['success']}/{A1['n_primary']}"),
    ("cascade before gate, explicit gold fields", "71/175", f"{P['llm3_pre|st']['success']}/{A1['n_primary']}"),
    ("deployed, explicit gold fields", "132/175", f"{P['deployed|st']['success']}/{A1['n_primary']}"),
    ("template alone, explicit gold fields", "167/175", f"{P['template_only|st']['success']}/{A1['n_primary']}"),
    ("concept retention, deployed (browser)", "215/215", f"{P['deployed|ui']['concepts_present']}/{P['deployed|ui']['concept_instances']}"),
    ("concept retention, deployed (explicit)", "215/215", f"{P['deployed|st']['concepts_present']}/{P['deployed|st']['concept_instances']}"),
    ("concept retention, cascade before gate (browser)", "175/215", f"{P['llm3_pre|ui']['concepts_present']}/{P['llm3_pre|ui']['concept_instances']}"),
    ("concept retention, cascade before gate (explicit)", "185/215", f"{P['llm3_pre|st']['concepts_present']}/{P['llm3_pre|st']['concept_instances']}"),
    ("polarity errors vs gold, cascade (explicit)", "36/175", f"{P['llm3_pre|st']['polarity_errors']}/{A1['n_primary']}"),
    ("polarity errors vs gold, deployed (explicit)", "0/175", f"{P['deployed|st']['polarity_errors']}/{A1['n_primary']}"),
    ("wrong-act outputs, deployed (browser)", "54/175", f"{P['deployed|ui']['act_wrong']}/{A1['n_primary']}"),
    ("wrong-act outputs, deployed (explicit)", "17/175", f"{P['deployed|st']['act_wrong']}/{A1['n_primary']}"),
    ("accepted outputs failing full scoring (explicit)", "37/108", f"{route['st|all']['accepted_fail']}/{route['st|all']['accepted']}"),
    ("template fallbacks failing full scoring (explicit)", "6/67", f"{route['st|all']['fallback_fail']}/{route['st|all']['fallback']}"),
    ("template-only failures (explicit)", "8/175", f"{175 - P['template_only|st']['success']}/{A1['n_primary']}"),
    ("primary scenarios by language EN/HI/GU/MR", "46/45/42/42", "/".join(str(A1["n_primary_by_lang"][l]) for l in LANGS)),
    ("monolingual scenarios / excluded / Hinglish", "184 / 9 / 8", f"{A1['n_all_monolingual']} / {A1['n_excluded_overlap']} / {A1['n_hinglish']}"),
]
write_csv(OUT / "A1_claims_check.csv", [dict(claim=a, manuscript=b, recomputed=c, match=(b == c)) for a, b, c in claims])
sub = []
for s, c in SYSTEMS:
    for l in LANGS:
        a = A1["by_lang"][f"{s}|{c}"][l]; sub.append(dict(level="language", key=l, system=s, cond=c, **{k: a[k] for k in ("n", "success", "act_wrong", "polarity_errors", "concepts_present", "concept_instances")}))
    for f, a in A1["by_family"][f"{s}|{c}"].items():
        sub.append(dict(level="family", key=f, system=s, cond=c, **{k: a[k] for k in ("n", "success", "act_wrong", "polarity_errors", "concepts_present", "concept_instances")}))
write_csv(OUT / "A1_subtotals.csv", sub)

# ------------------------------------------------------------------ A2: exclusion log + all-184 sensitivity
write_csv(OUT / "A2_exclusion_log.csv", overlap_log)
sens = {f"{s}|{c}": dict(primary_175=A1["pooled"][f"{s}|{c}"]["success"], all_184_incl_prompt_overlap=A1["all184"][f"{s}|{c}"]["success"]) for s, c in SYSTEMS}
sens["_note"] = "all-184 rows INCLUDE the 9 scenarios whose prompt input reproduces a few-shot example (prompt overlap); Hinglish (8) stays exploratory and is excluded from both."
(OUT / "A2_all184_sensitivity.json").write_text(json.dumps(sens, ensure_ascii=False, indent=1), encoding="utf-8")

# ------------------------------------------------------------------ A3: cohorts under explicit gold fields
by_key = {(r["id"], r["system"], r["cond"]): r for r in rows}
fail_rows = []
for sc in scs:
    if sc["code_mix"] or sc["_overlap"]:
        continue
    d = by_key[(sc["id"], "deployed", "st")]; t = by_key[(sc["id"], "template_only", "st")]
    rec = raw.get(payload_key(sc["payload_structured"])); resp = (rec or {}).get("response") or {}
    base = dict(id=sc["id"], lang=sc["lang"], family=sc["type"], gold_concepts="+".join(sc["content_concepts"]), gold_neg=sc["gold_neg"], gold_act=sc["gold_act"],
                payload=json.dumps(sc["payload_structured"], ensure_ascii=False), cascade_final_text=resp.get("llm3_final_text"), candidate_llm1=resp.get("candidate_llm1"))
    if not d["success"]:
        fail_rows.append(dict(cohort="accepted_model" if not d["fallback"] else "template_fallback", **base, output_text=d["text"],
                              **{k: d[k] for k in ("retention", "polarity_ok", "act_ok", "act_wrong", "act_missing", "unsupported", "offtask", "script_ok")},
                              unsupported_hits="|".join(d["unsupported_hits"]), validation_violations="|".join((resp.get("validation_data") or {}).get("violations_detected") or [])))
    if not t["success"]:
        fail_rows.append(dict(cohort="template_only", **base, output_text=t["text"],
                              **{k: t[k] for k in ("retention", "polarity_ok", "act_ok", "act_wrong", "act_missing", "unsupported", "offtask", "script_ok")},
                              unsupported_hits="|".join(t["unsupported_hits"]), validation_violations=""))
write_csv(OUT / "A3_failures.csv", fail_rows)
coh = collections.Counter(r["cohort"] for r in fail_rows)
tmpl_fail = [r for r in fail_rows if r["cohort"] == "template_only"]
cohorts = dict(accepted_model=dict(n=route["st|all"]["accepted"], failing=coh["accepted_model"]), template_fallback=dict(n=route["st|all"]["fallback"], failing=coh["template_fallback"]),
               template_only=dict(n=175, failing=coh["template_only"]),
               template_only_failures_by_language=dict(collections.Counter(r["lang"] for r in tmpl_fail)),
               template_only_failures_by_family=dict(collections.Counter(r["family"] for r in tmpl_fail)),
               template_only_failure_ids=[r["id"] for r in tmpl_fail])
(OUT / "A3_cohorts_explicit.json").write_text(json.dumps(cohorts, ensure_ascii=False, indent=1), encoding="utf-8")

# ------------------------------------------------------------------ A4: the unconstrained single-prompt baseline
nv = sel("naive_qwen", "ui")
no_act_only = [r for r in nv if r["retention"] == 1.0 and r["polarity_ok"] and not r["unsupported"] and not r["offtask"] and r["script_ok"] and not r["success"]]
A4 = dict(
    recovered_settings=dict(source="archived eval/run_naive.py (reads: SYSTEM string, messages, _call_llm arguments)", model="Qwen/Qwen2.5-0.5B-Instruct",
                            revision="7ae557604adf67be50417f59c2c2f167def9a775", dtype="float16 on CUDA", chat_template="tokenizer default (Qwen2.5 ChatML) via apply_chat_template(add_generation_prompt=True)",
                            decoding="greedy: temperature argument 0.01 => do_sample False; max_new_tokens 75; stop only at EOS; no repetition penalty",
                            system_prompt="You are an assistive communication tool. Turn the selected symbols into one short, natural sentence in {language}. Output only the sentence.",
                            user_prompt="Selected symbols: <comma-separated board labels, in the target locale>",
                            language_strings={"en": "English", "hi": "Hindi (Devanagari script)", "gu": "Gujarati (Gujarati script)", "mr": "Marathi (Devanagari script)"},
                            output_parsing="none (the full decoded string is scored)", failure_handling="none needed: 184+8 outputs recorded, no timeouts",
                            input_information="selected labels only (no intent, no negation field, no ledger)"),
    n=len(nv), success=sum(r["success"] for r in nv),
    overlapping_failure_flags={k: sum((not r[k]) if k in ("polarity_ok", "act_ok", "script_ok") else bool(r[k]) for r in nv) for k in ("act_missing", "act_wrong", "unsupported", "offtask", "polarity_ok", "script_ok")},
    concept_retention_full=sum(r["retention"] == 1.0 for r in nv),
    fail_only_because_no_act_marker=len(no_act_only),
    note="'success' requires an explicit request/feeling marker; a telegraphic or descriptive output ('Water is a liquid.') fails on act_missing even when concepts and polarity are right.")
(OUT / "A4_naive_baseline.json").write_text(json.dumps(A4, ensure_ascii=False, indent=1), encoding="utf-8")
write_csv(OUT / "A4_naive_outputs.csv", [dict(id=r["id"], lang=r["lang"], family=r["type"], text=r["text"], success=r["success"], act_missing=r["act_missing"], act_wrong=r["act_wrong"],
                                              unsupported=r["unsupported"], offtask=r["offtask"], script_ok=r["script_ok"], polarity_ok=r["polarity_ok"], retention=r["retention"]) for r in nv])

# ------------------------------------------------------------------ A6: the "27 of 32" browser diagnostic denominator
ui = json.loads((ARCH / "results/ui_audit.json").read_text(encoding="utf-8"))
feel = [r for r in ui["rows"] if r["category"] == "feelings"]
A6 = dict(denominator="single-symbol selections: 8 feeling symbols x 4 locales = 32 (NOT scenarios, NOT the 175)", n_feeling_selections=len(feel),
          n_sent_as_REQUEST=sum(r["ui_intent"] == "REQUEST" for r in feel), n_sent_as_STATEMENT=sum(r["ui_intent"] == "STATEMENT" for r in feel),
          statement_cases=[(r["id"], r["lang"], r["label"]) for r in feel if r["ui_intent"] == "STATEMENT"],
          n_single_selections_all_categories=len(ui["rows"]), n_false_negation=ui["summary"]["n_false_negation"],
          false_negation_cases=ui["summary"]["false_negation"],
          note="the client marks a selection negated when the joined lower-cased label string CONTAINS 'no','not','नहीं','ના','नाही' as a substring")
(OUT / "A6_feeling_denominator.json").write_text(json.dumps(A6, ensure_ascii=False, indent=1), encoding="utf-8")

# ------------------------------------------------------------------ A7: paired intervals -- (a) replay of the archived call order, (b) new seed, (c) group-level pooled
def pairs(a, b, lang):
    A = {r["id"]: r for r in rows if r["system"] == a[0] and r["cond"] == a[1] and r["lang"] == lang and not r["code_mix"] and not r["overlap"]}
    B = {r["id"]: r for r in rows if r["system"] == b[0] and r["cond"] == b[1] and r["lang"] == lang and not r["code_mix"] and not r["overlap"]}
    ids = sorted(set(A) & set(B))
    return ids, np.array([float(A[i]["success"]) for i in ids]), np.array([float(B[i]["success"]) for i in ids])


COMP = [(("deployed", "ui"), ("literal_join", "any")), (("deployed", "ui"), ("naive_qwen", "ui")), (("deployed", "ui"), ("template_only", "ui")), (("deployed", "ui"), ("llm3_pre", "ui")),
        (("deployed", "st"), ("deployed", "ui")), (("deployed", "st"), ("template_only", "st")), (("deployed", "st"), ("llm3_pre", "st")), (("llm1", "ui"), ("llm3_pre", "ui"))]
rng = np.random.default_rng(BOOT_SEED)           # archived: ONE generator shared by all calls, in this order
replay, matches = {}, 0
for a, b in COMP:
    for lang in LANGS:
        ids, x, y = pairs(a, b, lang); d = x - y; n = len(d)
        bs = d[rng.integers(0, n, size=(BOOT_N, n))].mean(1)
        key = f"{a[0]}|{a[1]} - {b[0]}|{b[1]} [{lang}]"
        mine = dict(n=n, diff=round(float(d.mean()), 4), ci95=[round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)])
        rep = archived_summary["paired_success"][key]
        ok = (mine["diff"] == rep["diff"] and mine["ci95"] == rep["ci95"] and n == rep["n"])
        matches += ok
        replay[key] = dict(recomputed=mine, reported=dict(n=rep["n"], diff=rep["diff"], ci95=rep["ci95"]), identical=ok)
rng2 = np.random.default_rng(BOOT_SEED_V2)       # new: independent generator per comparison, group-level pooled CI
group_of = lambda i: i.split("-", 1)[1]           # drop the language prefix: the same concept grid is translated into the 4 locales
pooled = {}
for a, b in COMP:
    key = f"{a[0]}|{a[1]} - {b[0]}|{b[1]}"
    cells = collections.defaultdict(list)
    for lang in LANGS:
        ids, x, y = pairs(a, b, lang)
        for i, xi, yi in zip(ids, x, y):
            cells[group_of(i)].append(xi - yi)
    groups = sorted(cells); tot = np.array([sum(cells[g]) for g in groups]); cnt = np.array([len(cells[g]) for g in groups])
    idx = np.random.default_rng(BOOT_SEED_V2).integers(0, len(groups), size=(BOOT_N, len(groups)))
    bs = tot[idx].sum(1) / cnt[idx].sum(1)
    pooled[key] = dict(n_items=int(cnt.sum()), n_groups=len(groups), diff_pp=round(100 * float(tot.sum() / cnt.sum()), 2),
                       ci95_pp=[round(100 * float(np.percentile(bs, 2.5)), 2), round(100 * float(np.percentile(bs, 97.5)), 2)], unit="semantic scenario group (same grid cell across the 4 locales)")
A7 = dict(replay_of_archived_procedure=dict(n_comparisons=len(replay), n_identical=int(matches), detail=replay), pooled_group_level_new_seed=pooled,
          bootstrap=dict(archived_seed=BOOT_SEED, new_seed=BOOT_SEED_V2, resamples=BOOT_N))
(OUT / "A7_paired_ci_recomputed.json").write_text(json.dumps(A7, ensure_ascii=False, indent=1), encoding="utf-8")

print("rows re-scored:", len(rows), "| mismatches vs archived scored.csv:", len(mism))
print("overlap flag matches archived:", A1["overlap_flag_matches_archived"], "| excluded:", len(overlap_log))
print("claims check:", sum(1 for a, b, c in claims if b == c), "/", len(claims), "match")
for a, b, c in claims:
    if b != c:
        print("  MISMATCH:", a, "| manuscript", b, "| recomputed", c)
print("template-only failures by lang:", cohorts["template_only_failures_by_language"], "| by family:", cohorts["template_only_failures_by_family"])
print("cohorts:", {k: v for k, v in cohorts.items() if k in ("accepted_model", "template_fallback", "template_only")})
print("archived bootstrap replay identical:", matches, "/", len(replay))
