#!/usr/bin/env python3
"""Analysis command.  Reads fixtures, captured payloads, saved streams and one-pass outputs; replays every system; scores with scorer v2
(scorer v1 columns are kept for the archived comparison); writes per-row traces and the paired tables.
Aggregation: per-scenario value = mean over the applicable seeds (English only; Indic paths are greedy); pooled rate = mean over scenarios;
paired difference = mean over scenarios of (A - B) in percentage points; bootstrap = 10,000 resamples of SCENARIO GROUPS (the four language
versions of one message share a group), seed 20261113; all compared systems and seeds stay together inside a resampled group.
Usage: python analyze_v2.py --split holdout|dev|legacy"""
import argparse, collections, csv, itertools, json, sys
import numpy as np
from common import *
import replay as R, score_v2 as S2

SEEDS_EN = [11, 23, 47]
EXCLUDE = set()                       # legacy: the nine scenarios whose input reproduces a few-shot example (Phase A, A2)
SYSTEM_ORDER = ["archived_deployed", "archived_llm1_stage", "revised_llm1_stage", "cascade_ungated_first", "cascade_ungated_last", "gate_only_v1", "revised_cascade_first", "revised_cascade_last",
                "revised_hybrid", "template_archived", "template_revised", "onepass"]
FLAGS = ["polarity_drop", "polarity_spur", "polarity_scope", "act_wrong", "act_missing", "unsupported", "third_person", "script_ok", "offtask", "latin_leak"]


def seeds_for(split):
    return [11] if split == "legacy" else SEEDS_EN


def build_rows(split):
    scs = jl(V2 / "fixtures" / split / "scenarios.jsonl")
    caps = {m: {r["id"]: r for r in jl(V2 / "results/payloads" / f"{('original' if m == 'orig' else 'revised')}_{split}.jsonl")} for m in ("orig", "rev")}
    streams, onepass = R.load_streams(split), R.load_onepass(split)
    out = []
    for sc in scs:
        if sc.get("code_mix") and split == "legacy":
            pass
        for system, mode, sd, res in R.systems_for(sc, caps, streams, onepass, seeds_for(split)):
            det = sc["expected_outcome"] == "sentence"
            oc = res["outcome"]
            row = dict(id=sc["id"], group=sc["group"], family=sc["family"], lang=sc["lang"], code_mix=sc.get("code_mix", False), split=split, mode=mode, system=system,
                       seed=sd, stage=res.get("stage", "final"), expected_outcome=sc["expected_outcome"], template_covered=sc["template_covered"], gold_act=sc["gold_act"],
                       gold_neg=sc["gold_neg"], outcome=oc, route=res.get("route"), attempts=res.get("attempts"), text=res.get("text"),
                       gate_reasons="|".join(res.get("reasons") or []), scorer="scorer-v2", assumed_retry=res.get("assumed", False))
            if oc.startswith("sentence") and res.get("text") is not None:
                f = S2.score(R.scorer_sc(sc), res["text"])
                row.update(retention=f["retention"], n_concepts=f["n_concepts"], n_present=f["n_present"], success=int(f["success"] and det),
                           **{k: int(bool(f[k])) for k in FLAGS if k != "script_ok"}, script_err=int(not f["script_ok"]))
            else:
                row.update(retention=None, n_concepts=None, n_present=None, success=0, **{k: None for k in FLAGS if k != "script_ok"}, script_err=None)
            row["missing_output"] = int(res.get("text") is None and oc.startswith("sentence"))
            row["clarification_appropriate"] = int(oc == "clarification") if not det else None
            out.append(row)
    if split == "legacy":
        arch = archived_rows(scs)
        have = {(r["system"], r["mode"]) for r in arch}
        out = [r for r in out if (r["system"], r["mode"]) not in have]        # saved archived outputs win over a recomputation (no duplicate keys)
        out += arch
    return out


ARCH_MAP = {("deployed", "ui"): ("archived_deployed", "orig"), ("deployed", "st"): ("archived_deployed", "gold"), ("llm3_pre", "ui"): ("cascade_ungated_first", "orig"),
            ("llm3_pre", "st"): ("cascade_ungated_first", "gold"), ("llm1", "ui"): ("archived_llm1_stage", "orig"), ("llm1", "st"): ("archived_llm1_stage", "gold"),
            ("template_only", "ui"): ("template_archived", "orig"), ("template_only", "st"): ("template_archived", "gold"), ("naive_qwen", "ui"): ("archived_unconstrained_prompt", "orig")}


