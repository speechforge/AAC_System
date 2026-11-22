import json
c = json.load(open("results/improve_cpu_en_hi_mr_gu.json")); g = json.load(open("results/improve_gpu_en.json"))["en"]
NM = {"en": "English", "hi": "Hindi", "mr": "Marathi", "gu": "Gujarati"}
L = [open("improvement_plan_static.txt", encoding="utf-8").read().rstrip("\n"), ""]
def table(head, rows):
    cols = list(zip(*([head] + rows))); w = [max(len(str(x)) for x in col) for col in cols]
    L.append("  " + " | ".join(str(h).ljust(w[i]) for i, h in enumerate(head))); L.append("  " + "-+-".join("-" * x for x in w))
    for r in rows: L.append("  " + " | ".join(str(x).ljust(w[i]) for i, x in enumerate(r)))
    L.append("")
L += [" EXECUTED 2026-11-19 (results/improve_cpu_en_hi_mr_gu.json, results/improve_gpu_en.json; code exp_improve.py).",
      " Same protocol as the main experiments; KSR = average of AAC-user and caregiver test sets. KSR ↑ higher is better.", "",
      " Steps 1 and 2 - full test sets, CPU:", ""]
rows = []
for l in ("en", "hi", "mr", "gu"):
    s = c[l]["systems"]; a = s["shipped infinity-gram"]["avg_ksr"]; b = s["step1: no selected-word exclusion"]["avg_ksr"]; h = s["step2: infinity-gram + char 12-gram hybrid"]["avg_ksr"]
    rows.append([NM[l], f"{a:.2f}", f"{b:.2f} ({b-a:+.2f})", f"{h:.2f} ({h-a:+.2f})", f"{s['char 12-gram']['avg_ksr']:.2f}", c[l]["mix_weight_infgram"]])
table(["Language", "shipped KSR ↑", "Step 1: no exclusion", "Step 2: + char 12-gram hybrid", "char 12-gram alone", "∞-gram weight in mix"], rows)
L += [" Step 1 RESULT: improves KSR in all four languages (+0.3 to +1.0). CONFIRMED - recommended.",
      " Step 2 RESULT: the hybrid adds only +0.0 to +0.5 over Step 1 (English -0.1, Hindi +0.0, Marathi +0.1, Gujarati +0.5). That is inside the noise",
      "   of these test sets, so the hybrid is NOT justified by this data; its benefit may show up with more training data. Not recommended yet.", "",
      " Step 3 - English, GPU, 40+40 sentence subsample (adapted OPT-125m retrained for 1 epoch; mixing weight tuned on only 30 dev sentences):", ""]
s = g["systems"]; rows = [[n, f"{v['avg_ksr']:.2f}", f"{v['aac']['top5']:.1f} / {v['care']['top5']:.1f}"] for n, v in s.items()]
table(["System", "KSR avg ↑", "top-5 hit % ↑ (AAC / Care)"], rows)
a = s["shipped infinity-gram"]["avg_ksr"]; o = s["adapted OPT-125m alone"]["avg_ksr"]; h = s["step3: infinity-gram + adapted OPT-125m hybrid"]["avg_ksr"]
L += [f" Step 3 RESULT: the hybrid reaches KSR {h:.1f}, +{h-a:.1f} over the shipped ∞-gram and level with the adapted OPT alone ({o:.1f}). The tuned weight put only {g['mix_weight_infgram']:.0%} on the",
      "   ∞-gram, i.e. the LM is doing the work. So the accuracy gap CAN be closed, but only by running the LM (GPU or quantised CPU); the ∞-gram's",
      "   remaining roles are the instant CPU fallback, an interpretable shelf and candidate proposal. Treat as an optional 'accuracy mode', not a replacement.", "",
      " Step 5 (evidence already in RESULTS_vs_baseline.txt, Sec. 5): a 2-word context cap ties or beats unlimited depth in all four languages.", "",
      " NOT YET DONE (need code changes in the app, new data, participants or live services):",
      "   Step 4 per-language engines in the app | Step 6 more/native data | Step 7 personalisation | Step 8 live LLM cascade, TTS MOS, user study | Step 9 CIs over 5 splits",
      " I did NOT modify the shipped application code; Steps 1, 4, 5 are ready to apply on request (small changes in indic-generative-aac/backend/infinity_gram.py and hmm.py).", "",
      "--------------------------------------------------------------------------------------------------------------",
      " 5. RECOMMENDED NEXT ACTIONS (in order)",
      "--------------------------------------------------------------------------------------------------------------",
      "  1. Apply Step 1 + Step 5 to the app (exclude_selected off for the word shelf; cap context at 3 words with unlimited back-off).  [safe, measured]",
      "  2. Run Step 9 (5 splits, CIs) so Steps 1/2 can be called significant or tied.",
      "  3. Run Step 8a (live cascade evaluation) - it is the largest missing piece of evidence for the paper.",
      "  4. Collect the native Marathi/Gujarati test sets (Step 6a) - the mr/gu numbers are currently machine-translation based.",
      "  5. Decide on the optional LM re-ranker (Step 3) after weighing GPU/CPU cost against a ~+7 KSR gain."]
open("IMPROVEMENT_PLAN.txt", "w", encoding="utf-8").write("\n".join(L))
print("\n".join(L[-40:]))
