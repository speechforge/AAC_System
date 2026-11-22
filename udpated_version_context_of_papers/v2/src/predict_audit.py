#!/usr/bin/env python3
"""PHASE A (cont.) -- next-word prediction: (1) replay the archived evaluation and confirm it reproduces, (2) reconcile the printed one-decimal
hit@1 values with unrounded correct counts, (3) verify overlap / OOV denominators, (4) add a repeat-filtered test on the SAME train split.

Uses the archived functions (predict_eval.py) with an explicit repository root: the archived script computes ROOT from its own location
(parents[2]), which no longer points at the repository after the workspace moved under paper/CLAUDE_WRITTEN/. Nothing archived is modified.
OOV targets stay in every denominator and count as misses. CPU only.
Output: results/audit/A8_prediction_audit.json, A8_prediction_counts.csv"""
import json, pathlib, sys
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import *
sys.path.insert(0, str(ARCH_SYS / "backend"))          # infinity_gram.py: byte-identical to the working tree (checked in the log)
M = load_module("predict_eval_archived", ARCH / "predict_eval.py")
M.ROOT = ROOT                                           # explicit repository root (see docstring)
OUT = V2 / "results/audit"
archived = json.loads((ARCH / "results/prediction.json").read_text(encoding="utf-8"))
NAMES = ["unigram_frequency", "bigram_backoff", "trigram_backoff", "infinity_gram_deployed"]
rng_replay = np.random.default_rng(BOOT_SEED)           # archived: one generator shared by en then hi
report, count_rows = {}, []
for lang in ("en", "hi"):
    eng, train_sents, items, n_tr = M.build(lang)
    uni, bi, tri = M.NGram(train_sents, 1), M.NGram(train_sents, 2), M.NGram(train_sents, 3)
    systems = [("unigram_frequency", lambda c, m=uni: m.predict(c)), ("bigram_backoff", lambda c, m=bi: m.predict(c)), ("trigram_backoff", lambda c, m=tri: m.predict(c)),
               ("infinity_gram_deployed", lambda c, e=eng, l=lang: [p["word"] for p in e.predict_next(c, language=l, top_k=10)])]
    res = {s.get("name"): s for s in [M.eval_system(n, f, items, uni.vocab) for n, f in systems]}
    cl = np.array([i[0] for i in items])
    bs = M.boot(list(res.values()), cl, BOOT_N, rng_replay)
    # (1) replay vs archived values
    replay_ok = all(round(float(res[n][m].mean()), 4) == archived[lang]["systems"][n][m]["value"] for n in NAMES for m in ("hit1", "hit3", "hit5", "mrr"))
    ci_ok = all([round(float(np.percentile(bs[n]["hit1"], 2.5)), 4), round(float(np.percentile(bs[n]["hit1"], 97.5)), 4)] == archived[lang]["systems"][n]["hit1"]["ci95"] for n in NAMES)
    n = len(items)
    # (2) unrounded counts
    counts = {nm: dict(hit1=int(res[nm]["hit1"].sum()), hit5=int(res[nm]["hit5"].sum()), n=n) for nm in NAMES}
    t, g = counts["infinity_gram_deployed"], counts["trigram_backoff"]
    pp = lambda a, b: round(100 * (a - b) / n, 3)
    printed = {nm: round(100 * counts[nm]["hit1"] / n, 1) for nm in NAMES}
    rec = dict(n_items=n, replay_point_estimates_identical=replay_ok, replay_hit1_ci_identical=ci_ok, counts=counts,
               hit1_pct_unrounded={nm: round(100 * counts[nm]["hit1"] / n, 3) for nm in NAMES},
               hit1_pct_printed_one_decimal=printed,
               trie_minus_trigram_hit1=dict(count_diff=t["hit1"] - g["hit1"], pp_from_counts=pp(t["hit1"], g["hit1"]), pp_from_printed_values=round(printed["infinity_gram_deployed"] - printed["trigram_backoff"], 1)),
               trie_minus_trigram_hit5=dict(count_diff=t["hit5"] - g["hit5"], pp_from_counts=pp(t["hit5"], g["hit5"])))
    # (3) denominators
    full_utts = {i[3] for i in items}; train_utts = {tuple(s) for s in train_sents}
    seen = sorted(u for u in full_utts if u in train_utts)
    rec["denominators"] = dict(n_clusters=len(set(cl)), distinct_test_utterances=len(full_utts), distinct_seen_verbatim_in_train=len(seen),
                               oov_target_items=int(sum(t_ not in uni.vocab for _, _, t_, _ in items)), oov_rate=round(float(np.mean([t_ not in uni.vocab for _, _, t_, _ in items])), 4),
                               items_whose_utterance_is_seen_verbatim=int(sum(i[3] in train_utts for i in items)))
    # (4) repeat-filtered test on the same split (drop items whose whole utterance appears verbatim in training; OOV targets remain)
    keep = [k for k, i in enumerate(items) if i[3] not in train_utts]
    fitems = [items[k] for k in keep]
    fres = [M.eval_system(nm, f, fitems, uni.vocab) for nm, f in systems]
    fcl = np.array([i[0] for i in fitems]); fb = M.boot(fres, fcl, BOOT_N, np.random.default_rng(BOOT_SEED_V2))
    fr = {s["name"]: s for s in fres}
    rec["repeat_filtered"] = dict(n_items=len(fitems), n_clusters=len(set(fcl)), n_removed=n - len(fitems),
                                  oov_target_items=int(sum(t_ not in uni.vocab for _, _, t_, _ in fitems)),
                                  systems={nm: dict(hit1_count=int(fr[nm]["hit1"].sum()), hit1_pct=round(100 * float(fr[nm]["hit1"].mean()), 3),
                                                    hit5_pct=round(100 * float(fr[nm]["hit5"].mean()), 3), mrr=round(float(fr[nm]["mrr"].mean()), 4)) for nm in NAMES},
                                  trie_minus_trigram=dict(hit1_pp=round(100 * float(fr["infinity_gram_deployed"]["hit1"].mean() - fr["trigram_backoff"]["hit1"].mean()), 3),
                                                          hit1_ci95_pp=[round(100 * float(np.percentile(fb["infinity_gram_deployed"]["hit1"] - fb["trigram_backoff"]["hit1"], q)), 3) for q in (2.5, 97.5)],
                                                          hit5_pp=round(100 * float(fr["infinity_gram_deployed"]["hit5"].mean() - fr["trigram_backoff"]["hit5"].mean()), 3),
                                                          hit5_ci95_pp=[round(100 * float(np.percentile(fb["infinity_gram_deployed"]["hit5"] - fb["trigram_backoff"]["hit5"], q)), 3) for q in (2.5, 97.5)]))
    # full-test paired CI with the new seed as well (same resamples for both systems)
    fullb = M.boot(list(res.values()), cl, BOOT_N, np.random.default_rng(BOOT_SEED_V2))
    rec["full_test_paired_trie_minus_trigram_hit1_ci95_pp"] = [round(100 * float(np.percentile(fullb["infinity_gram_deployed"]["hit1"] - fullb["trigram_backoff"]["hit1"], q)), 3) for q in (2.5, 97.5)]
    report[lang] = rec
    for nm in NAMES:
        count_rows.append(dict(language=lang, system=nm, n_items=n, hit1_count=counts[nm]["hit1"], hit1_pct_unrounded=round(100 * counts[nm]["hit1"] / n, 3),
                               hit1_pct_one_decimal=printed[nm], hit5_count=counts[nm]["hit5"], filtered_n=len(fitems), filtered_hit1_count=int(fr[nm]["hit1"].sum())))
(OUT / "A8_prediction_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
write_csv(OUT / "A8_prediction_counts.csv", count_rows)
for lang, r in report.items():
    print(lang, "replay identical:", r["replay_point_estimates_identical"], r["replay_hit1_ci_identical"], "| n", r["n_items"], "| trie-trigram hit@1 count diff", r["trie_minus_trigram_hit1"],
          "| denominators", r["denominators"], "| repeat-filtered", {k: v for k, v in r["repeat_filtered"].items() if k != "systems"})