def archived_rows(scs):
    """ARCHIVED saved outputs (original run: GTX 1650, one sample per payload) scored with scorer v2, so archived and revised systems share one scorer."""
    by = {r["id"]: r for r in scs}
    rows = []
    for r in csv.DictReader(open(ARCH / "results/scored.csv", encoding="utf-8")):
        k = ARCH_MAP.get((r["system"], r["cond"]))
        sc = by.get(r["id"])
        if not k or not sc: continue
        f = S2.score(R.scorer_sc(sc), r["text"]); det = sc["expected_outcome"] == "sentence"
        rows.append(dict(id=sc["id"], group=sc["group"], family=sc["family"], lang=sc["lang"], code_mix=sc.get("code_mix", False), split="legacy", mode=k[1], system=k[0], seed=None,
                         stage=("llm1" if k[0] == "archived_llm1_stage" else "final"), expected_outcome=sc["expected_outcome"], template_covered=sc["template_covered"], gold_act=sc["gold_act"],
                         gold_neg=sc["gold_neg"], outcome="sentence_ungated" if k[0] != "archived_deployed" else "sentence", route="archived_saved_output", attempts=None, text=r["text"], gate_reasons="",
                         scorer="scorer-v2", assumed_retry=False, retention=f["retention"], n_concepts=f["n_concepts"], n_present=f["n_present"], success=int(f["success"] and det),
                         **{k2: int(bool(f[k2])) for k2 in FLAGS if k2 != "script_ok"}, script_err=int(not f["script_ok"]), missing_output=0, clarification_appropriate=None,
                         prompt_overlap=sc["id"] in EXCLUDE))
    return rows


def items(rows, system, mode, lang=None, determinate=True, field="success"):
    """per-scenario mean over seeds -> {scenario_id: (group, value)}"""
    acc = collections.defaultdict(list); grp = {}
    for r in rows:
        if r["system"] != system or r["mode"] != mode or r["code_mix"]: continue
        if lang and r["lang"] != lang: continue
        if r["id"] in EXCLUDE: continue
        if determinate and r["expected_outcome"] != "sentence": continue
        v = r[field]
        if v is None: v = 0 if field == "success" else None
        if v is None: continue
        acc[r["id"]].append(v); grp[r["id"]] = r["group"]
    return {i: (grp[i], float(np.mean(v))) for i, v in acc.items()}


def boot_diff(a, b, n=BOOT_N, seed=BOOT_SEED_V2):
    ids = sorted(set(a) & set(b))
    if not ids: return None
    groups = sorted({a[i][0] for i in ids}); gi = {g: k for k, g in enumerate(groups)}
    S, N = np.zeros(len(groups)), np.zeros(len(groups))
    for i in ids:
        k = gi[a[i][0]]; S[k] += a[i][1] - b[i][1]; N[k] += 1
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(groups), size=(n, len(groups)))
    m = S[idx].sum(1) / np.maximum(N[idx].sum(1), 1)
    return dict(n_items=len(ids), n_groups=len(groups), diff_pp=round(100 * S.sum() / N.sum(), 2), lo=round(100 * np.percentile(m, 2.5), 2), hi=round(100 * np.percentile(m, 97.5), 2),
                n_a_only_wins=sum(a[i][1] > b[i][1] for i in ids), n_b_only_wins=sum(b[i][1] > a[i][1] for i in ids))


def boot_rate(a, n=BOOT_N, seed=BOOT_SEED_V2):
    ids = sorted(a); groups = sorted({a[i][0] for i in ids}); gi = {g: k for k, g in enumerate(groups)}
    S, N = np.zeros(len(groups)), np.zeros(len(groups))
    for i in ids: S[gi[a[i][0]]] += a[i][1]; N[gi[a[i][0]]] += 1
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(groups), size=(n, len(groups)))
    m = S[idx].sum(1) / np.maximum(N[idx].sum(1), 1)
    return round(100 * S.sum() / N.sum(), 1), round(100 * np.percentile(m, 2.5), 1), round(100 * np.percentile(m, 97.5), 1)


