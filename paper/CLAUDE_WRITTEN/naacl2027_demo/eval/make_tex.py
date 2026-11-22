#!/usr/bin/env python3
"""Regenerate generated/numbers.tex and generated/tab_*.tex from eval/results/*.json. Every number in the manuscript comes from here."""
import json, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
RES = HERE / "results"; GEN = HERE.parent / "generated"; GEN.mkdir(exist_ok=True)
S = json.loads((RES / "summary.json").read_text(encoding="utf-8"))
P = json.loads((RES / "prediction.json").read_text(encoding="utf-8"))
R = json.loads((RES / "reliability_ui.json").read_text(encoding="utf-8")) if (RES / "reliability_ui.json").exists() else {}
U = json.loads((RES / "ui_audit.json").read_text(encoding="utf-8"))["summary"]
LANGS = ["en", "hi", "gu", "mr"]; LN = dict(en="EN", hi="HI", gu="GU", mr="MR")
M = []  # macro lines
def defm(name, val):
    val = str(val)
    if name.startswith("PredD"):
        val = "\\mbox{" + re.sub(r"(?<![\\\w])-(?=\d)", "\\\\ensuremath{-}", val) + "}"
    M.append("\\newcommand{\\%s}{%s}" % (name, val))
def pc(a, b, d=0): return f"{100*a/b:.{d}f}\\%" if b else "n/a"
def pp(x, d=0):
    v = f"{100*x:+.{d}f}"
    return ("\\ensuremath{-}" + v[1:]) if v.startswith("-") else v

# ---- set sizes ----
defm("NScen", S["meta"]["n_scenarios"] - 8); defm("NScenCM", 8)
defm("NOverlap", S["meta"]["n_overlap_scenarios"])
for l in LANGS:
    defm("NPrim" + LN[l], S["by_lang"][l]["deployed|ui"]["n"]); defm("NAll" + LN[l], S["all_items"][l]["deployed|ui"]["n"])
nprim = sum(S["by_lang"][l]["deployed|ui"]["n"] for l in LANGS); defm("NPrimAll", nprim)

def tot(sysk, f, src="by_lang"): return sum(S[src][l][sysk][f] for l in LANGS)
def totN(sysk, src="by_lang"): return sum(S[src][l][sysk]["n"] for l in LANGS)

# ---- combined results table (success per language | error decomposition, pooled primary set) ----
ROWS = [("literal_join|any", "Literal join"), ("template_only|ui", "Template only (client)"), ("naive_qwen|ui", "Prompted Qwen, no gate"),
        ("llm3_pre|ui", "Cascade before gate (client)"), ("deployed|ui", "\\textbf{Deployed (client)}"),
        ("template_only|st", "Template only (struct.)"), ("deployed|st", "\\textbf{Deployed (struct.)}")]
t = ["\\begin{table*}[t]\\centering\\footnotesize\\setlength{\\tabcolsep}{2.6pt}", "\\begin{tabular}{@{}p{3.5cm}ccccc@{\\hspace{8pt}}ccccc@{}}", "\\toprule",
     " & \\multicolumn{5}{c}{Scenario success (n/N)} & \\multicolumn{5}{c}{Pooled error decomposition (lower is better)} \\\\",
     "\\cmidrule(lr){2-6}\\cmidrule(lr){7-11}",
     "System & EN & HI & GU & MR & All & Kept & Polarity & Act & Added & Off-task \\\\", "\\midrule"]
for k, lab in ROWS:
    cells = [f"{S['by_lang'][l][k]['success']}/{S['by_lang'][l][k]['n']}" for l in LANGS]
    a_, n = tot(k, "success"), totN(k); c = tot(k, "concept_instances"); kept = tot(k, "concepts_present")
    wp = tot(k, "polarity_drop") + tot(k, "polarity_spur")
    errs = [f"{kept}/{c}", f"{wp}/{n}", f"{tot(k,'act_wrong')}/{n}", f"{tot(k,'unsupported')}/{n}", f"{tot(k,'offtask')}/{n}"]
    t.append(f"{lab} & " + " & ".join(cells) + f" & {a_}/{n} & " + " & ".join(errs) + " \\\\")
    if k in ("deployed|ui",): t.append("\\midrule")
