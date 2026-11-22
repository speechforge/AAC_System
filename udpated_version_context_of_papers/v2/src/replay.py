#!/usr/bin/env python3
"""Replay saved candidate streams through every system / policy and score the outputs (scorer v2; scorer v1 kept for the archived comparison).
One output row per (scenario, system, input mode, seed, stage).  All policies read the SAME saved candidates, so differences between
policies are policy differences, not generator noise.
Systems (names are stable keys used by analyze_v2.py):
  archived_deployed        G0 stream + V0 gate + T0 template, archived retry policy (2 attempts)            [input: orig browser | gold]
  cascade_ungated_first    first candidate of the G0 stream, no gate, no fallback                            [orig | gold]
  cascade_ungated_last     last candidate after an earlier rejection by the archived gate V0 (== first when V0 accepts)
  gate_only_v1             G0 stream + V1 gate + T0 template (pure gate change, same retry policy)           [orig | gold]
  revised_cascade_first    first candidate of the G1 stream, no gate (matched ungated generation for the repaired hybrid) [rev | gold | orig]
  revised_cascade_last     last candidate of the G1 stream after a V1 rejection
  revised_hybrid           G1 stream + V1 gate + T1 template + clarification / literal outcomes               [rev | gold | orig(cross)]
  template_archived        T0 alone                                                                           [orig | gold]
  template_revised         T1 alone (no model)                                                                [rev | gold]
  onepass                  matched one-pass Qwen prompt, no gate                                              [rev | gold]
"""
import collections, json, sys
from common import *
import score_v2 as S2
sys.path.insert(0, str(REPO / "backend"))
import aac_lexicon as L, pipeline as P, semantic as SEM, templates as T
LLM_ARCH_T0 = None


def _arch():
    global LLM_ARCH_T0
    if LLM_ARCH_T0 is None:
        import types, builtins
        # import the archived llm module WITHOUT loading weights: only its generate_deterministic_fallback (pure function of the context) is needed
        from run_streams import LLM_ARCH, SEM_ARCH
        LLM_ARCH_T0 = (LLM_ARCH, SEM_ARCH)
    return LLM_ARCH_T0


def legacy_context(payload):
    from run_streams import legacy_context as lc
    return lc(payload)


def scorer_sc(r):
    return dict(lang=r["lang"], code_mix=bool(r.get("code_mix")), content_concepts=r["content_concepts"], gold_neg=r["gold_neg"], gold_act=r["gold_act"], more=r.get("more", False))


class StubLLM:
    realize_template = None


def load_streams(split):
    out = {}
    for p in sorted((V2 / "results/streams").glob(f"{split}*shard*.jsonl")):
        for r in jl(p):
            if "attempts" in r or r.get("note"):
                out[(r["id"], r["gen"], r["mode"], r["seed"])] = r
    return out


def load_onepass(split):
    out = {}
    for p in sorted((V2 / "results/streams").glob(f"onepass_{split}_shard*.jsonl")):
        for r in jl(p):
            out[(r["id"], r["mode"], r["seed"])] = r
    return out


def _att(row, k, greedy):
    at = row.get("attempts") or []
    if k < len(at): return at[k], False
    if greedy and at: return at[0], True               # greedy retry reproduces attempt 1 (checked by determinism_check.py)
    return None, False


def run_archived_policy(ctx0, row, gate, lang, template_fn, greedy, retries=2):
    """Archived app.py loop: up to 2 attempts, first gate-accepted wins, else the template (marked valid unconditionally)."""
    used, assumed = 0, False
    for k in range(retries):
        at, ass = _att(row, k, greedy)
        if at is None: break
        used += 1; assumed = assumed or ass
        if at.get("text") is None: continue
        ok, d = gate(ctx0, at, at["text"])
        if ok: return dict(text=at["text"], outcome="sentence_model", route="model_first" if k == 0 else "model_retry", attempts=used, reasons=[], assumed=assumed)
    return dict(text=template_fn(), outcome="sentence_template", route="template_after_rejection", attempts=used, reasons=[], assumed=assumed)


def payload_for(sc, mode, gen, caps):
    import run_streams as RS
    if mode == "gold": return RS.gold_payload(sc, gen)
    if sc.get("code_mix") and mode == "orig": return sc.get("archived_payload_ui")
    c = caps["orig" if mode in ("orig", "cross") else "rev"].get(sc["id"])
    return (c or {}).get("payload")


