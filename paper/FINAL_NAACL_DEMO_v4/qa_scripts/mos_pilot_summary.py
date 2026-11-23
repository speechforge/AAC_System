#!/usr/bin/env python3
"""Review point 3: aggregate, privacy-safe summary of the listening test (MOS portal) for the paper.

Reads subjective_Mos_portal/.data/portal.sqlite3 READ-ONLY and writes ONLY aggregates (no names, e-mails, ages or IDs):
  mos_pilot_summary.json next to this script.
Method (same as the portal, subjective_Mos_portal/FINAL_CONTEXT.md): primary MOS = mean of all 1-5 ratings from COMPLETED
(20 of 20 clips), non-excluded sessions; 95 % CI = percentile bootstrap over LISTENERS (2,000 resamples, seed 20261117),
each resample averaging the listeners' per-language means. Reported twice: all completed listeners, and only listeners whose
stated mother tongue is the clip's language ("native"). English clips: F5-TTS; Hindi/Gujarati/Marathi: IndicF5; 5 clips per
language, authored AAC sentences, synthesized 2026-11-17 by the CURRENT build's /api/tts (not the evaluated build of Section 4,
whose speech was a placeholder tone).
Usage: python3 mos_pilot_summary.py"""
import collections, datetime, json, pathlib, random, sqlite3, statistics

HERE = pathlib.Path(__file__).resolve().parent
PORTAL = HERE.parents[2] / "subjective_Mos_portal"
db = sqlite3.connect(f"file:{PORTAL / '.data/portal.sqlite3'}?mode=ro", uri=True)
stim = {s["id"]: s for s in json.load(open(PORTAL / "config/stimuli.json", encoding="utf-8"))}
NATIVE = {"en": "english", "hi": "hindi", "gu": "gujarati", "mr": "marathi"}
P = {pid: dict(excluded=bool(x), done=(n == 20), tongue=(t or "").strip().lower())
     for pid, x, n, t in db.execute("select participant_id, is_excluded, trials_completed, mother_tongue from participants")}
R = [(pid, cid, s) for pid, cid, s in db.execute("select participant_id, clip_id, score from trials where score is not null")]


def summary(keep):
    out = {}
    for lang in ("en", "hi", "gu", "mr"):
        per = collections.defaultdict(list)
        for pid, cid, s in R:
            if stim[cid]["language"] == lang and keep(pid, lang):
                per[pid].append(s)
        means = [statistics.mean(v) for v in per.values()]
        allr = [s for v in per.values() for s in v]
        ci = None
        if len(means) >= 2:
            rng = random.Random(20261117)
            bs = sorted(statistics.mean(rng.choice(means) for _ in means) for _ in range(2000))
            ci = [round(bs[49], 2), round(bs[1949], 2)]
        out[lang] = dict(listeners=len(means), ratings=len(allr), mos=round(statistics.mean(allr), 2) if allr else None,
                         ci95_listener_bootstrap=ci, engine=sorted({stim[c]["engine"] for c in stim if stim[c]["language"] == lang}))
    return out


res = dict(
    snapshot_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    method=__doc__.split("Usage")[0].strip(),
    registered=len(P), completed=sum(v["done"] and not v["excluded"] for v in P.values()),
    excluded=sum(v["excluded"] for v in P.values()),
    mother_tongue_counts=dict(collections.Counter(v["tongue"] or "not given" for v in P.values())),
    completed_all_listeners=summary(lambda pid, lang: P[pid]["done"] and not P[pid]["excluded"]),
    native_listeners_any_progress=summary(lambda pid, lang: not P[pid]["excluded"] and P[pid]["tongue"] == NATIVE[lang]),
)
json.dump(res, open(HERE / "mos_pilot_summary.json", "w"), indent=1, ensure_ascii=False)
# LaTeX macros for the v4 paper (appendix, speech paragraph)
fmt = lambda r: f"{r['mos']:.2f} ({r['ci95_listener_bootstrap'][0]:.2f}--{r['ci95_listener_bootstrap'][1]:.2f})"
c, n = res["completed_all_listeners"], res["native_listeners_any_progress"]
tex = ["% v4 MOS pilot, written by qa_scripts/mos_pilot_summary.py (snapshot " + res["snapshot_utc"] + ")"]
tex += ["\\newcommand{\\MosPilot" + k + "}{" + fmt(c[l]) + "}" for k, l in (("EN", "en"), ("HI", "hi"), ("GU", "gu"), ("MR", "mr"))]
tex += ["\\newcommand{\\MosNat" + k + "}{" + fmt(n[l]) + "}" for k, l in (("GU", "gu"), ("HI", "hi"))]
(HERE.parent / "latex_source_v4/generated/mos_pilot.tex").write_text("\n".join(tex) + "\n")
print(json.dumps({k: v for k, v in res.items() if k != "method"}, indent=1, ensure_ascii=False))