t += ["\\bottomrule", "\\end{tabular}",
      f"\\caption{{Primary set ({nprim} scenarios; EN {S['by_lang']['en']['deployed|ui']['n']}, HI {S['by_lang']['hi']['deployed|ui']['n']}, GU {S['by_lang']['gu']['deployed|ui']['n']}, MR {S['by_lang']['mr']['deployed|ui']['n']}). Left: scenarios whose output keeps every selected concept, has the gold polarity and act, adds no unselected concept and is an on-task first-person sentence (independent lexical scorer). Right (pooled): required concept instances kept (of {tot('deployed|ui','concept_instances')}) and scenarios with a wrong polarity, wrong act, added concept or off-task output. Client = payload built by the web client; struct. = explicit intent and negation fields.}}",
      "\\label{tab:results}", "\\end{table*}"]
(GEN / "tab_results.tex").write_text("\n".join(t) + "\n", encoding="utf-8")
for old in ("tab_success.tex", "tab_errors.tex"):
    q = GEN / old
    if q.exists(): q.unlink()

# ---- prediction table (with the project's trained HMMs) ----
HE = json.loads((RES / "hmm_eval.json").read_text(encoding="utf-8")) if (RES / "hmm_eval.json").exists() else {}
def cell(d, k):
    return (f"{100*d[k]['hit1']['value']:.1f}", f"{100*d[k]['hit5']['value']:.1f}", f"{d[k]['mrr']['value']:.3f}") if d and k in d else ("--", "--", "--")
def prow(label, en_sys, hi_sys, en_key, hi_key):
    return label + " & " + " & ".join(cell(en_sys, en_key) + cell(hi_sys, hi_key)) + " \\\\"
en, hi = P["en"]["systems"], P["hi"]["systems"]
hen, hhi = (HE.get("en", {}).get("systems") or {}), (HE.get("hi", {}).get("systems") or {})
t = ["\\begin{table}[H]\\centering\\scriptsize\\setlength{\\tabcolsep}{2.4pt}", "\\begin{tabular}{@{}lcccccc@{}}", "\\toprule",
     " & \\multicolumn{3}{c}{English} & \\multicolumn{3}{c}{Hindi} \\\\", "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}", "Model & hit@1 & hit@5 & MRR & hit@1 & hit@5 & MRR \\\\", "\\midrule",
     prow("Unigram frequency", en, hi, "unigram_frequency", "unigram_frequency"), prow("Bigram, backoff", en, hi, "bigram_backoff", "bigram_backoff"),
     prow("Trigram, backoff", en, hi, "trigram_backoff", "trigram_backoff"),
     prow("Gutenberg HMM$^{\\ast}$", hen, {}, "gutenberg_hmm_english", "-"), prow("Hindi AAC HMM$^{\\ast}$", {}, hhi, "-", "hindi_hmm_retrained")]
if "hmm1_dual_kit_4gram" in hen: t.append(prow("HMM-1, 4-gram$^{\\ast}$", hen, {}, "hmm1_dual_kit_4gram", "-"))
else: t.append("HMM-1, 4-gram & n/a$^{\\dagger}$ & n/a & n/a & -- & -- & -- \\\\")
t += ["\\midrule", prow("\\textbf{Infinity-gram}", en, hi, "infinity_gram_deployed", "infinity_gram_deployed"), "\\bottomrule", "\\end{tabular}",
      f"\\caption{{Held-out next-word prediction (hit@$k$ in \\%, MRR@10) on AAC-user utterances of {P['en']['n_clusters']} held-out source conversations per language ({P['en']['n_items']} English and {P['hi']['n_items']} Hindi contexts). Training and test sources are disjoint. $^{{\\ast}}$Trained HMM scored with the deployed Markov rule; the Hindi HMM is retrained on the training sources with the project's script (the shipped file saw all sources). $^{{\\dagger}}$Git LFS object not available during evaluation.}}",
      "\\label{tab:pred}", "\\end{table}"]
(GEN / "tab_pred.tex").write_text("\n".join(t) + "\n", encoding="utf-8")

# ---- macros: paired differences, fallback, latency, prediction, audits ----
CMP = dict(DN=("deployed|ui", "naive_qwen|ui"), DT=("deployed|ui", "template_only|ui"), DP=("deployed|ui", "llm3_pre|ui"),
           SU=("deployed|st", "deployed|ui"), ST=("deployed|st", "template_only|st"), SP=("deployed|st", "llm3_pre|st"), LL=("llm1|ui", "llm3_pre|ui"))
for tag, (a, b) in CMP.items():
    for l in LANGS:
        key = f"{a.split('|')[0]}|{a.split('|')[1]} - {b.split('|')[0]}|{b.split('|')[1]} [{l}]"
        r = S["paired_success"].get(key)
        if r: defm(f"P{tag}{LN[l]}", "\\mbox{" + f"{pp(r['diff'])}\\,pp [{pp(r['ci95'][0])}, {pp(r['ci95'][1])}]" + "}"); defm(f"C{tag}{LN[l]}", f"{r['a']}/{r['n']}\\,vs\\,{r['b']}/{r['n']}")