def systems_for(sc, caps, streams, onepass, seeds_en):
    """Yield (system, mode, seed, result dict) for one scenario."""
    LLM0, SEM0 = _arch()
    V0, V1 = SEM0(None), SEM.SemanticValidator(None)
    lang, cm = sc["lang"], bool(sc.get("code_mix"))
    greedy = lang != "en" and not cm
    seeds = seeds_en if not greedy else [None]
    res = []
    for mode in ("orig", "gold", "rev", "cross"):
        p0, p1 = (None if mode == "cross" else payload_for(sc, mode, "G0", caps)), payload_for(sc, mode, "G1", caps)
        if not p0 and not p1: continue
        ctx0 = legacy_context(dict(p0, language=lang, code_mix=cm)) if p0 else None
        ctx1 = P.normalize_request(dict(p1, language=lang, code_mix=cm)) if p1 else None
        t0 = (lambda: LLM0.generate_deterministic_fallback(None, ctx0, language=lang, code_mix=cm)) if ctx0 else None
        for sd in seeds:
            # ---- G0 stream systems (archived generator); judged by V0 on the archived context and by V1 on the normalised payload
            r0 = streams.get((sc["id"], "G0", mode, sd))
            if r0 and r0.get("attempts") and ctx0:
                c1g = ctx1 or P.normalize_request(dict(p0, language=lang, code_mix=cm))
                g0 = lambda ctx, at, txt: V0.validate(ctx0, at.get("ledger") or {"forbidden": []}, txt, lang)
                g1 = lambda ctx, at, txt: V1.validate(c1g, {}, txt, lang)
                res.append(("archived_deployed", mode, sd, run_archived_policy(ctx0, r0, g0, lang, t0, greedy)))
                a0 = r0["attempts"]
                res.append(("cascade_ungated_first", mode, sd, dict(text=a0[0].get("text"), outcome="sentence_ungated", route="first", attempts=1, reasons=[])))
                res.append(("archived_llm1_stage", mode, sd, dict(text=a0[0].get("llm1"), outcome="sentence_ungated", route="llm1_stage", attempts=1, reasons=[], stage="llm1")))
                last = a0[0] if (len(a0) == 1 or g0(ctx0, a0[0], a0[0].get("text") or "")[0]) else a0[1]
                res.append(("cascade_ungated_last", mode, sd, dict(text=last.get("text"), outcome="sentence_ungated", route="last_after_V0", attempts=len(a0), reasons=[])))
                res.append(("gate_only_v1", mode, sd, run_archived_policy(ctx0, r0, g1, lang, t0, greedy)))
            # ---- G1 stream systems (revised generator)
            r1 = streams.get((sc["id"], "G1", mode, sd))
            if r1 is not None and ctx1:
                if r1.get("note") == "clarification_no_generation" or not r1.get("attempts"):
                    res.append(("revised_hybrid", mode, sd, _fmt(P.decide(ctx1, lang, lambda k: None, V1, _RevLLM(), policy="hybrid"))))
                else:
                    out = P.decide(ctx1, lang, lambda k, r=r1: _norm_att(_att(r, k, greedy)[0]), V1, _RevLLM(), policy="hybrid")
                    res.append(("revised_hybrid", mode, sd, _fmt(out)))
                    a1 = r1["attempts"]
                    res.append(("revised_cascade_first", mode, sd, dict(text=a1[0].get("text"), outcome="sentence_ungated", route="first", attempts=1, reasons=[])))
                    res.append(("revised_llm1_stage", mode, sd, dict(text=a1[0].get("llm1"), outcome="sentence_ungated", route="llm1_stage", attempts=1, reasons=[], stage="llm1")))
                    lastv = a1[0] if (len(a1) == 1 or V1.validate(ctx1, {}, a1[0].get("text") or "", lang)[0]) else a1[1]
                    res.append(("revised_cascade_last", mode, sd, dict(text=lastv.get("text"), outcome="sentence_ungated", route="last_after_V1", attempts=len(a1), reasons=[])))
        # ---- model-free templates (seed-independent)
        if t0 and mode != "cross": res.append(("template_archived", mode, None, dict(text=t0(), outcome="sentence_template", route="template_only", attempts=0, reasons=[])))
        if ctx1 and mode in ("rev", "gold"):
            res.append(("template_revised", mode, None, _fmt(P.decide(ctx1, lang, lambda k: None, V1, _RevLLM(), policy="template_only"))))
        # ---- one-pass
        for sd in seeds:
            op = onepass.get((sc["id"], mode, sd))
            if op and mode in ("rev", "gold") and mode != "cross":
                res.append(("onepass", mode, sd, dict(text=op.get("text"), outcome="sentence_ungated", route="onepass", attempts=1, reasons=[], latency=op.get("latency"))))
    return res


class _RevLLM:
    def realize_template(self, ctx, language):
        from run_streams import LLM_REV
        return LLM_REV.realize_template(None, ctx, language)


def _norm_att(at):
    if at is None: return None
    return dict(text=at.get("text"), llm1=at.get("llm1"), llm2=at.get("llm2"), llm3_text=at.get("llm3_text"), latency=at.get("latency"), error=at.get("error"), ledger=at.get("ledger"))


def _fmt(o):
    return dict(text=o.get("text"), outcome=o["outcome"], route=o["route"], attempts=len(o["attempts"]), reasons=[x for a in o["attempts"] for x in a.get("reasons", [])] if o["outcome"] != "sentence_model" else [],
                options=o.get("options"), literal=o.get("literal"), template_gate=o.get("template_gate"))