COMPARISONS = [   # (A, mode A, B, mode B, label)
    ("revised_hybrid", "rev", "archived_deployed", "orig", "end-to-end: revised hybrid (browser) vs archived system (browser)"),
    ("revised_hybrid", "gold", "archived_deployed", "gold", "end-to-end, explicit gold fields: revised hybrid vs archived system"),
    ("revised_hybrid", "rev", "revised_cascade_first", "rev", "gate effect: revised hybrid vs same generator without gate/fallback (first candidate)"),
    ("revised_hybrid", "gold", "revised_cascade_first", "gold", "gate effect, gold fields"),
    ("archived_deployed", "orig", "cascade_ungated_first", "orig", "gate effect, archived system (browser): deployed vs ungated first candidate"),
    ("archived_deployed", "gold", "cascade_ungated_first", "gold", "gate effect, archived system (gold): deployed vs ungated first candidate"),
    ("gate_only_v1", "gold", "archived_deployed", "gold", "pure gate change V0 -> V1 on identical archived candidates (gold fields)"),
    ("gate_only_v1", "orig", "archived_deployed", "orig", "pure gate change V0 -> V1 on identical archived candidates (browser)"),
    ("revised_hybrid", "rev", "onepass", "rev", "revised hybrid vs matched one-pass prompt (browser fields)"),
    ("revised_hybrid", "gold", "onepass", "gold", "revised hybrid vs matched one-pass prompt (gold fields)"),
    ("revised_hybrid", "rev", "revised_llm1_stage", "rev", "revised hybrid vs the few-shot realiser alone (LLM-1 stage, no refiner / verifier / gate)"),
    ("revised_hybrid", "rev", "template_revised", "rev", "revised hybrid vs repaired template alone (browser)"),
    ("revised_hybrid", "gold", "template_revised", "gold", "revised hybrid vs repaired template alone (gold)"),
    ("template_revised", "rev", "template_archived", "orig", "repaired template (revised client) vs archived template (original client)"),
    ("template_revised", "gold", "template_archived", "gold", "repaired template vs archived template (gold fields)"),
    ("revised_hybrid", "rev", "revised_hybrid", "gold", "interface effect: revised-browser vs explicit gold fields (hybrid)"),
    ("revised_hybrid", "cross", "revised_hybrid", "rev", "interface effect: same realiser, original-client payload vs revised-client payload"),
    ("template_revised", "rev", "template_revised", "gold", "interface effect on the template"),
]