for cond, tag in (("ui", "U"), ("st", "S")):
    f = sum(S["deployed_accounting"][f"{cond}|{l}"]["fallback"] for l in LANGS); n = sum(S["deployed_accounting"][f"{cond}|{l}"]["n"] for l in LANGS)
    defm(f"FB{tag}All", f"{f}/{n}")
    for l in LANGS:
        a = S["deployed_accounting"][f"{cond}|{l}"]; defm(f"FB{tag}{LN[l]}", f"{a['fallback']}/{a['n']}"); defm(f"FBpct{tag}{LN[l]}", pc(a["fallback"], a["n"]))
        defm(f"Err{tag}{LN[l]}", a["errors"])
L = S["latency_wall_s"]
for l in LANGS:
    for g in ("all", "accepted", "fallback"):
        d = L[f"{l}|{g}"]; defm(f"Lat{g.capitalize()}{LN[l]}", f"{d['median']}\\,s (p90 {d['p90']}, n={d['n']})")
for l in LANGS:
    defm(f"LatMedAcc{LN[l]}", L[f"{l}|accepted"]["median"]); defm(f"LatMedFb{LN[l]}", L[f"{l}|fallback"]["median"])
defm("LatFbMin", min(L[f"{l}|fallback"]["median"] for l in LANGS)); defm("LatFbMax", max(L[f"{l}|fallback"]["median"] for l in LANGS))
defm("NUniqueReq", sum(L[f"{l}|all"]["n"] for l in LANGS))
st = S["latency_stage_medians_s"]
NM = {"t_llm1": "StageLlmOne", "t_llm2": "StageLlmTwo", "t_llm3": "StageLlmThree", "t_sem": "StageSem", "t_tts": "StageTts", "t_total": "StageTotal"}
for k, v in st.items(): defm(NM[k], f"{v['median']}")
for l in ("en", "hi"):
    d = P[l]; g = d["systems"]["infinity_gram_deployed"]; tg = d["systems"]["trigram_backoff"]; bg = d["systems"]["bigram_backoff"]; ug = d["systems"]["unigram_frequency"]
    for m, mn in (("hit1", "One"), ("hit5", "Five")):
        defm(f"Pred{LN[l]}{mn}Inf", f"{100*g[m]['value']:.1f}"); defm(f"Pred{LN[l]}{mn}Tri", f"{100*tg[m]['value']:.1f}")
    pv = d["paired_vs_infinity_gram"]
    for nm, tag in (("trigram_backoff", "Tri"), ("bigram_backoff", "Bi"), ("unigram_frequency", "Uni")):
        for m, mn in (("hit1", "One"), ("hit5", "Five"), ("mrr", "Mrr")):
            r = pv[nm][m]; sc = 1 if m == "mrr" else 100
            defm(f"PredD{LN[l]}{mn}{tag}", (f"{r['diff']*sc:+.3f}" if m == "mrr" else f"{r['diff']*sc:+.1f}") + f" [{r['ci95'][0]*sc:+.3f}, {r['ci95'][1]*sc:+.3f}]" if m == "mrr" else f"{r['diff']*sc:+.1f}\\,pp [{r['ci95'][0]*sc:+.1f}, {r['ci95'][1]*sc:+.1f}]")
    defm(f"PredN{LN[l]}", d["n_items"]); defm(f"PredClusters{LN[l]}", d["n_clusters"]); defm(f"PredOOV{LN[l]}", f"{100*d['oov_target_rate']:.1f}\\%")
defm("UIFalseNeg", U["n_false_negation"]); defm("UISingle", U["n_single_selections"]); defm("UIFeelReq", U["n_feelings_sent_as_REQUEST"])

GP = S["gate_precision"]
for cond, tg in (("ui", "U"), ("st", "S")):
    g = GP[cond]; defm(f"GateAcc{tg}", f"{g['accepted']}"); defm(f"GateAccOk{tg}", f"{g['accepted_success']}"); defm(f"GateAccPct{tg}", pc(g['accepted_success'], g['accepted']))
    defm(f"GateFb{tg}", f"{g['fallback']}"); defm(f"GateFbOk{tg}", f"{g['fallback_success']}"); defm(f"GateFbPct{tg}", pc(g['fallback_success'], g['fallback']))
