#!/usr/bin/env python3
"""Score every system on the frozen scenarios and regenerate the paper's numbers.

Systems (all scored by score.py, which shares no code with the backend validator):
  literal_join            labels joined by spaces (no processing)
  template_only_{ui,st}   backend deterministic template (llm.generate_deterministic_fallback) on the same payload, no LLM
  naive_qwen              single-pass prompted Qwen2.5-0.5B, no ledger / few-shot / validator (run_naive.py)
  llm1 / llm2 / llm3_pre  the deployed cascade's stage outputs BEFORE the validator (from the same /generate response)
  deployed                final text returned by POST /generate (validator + template fallback applied)
Payload conditions: ui (what the deployed web client sends) and st (explicit-polarity structured payload).
Primary set = scenarios whose prompt does NOT reproduce a few-shot example of llm.py for either payload (overlap flagged by parsing llm.py).
Uncertainty: paired bootstrap over scenarios (10,000 resamples, seed in config.json)."""
import ast, json, sys, hashlib, pathlib, statistics, csv, collections
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import score as S
CFG = json.loads((HERE / "config.json").read_text())
RES = HERE / "results"; GEN = HERE.parent / "generated"; GEN.mkdir(exist_ok=True)

def key(p): return hashlib.sha256(json.dumps(p, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
def load_jsonl(p): return [json.loads(l) for l in pathlib.Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]

scs = load_jsonl(HERE / CFG["scenarios"])
raw = {r["key"]: r for r in load_jsonl(RES / "raw_pipeline.jsonl")}
naive = {r["id"]: r for r in load_jsonl(RES / "raw_naive.jsonl")} if (RES / "raw_naive.jsonl").exists() else {}

# ---------- few-shot overlap, parsed from backend/llm.py (no model import) ----------
src = (ROOT / "indic-generative-aac/backend/llm.py").read_text(encoding="utf-8")
tree = ast.parse(src)
fs = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "FEW_SHOT" for t in node.targets):
        fs = ast.literal_eval(node.value)
EX_IN = {lang: {ex[0] for ex in cfg["examples"]} for lang, cfg in fs.items()}

def build_q(lang, intent, negation, entities):
    """Re-implementation of the query string built in llm._llm1_realize for hi/gu/mr (few-shot path)."""
    I = intent.upper(); ent = entities
    if lang == "hi":
        pre = "नहीं चाहिए" if negation else ("मुझे चाहिए" if I in ["REQUEST", "WANT"] else ("मैं कह रहा हूँ" if I in ["STATEMENT", "FEEL"] else "क्या मुझे मिल सकता है"))
        return "Input Sequence: " + " + ".join([pre] + ent if ent else [pre, "यह"])
    if lang == "gu":
        pre = "નથી જોઈતું" if negation else ("મને જોઈએ છે" if I in ["REQUEST", "WANT"] else ("હું કહું છું" if I in ["STATEMENT", "FEEL"] else "શું મને મળી શકે"))
        return "ઈનપુટ ક્રમ: " + " + ".join([pre] + ent if ent else [pre, "આ"])
    if lang == "mr":
        pre = "नको आहे" if negation else ("मला हवे आहे" if I in ["REQUEST", "WANT"] else ("मी सांगत आहे" if I in ["STATEMENT", "FEEL"] else "मला मिळू शकेल का"))
        return "इनपुट क्रम: " + " + ".join([pre] + ent if ent else [pre, "हे"])
    return None

def api_negation(p):  # app.py: negation = req.negation or intent == 'NEGATION' or 'NOT' in intent
    return bool(p["negation"]) or p["intent"].upper() == "NEGATION" or "NOT" in p["intent"].upper()

def overlap(sc, cond):
    p = sc["payload_" + cond]
    if p["code_mix"] or p["language"] not in EX_IN: return False
    return build_q(p["language"], p["intent"], api_negation(p), p["entities"]) in EX_IN[p["language"]]

# ---------- template-only baseline (backend function without model load) ----------
sys.path.insert(0, str(ROOT / "indic-generative-aac/backend"))
from llm import IndicLLM  # noqa: E402  (imports torch/transformers, does NOT load weights)
def template(p):
    ctx = dict(intent=p["intent"], actor="USER", entities=p["entities"], negation=api_negation(p))
    return IndicLLM.generate_deterministic_fallback(None, ctx, language=p["language"], code_mix=p["code_mix"])

# ---------- collect outputs ----------
rows = []  # one per (scenario, system, condition)
def add(sc, system, cond, text, extra=None):
    r = dict(id=sc["id"], lang=sc["lang"], code_mix=sc["code_mix"], type=sc["type"], system=system, cond=cond, text=text,
             overlap=sc["overlap_any"], missing=(text is None))
    if text is None:
        r.update(retention=0.0, n_concepts=len(sc["content_concepts"]), n_present=0, polarity_ok=False, polarity_drop=sc["gold_neg"], polarity_spur=False,
                 act_ok=False, act_wrong=False, act_missing=True, unsupported=False, unsupported_hits=[], offtask=True, script_ok=False, success=False)
    else:
        r.update(S.score(sc, text))
    r.update(extra or {})
    rows.append(r)

for sc in scs:
    sc["overlap_ui"], sc["overlap_st"] = overlap(sc, "ui"), overlap(sc, "structured")
    sc["overlap_any"] = sc["overlap_ui"] or sc["overlap_st"]
    add(sc, "literal_join", "any", " ".join(sc["labels"]))
    nv = naive.get(sc["id"])
    add(sc, "naive_qwen", "ui", nv["text"] if nv else None)
    for cond, tag in (("ui", "ui"), ("structured", "st")):
        p = sc["payload_" + cond]
        add(sc, "template_only", tag, template(p))
        rec = raw.get(key(p))
        resp = rec.get("response") if rec else None
        for stage, fld in (("llm1", "candidate_llm1"), ("llm2", "candidate_llm2"), ("llm3_pre", "llm3_final_text"), ("deployed", "text")):
            txt = resp.get(fld) if resp else None
            ex = {}
            if stage == "deployed":
                ex = dict(fallback=bool(resp and resp.get("fallback_used")), validated=bool(resp and resp.get("validated")),
                          wall_s=rec["wall_s"] if rec else None, t_total=(resp or {}).get("metrics", {}).get("t_total") if resp else None,
                          error=(rec or {}).get("error") if rec else "no request recorded")
            add(sc, stage, tag, txt, ex)

# ---------- aggregation ----------
FLAGS = ["success", "polarity_ok", "act_ok", "act_wrong", "act_missing", "unsupported", "offtask", "script_ok", "polarity_drop", "polarity_spur"]
def agg(rs):
    n = len(rs); c = sum(r["n_concepts"] for r in rs); k = sum(r["n_present"] for r in rs)
    o = dict(n=n, concept_instances=c, concepts_present=k, retention=k / c if c else None, retention_full=sum(r["retention"] == 1.0 for r in rs))
    for f in FLAGS: o[f] = sum(bool(r[f]) for r in rs)
    o["n_missing_output"] = sum(r["missing"] for r in rs)
    return o

def select(system, cond, lang, primary=True, code_mix=False):
    return [r for r in rows if r["system"] == system and r["cond"] == cond and r["lang"] == lang and r["code_mix"] == code_mix and (not primary or not r["overlap"])]

SYSTEMS = [("literal_join", "any"), ("template_only", "ui"), ("template_only", "st"), ("naive_qwen", "ui"), ("llm1", "ui"), ("llm2", "ui"), ("llm3_pre", "ui"), ("deployed", "ui"),
           ("llm1", "st"), ("llm2", "st"), ("llm3_pre", "st"), ("deployed", "st")]
summary = dict(meta=dict(n_scenarios=len(scs), n_overlap_scenarios=sum(s["overlap_any"] for s in scs),
                         overlap_ids=[s["id"] for s in scs if s["overlap_any"]], scenarios_sha256=hashlib.sha256((HERE / CFG["scenarios"]).read_bytes()).hexdigest(),
                         lexicon_sha256=hashlib.sha256((HERE / "fixtures/lexicon.json").read_bytes()).hexdigest()), by_lang={}, all_items={})
for lang in ["en", "hi", "gu", "mr"]:
    summary["by_lang"][lang] = {f"{s}|{c}": agg(select(s, c, lang)) for s, c in SYSTEMS}
    summary["all_items"][lang] = {f"{s}|{c}": agg(select(s, c, lang, primary=False)) for s, c in SYSTEMS}
summary["code_mix_exploratory"] = {f"{s}|{c}": agg(select(s, c, "hi", primary=False, code_mix=True)) for s, c in SYSTEMS}

# fallback / validation accounting for deployed
acc = {}
for cond in ("ui", "st"):
    for lang in ["en", "hi", "gu", "mr"]:
        rs = select("deployed", cond, lang, primary=False)
        acc[f"{cond}|{lang}"] = dict(n=len(rs), fallback=sum(bool(r.get("fallback")) for r in rs), validated=sum(bool(r.get("validated")) for r in rs),
                                     errors=sum(bool(r.get("error")) for r in rs))
summary["deployed_accounting"] = acc

# ---------- paired bootstrap on success (scenario = cluster) ----------
rng = np.random.default_rng(CFG["bootstrap"]["seed"]); B = CFG["bootstrap"]["resamples"]
def succ_vec(system, cond, lang, primary=True):
    d = {r["id"]: r for r in rows if r["system"] == system and r["cond"] == cond and r["lang"] == lang and not r["code_mix"] and (not primary or not r["overlap"])}
    return d
def paired(a, b, lang, primary=True, flag="success"):
    A = succ_vec(*a, lang, primary); Bv = succ_vec(*b, lang, primary)
    ids = sorted(set(A) & set(Bv))
    x = np.array([float(A[i][flag]) for i in ids]); y = np.array([float(Bv[i][flag]) for i in ids])
    d = x - y; n = len(d)
    idx = rng.integers(0, n, size=(B, n)); bs = d[idx].mean(1)
    both1 = int(((x == 1) & (y == 1)).sum()); a_only = int(((x == 1) & (y == 0)).sum()); b_only = int(((x == 0) & (y == 1)).sum())
    return dict(n=n, a=int(x.sum()), b=int(y.sum()), diff=round(float(d.mean()), 4), ci95=[round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                a_only=a_only, b_only=b_only, both=both1)
COMP = [(("deployed", "ui"), ("literal_join", "any")), (("deployed", "ui"), ("naive_qwen", "ui")), (("deployed", "ui"), ("template_only", "ui")),
        (("deployed", "ui"), ("llm3_pre", "ui")), (("deployed", "st"), ("deployed", "ui")), (("deployed", "st"), ("template_only", "st")), (("deployed", "st"), ("llm3_pre", "st")),
        (("llm1", "ui"), ("llm3_pre", "ui"))]
summary["paired_success"] = {}
for a, b in COMP:
    for lang in ["en", "hi", "gu", "mr"]:
        summary["paired_success"][f"{a[0]}|{a[1]} - {b[0]}|{b[1]} [{lang}]"] = paired(a, b, lang)

# ---------- latency ----------
def pct(v, q): return round(float(np.percentile(v, q)), 2) if v else None
lat = {}
# one observation per UNIQUE request payload (identical client/structured payloads are the same request and must not be counted twice)
uniq_req = [r for r in raw.values() if r.get("response") and not r["payload"]["code_mix"]]
for lang in ["en", "hi", "gu", "mr"]:
    for grp, f in (("all", lambda r: True), ("accepted", lambda r: not r["response"]["fallback_used"]), ("fallback", lambda r: r["response"]["fallback_used"])):
        v = [r["wall_s"] for r in uniq_req if r["payload"]["language"] == lang and f(r)]
        lat[f"{lang}|{grp}"] = dict(n=len(v), median=pct(v, 50), p90=pct(v, 90), max=round(max(v), 2) if v else None)
summary["latency_wall_s"] = lat
# stage breakdown from server telemetry
stage = collections.defaultdict(list)
for rec in raw.values():
    m = (rec.get("response") or {}).get("metrics")
    if m:
        for k in ("t_llm1", "t_llm2", "t_llm3", "t_sem", "t_tts", "t_total"): stage[k].append(m[k])
summary["latency_stage_medians_s"] = {k: dict(median=pct(v, 50), p90=pct(v, 90), n=len(v)) for k, v in stage.items()}

gp = {}
for cond in ("ui", "st"):
    c = collections.Counter()
    for r in rows:
        if r["system"] == "deployed" and r["cond"] == cond and not r["overlap"] and not r["code_mix"]:
            k = "fallback" if r.get("fallback") else "accepted"; c[k] += 1; c[k + "_success"] += int(bool(r["success"]))
    gp[cond] = dict(c)
summary["gate_precision"] = gp
(RES / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
with (RES / "scored.csv").open("w", newline="", encoding="utf-8") as f:
    cols = ["id", "lang", "code_mix", "type", "system", "cond", "overlap", "success", "retention", "polarity_ok", "act_ok", "act_wrong", "act_missing", "unsupported", "offtask", "script_ok", "fallback", "validated", "wall_s", "text", "unsupported_hits"]
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
    for r in rows: w.writerow({**r, "unsupported_hits": "|".join(r.get("unsupported_hits") or [])})
print("scenarios", len(scs), "| overlap scenarios", summary["meta"]["n_overlap_scenarios"], "| rows scored", len(rows))
print("deployed accounting:", json.dumps(acc))