def tables(rows, split, out):
    out.mkdir(parents=True, exist_ok=True)
    present = sorted({(r["system"], r["mode"]) for r in rows if not r["code_mix"]}, key=lambda x: (SYSTEM_ORDER.index(x[0]) if x[0] in SYSTEM_ORDER else 99, x[1]))
    # --- T1 success rates
    t1 = []
    for system, mode in present:
        rec = dict(system=system, mode=mode)
        for lang in LANGS + [None]:
            it = items(rows, system, mode, lang)
            if not it: continue
            rate, lo, hi = boot_rate(it) if len(it) > 1 else (round(100 * list(it.values())[0][1], 1), None, None)
            tag = lang or "ALL"
            rec[f"{tag}_n"] = len(it); rec[f"{tag}_k"] = round(sum(v for _, v in it.values()), 2); rec[f"{tag}_rate"] = rate; rec[f"{tag}_ci"] = f"[{lo},{hi}]"
        t1.append(rec)
    write_csv(out / f"T1_success_{split}.csv", t1, list(dict.fromkeys(k for r in t1 for k in r)))
    # --- T2 paired differences
    t2 = []
    for A, ma, B, mb, label in COMPARISONS:
        for lang in LANGS + [None]:
            d = boot_diff(items(rows, A, ma, lang), items(rows, B, mb, lang))
            if d: t2.append(dict(comparison=label, A=f"{A}|{ma}", B=f"{B}|{mb}", lang=lang or "ALL", **d))
    write_csv(out / f"T2_paired_{split}.csv", t2)
    # --- T3 error breakdown (overlapping flags; denominator = determinate scenario-draws)
    t3 = []
    for system, mode in present:
        rs = [r for r in rows if r["system"] == system and r["mode"] == mode and not r["code_mix"] and r["expected_outcome"] == "sentence"]
        if not rs: continue
        sent = [r for r in rs if r["retention"] is not None]
        miss_inst = sum((r["n_concepts"] - r["n_present"]) for r in sent); tot_inst = sum(r["n_concepts"] for r in sent)
        t3.append(dict(system=system, mode=mode, n_rows=len(rs), n_sentence=len(sent), n_not_sentence=len(rs) - len(sent), concept_instances=tot_inst, missed_concepts=miss_inst,
                       **{k: sum(r[k] or 0 for r in sent) for k in [f for f in FLAGS if f != "script_ok"] + ["script_err"]}, success=sum(r["success"] for r in rs)))
    write_csv(out / f"T3_errors_{split}.csv", t3)
    # --- T5 outcomes / routes
    t5 = []
    for system, mode in present:
        rs = [r for r in rows if r["system"] == system and r["mode"] == mode and not r["code_mix"]]
        det = [r for r in rs if r["expected_outcome"] == "sentence"]; amb = [r for r in rs if r["expected_outcome"] != "sentence"]
        if not det: continue
        c = collections.Counter(r["outcome"] for r in det)
        accepted = [r for r in det if r["route"] in ("model_first", "model_retry")]; fb = [r for r in det if r["outcome"] == "sentence_template" and system != "template_archived" and system != "template_revised"]
        t5.append(dict(system=system, mode=mode, n_determinate=len(det), **{f"n_{k}": v for k, v in sorted(c.items())},
                       model_accepted=len(accepted), accepted_error=sum(1 - r["success"] for r in accepted), fallback=len(fb), fallback_success=sum(r["success"] for r in fb),
                       first_attempt_accepted=sum(r["route"] == "model_first" for r in det), n_ambiguous=len(amb),
                       ambiguous_clarified=sum(r["outcome"] == "clarification" for r in amb), ambiguous_literal=sum(r["outcome"] == "literal_preview" for r in amb),
                       ambiguous_confident_sentence=sum(r["outcome"].startswith("sentence") for r in amb)))
    write_csv(out / f"T5_outcomes_{split}.csv", t5)
    # --- T6 by family (revised hybrid vs template vs archived), covered / uncovered
    t6 = []
    for system, mode in [("revised_hybrid", "rev"), ("template_revised", "rev"), ("archived_deployed", "orig"), ("onepass", "rev"), ("revised_hybrid", "gold"), ("template_revised", "gold")]:
        for key in ("family", "template_covered"):
            vals = collections.defaultdict(lambda: [0.0, 0])
            for i, (g, v) in items(rows, system, mode).items():
                r0 = next(r for r in rows if r["id"] == i)
                vals[str(r0[key])][0] += v; vals[str(r0[key])][1] += 1
            for k, (s, n) in sorted(vals.items()):
                t6.append(dict(system=system, mode=mode, by=key, value=k, n=n, successes=round(s, 2), rate=round(100 * s / n, 1), sparse=n < 8))
    write_csv(out / f"T6_by_family_{split}.csv", t6)
    return t1, t2, t3, t5


def codemix(rows, split, out):
    """Exploratory Hinglish rows (n = 8): raw counts only."""
    c = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["code_mix"] in (True, "True") and r["expected_outcome"] == "sentence":
            c[(r["system"], r["mode"])][0] += r["success"] or 0; c[(r["system"], r["mode"])][1] += 1
    write_csv(out / f"T8_codemix_exploratory_{split}.csv", [dict(system=k[0], mode=k[1], successes=v[0], rows=v[1]) for k, v in sorted(c.items())])