CM = S["code_mix_exploratory"]
for key, nm in (("naive_qwen|ui", "Naive"), ("llm3_pre|ui", "Pre"), ("deployed|ui", "DepU"), ("deployed|st", "DepS"), ("template_only|ui", "TmplU"), ("template_only|st", "TmplS")):
    defm(f"CMSucc{nm}", f"{CM[key]['success']}/{CM[key]['n']}")
for l in LANGS:
    for key, nm in (("deployed|ui", "U"), ("deployed|st", "S")):
        d = S["by_lang"][l][key]; defm(f"ActWrong{nm}{LN[l]}", f"{d['act_wrong']}/{d['n']}"); defm(f"SuccEff{nm}{LN[l]}", f"{d['success']}/{d['n']}")
_he = json.loads((RES / "hmm_eval.json").read_text(encoding="utf-8"))
defm("GutHitOne", f"{100*_he['en']['systems']['gutenberg_hmm_english']['hit1']['value']:.1f}"); defm("HiHmmHitOne", f"{100*_he['hi']['systems']['hindi_hmm_retrained']['hit1']['value']:.1f}")
# ---- exact binomial bounds, refiner, HMM stats, offline ----
def cp_upper0(n): return 100 * (1 - 0.025 ** (1 / n))      # 95% two-sided Clopper-Pearson upper bound for 0/n
def cp_lower_all(n): return 100 * (0.025 ** (1 / n))       # lower bound for n/n
nP = nprim; cI = tot("deployed|ui", "concept_instances")
defm("CPzeroPol", f"{cp_upper0(nP):.1f}\\%"); defm("CPallConcept", f"{cp_lower_all(cI):.1f}\\%")
for key, nm in (("naive_qwen|ui", "Naive"), ("llm3_pre|ui", "Pre"), ("deployed|ui", "DepU"), ("deployed|st", "DepS"), ("template_only|st", "TmplS"), ("template_only|ui", "TmplU"), ("literal_join|any", "Lit")):
    n = totN(key); c = tot(key, "concept_instances"); k = tot(key, "concepts_present")
    defm(f"Succ{nm}", f"{tot(key,'success')}/{n}"); defm(f"SuccPct{nm}", pc(tot(key, "success"), n)); defm(f"Kept{nm}", f"{k}/{c}"); defm(f"KeptPct{nm}", pc(k, c))
    defm(f"PolErr{nm}", f"{tot(key,'polarity_drop')+tot(key,'polarity_spur')}/{n}"); defm(f"ActWrong{nm}", f"{tot(key,'act_wrong')}/{n}")
    defm(f"Added{nm}", f"{tot(key,'unsupported')}/{n}"); defm(f"Off{nm}", f"{tot(key,'offtask')}/{n}")
RF = json.loads((RES / "refiner_repro.json").read_text(encoding="utf-8"))
for arm, nm in (("aac_only", "A"), ("fluency_then_aac", "F")):
    for m, mn in (("rules", "Rules"), ("model", "Model"), ("hybrid", "Hybrid"), ("raw", "Raw")):
        d = RF[arm][m]; defm(f"Ref{nm}{mn}", f"{d['exact_match']}/{d['n']}"); defm(f"Ref{nm}{mn}Pct", f"{100*d['exact_match']/d['n']:.1f}\\%")
    defm(f"Ref{nm}Lat", RF[arm]["model"]["median_latency_ms_model_calls"])
env = json.loads((RES / "env.json").read_text(encoding="utf-8")); st = env["backend_health"]["infinity_gram_stats"]
defm("IGSent", f"{st['sentence_count']:,}".replace(",", "{,}")); defm("IGTok", f"{st['total_tokens']:,}".replace(",", "{,}")); defm("IGDepth", st["max_depth_seen"])
OF = json.loads((RES / "offline_summary.json").read_text(encoding="utf-8"))
defm("OffReady", OF["time_to_ready_s"]); defm("OffFirstEn", OF["first_generate_en_s"]); defm("OffHi", OF["generate_hi_s"])
KB = json.loads((HERE / "fixtures/board_vocab.json").read_text(encoding="utf-8"))["meta"]; defm("NSymbols", KB["n_symbols"]); defm("NCategories", KB["n_categories"])

(GEN / "numbers.tex").write_text("% AUTO-GENERATED by eval/make_tex.py from eval/results/*.json -- do not edit\n" + "\n".join(M) + "\n", encoding="utf-8")
print(len(M), "macros;", "tables written:", [p.name for p in sorted(GEN.glob("tab_*.tex"))])