def gate_confusion(split, out):
    """Gate verdict vs scorer verdict on every FIRST candidate (final text of attempt 1) of the saved streams, determinate scenarios."""
    scs = {s["id"]: s for s in jl(V2 / "fixtures" / split / "scenarios.jsonl")}
    streams = R.load_streams(split); LLM0, SEM0 = R._arch(); V0, V1 = SEM0(None), R.SEM.SemanticValidator(None)
    caps = {m: {r["id"]: r for r in jl(V2 / "results/payloads" / f"{('original' if m == 'orig' else 'revised')}_{split}.jsonl")} for m in ("orig", "rev")}
    rows = []
    for (i, gen, mode, sd), r in streams.items():
        sc = scs.get(i)
        if not sc or sc["expected_outcome"] != "sentence" or sc.get("code_mix") or not r.get("attempts"): continue
        pay = dict(r["payload"], language=sc["lang"], code_mix=False)
        ctx0, ctx1 = R.legacy_context(pay), R.P.normalize_request(pay)
        for k, at in enumerate(r["attempts"]):
            if at.get("text") is None: continue
            ok = S2.score(R.scorer_sc(sc), at["text"])["success"]
            for gname, G in (("V0_archived", lambda t: V0.validate(ctx0, at.get("ledger") or {"forbidden": []}, t, sc["lang"])[0]), ("V1_revised", lambda t: V1.validate(ctx1, {}, t, sc["lang"])[0])):
                rows.append(dict(id=i, lang=sc["lang"], gen=gen, mode=mode, seed=sd, attempt=k, gate=gname, gate_accept=int(G(at["text"])), scorer_correct=int(ok)))
    write_csv(out / f"T4_gate_candidates_{split}.csv", rows)
    agg = collections.defaultdict(lambda: collections.Counter())
    for r in rows:
        if r["attempt"] != 0: continue
        for key in ((r["gate"], r["gen"], "ALL"), (r["gate"], r["gen"], r["lang"])):
            agg[key][("TA" if r["scorer_correct"] else "FA") if r["gate_accept"] else ("FR" if r["scorer_correct"] else "TR")] += 1
    t4 = []
    for (g, gen, lang), c in sorted(agg.items()):
        n = sum(c.values()); acc = c["TA"] + c["FA"]; cor = c["TA"] + c["FR"]
        t4.append(dict(gate=g, generator=gen, lang=lang, n=n, accept_correct=c["TA"], accept_wrong=c["FA"], reject_wrong=c["TR"], reject_correct=c["FR"],
                       coverage_accept_rate=round(acc / n, 3), accepted_error_rate=round(c["FA"] / acc, 3) if acc else None,
                       false_reject_of_correct=round(c["FR"] / cor, 3) if cor else None, false_accept_of_wrong=round(c["FA"] / (n - cor), 3) if n - cor else None))
    write_csv(out / f"T4_gate_confusion_{split}.csv", t4)
    return t4


def latency(rows, split, out):
    streams = R.load_streams(split); res = []
    by = collections.defaultdict(list)
    for (i, gen, mode, sd), r in streams.items():
        for at in r.get("attempts", []):
            if at.get("latency") is not None: by[(gen, r["lang"], at["k"])].append(at["latency"])
    for (gen, lang, k), v in sorted(by.items()):
        res.append(dict(generator=gen, lang=lang, attempt=k, n=len(v), median_s=round(float(np.median(v)), 2), p95_s=round(float(np.percentile(v, 95)), 2), note="latency of the original uncached GPU call (GTX 1650)"))
    write_csv(out / f"T7_stage_latency_{split}.csv", res)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--split", required=True); a = ap.parse_args()
    out = V2 / "results/tables"; (V2 / "results/scored").mkdir(exist_ok=True, parents=True)
    if a.split == "legacy":
        EXCLUDE.update(r["id"] for r in csv.DictReader(open(V2 / "results/audit/A2_exclusion_log.csv", encoding="utf-8")))
    rows = build_rows(a.split)
    write_csv(V2 / "results/scored" / f"{a.split}_scored.csv", rows)
    t1, t2, t3, t5 = tables(rows, a.split, out)
    t4 = gate_confusion(a.split, out); latency(rows, a.split, out); codemix(rows, a.split, out)
    print(f"{a.split}: {len(rows)} scored rows")
    for r in t1: print({k: r[k] for k in r if k in ("system", "mode", "ALL_n", "ALL_rate", "ALL_ci", "en_rate", "hi_rate", "gu_rate", "mr_rate")})
    for r in t2[:40]:
        if r["lang"] == "ALL": print(r["comparison"], r["diff_pp"], (r["lo"], r["hi"]), "n=", r["n_items"])
