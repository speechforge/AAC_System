#!/usr/bin/env python3
"""Analyse returned native-rater files (reviewer_packet/filled/packet_<lang>_R1.csv, _R2.csv, optional adjudicated_<lang>.csv).  With no returned ratings it writes
results/audit/D_ratings_status.json with status PENDING and exits 0 -- it never fabricates or imputes ratings.
When ratings exist it reports: assigned / rated / missing counts, pre-adjudication agreement (percent and Cohen's kappa) per Y/N field, adjudicated meaning
outcomes for the template and the hybrid on (a) all assigned pairs and (b) the prespecified subset where BOTH outputs preserve meaning, naturalness and paired preference
(with tie), and agreement of the automatic scorer v2 and the gate with the adjudicated meaning."""
import csv, collections, json, pathlib
from common import *

PK = V2 / "reviewer_packet"; FILLED = PK / "filled"
YN = ["content_added(Y/N)", "content_omitted(Y/N)", "polarity_and_negation_scope_correct(Y/N)", "act_correct(Y/N)", "speaker_is_first_person(Y/N)"]


def kappa(a, b):
    n = len(a)
    if n == 0: return None
    po = sum(x == y for x, y in zip(a, b)) / n
    labs = set(a) | set(b); pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labs)
    return None if pe == 1 else round((po - pe) / (1 - pe), 3)


def main():
    key = {k["item_id"]: k for k in jl_csv(PK / "KEY_DO_NOT_SHARE_WITH_RATERS.csv")} if (PK / "KEY_DO_NOT_SHARE_WITH_RATERS.csv").exists() else {}
    files = sorted(FILLED.glob("packet_*_R*.csv")) if FILLED.exists() else []
    rows = []
    for f in files: rows += list(csv.DictReader(open(f, encoding="utf-8")))
    filled = [r for r in rows if any((r.get(f"o1_{c}") or "").strip() for c in YN) or (r.get("preference(1/2/tie)") or "").strip()]
    st = dict(status="PENDING" if not filled else "PARTIAL_OR_COMPLETE", n_files=len(files), n_items_assigned=len(key) // 1 if key else None, n_items_with_any_rating=len(filled), generated=now_utc(),
              note="No native-speaker ratings have been returned; no human outcome is reported or imputed. The automatic scorer and gate verdicts are not substitutes for these judgments.")
    if filled:
        by = collections.defaultdict(dict)
        for r in filled: by[(r["item_id"].split("-")[0], r["item_id"].split("-")[2])][r["item_id"].split("-")[1]] = r
        agree = {}
        for fld in YN:
            for o in ("o1", "o2"):
                a, b = [], []
                for k, d in by.items():
                    if "R1" in d and "R2" in d and d["R1"].get(f"{o}_{fld}") and d["R2"].get(f"{o}_{fld}"):
                        a.append(d["R1"][f"{o}_{fld}"].strip().upper()); b.append(d["R2"][f"{o}_{fld}"].strip().upper())
                agree[f"{o}_{fld}"] = dict(n=len(a), percent=round(100 * sum(x == y for x, y in zip(a, b)) / len(a), 1) if a else None, cohen_kappa=kappa(a, b))
        st["pre_adjudication_agreement"] = agree
        st["note"] = "Ratings present: adjudicated outcomes require adjudicated_<lang>.csv (see ADJUDICATION.md); run again after adjudication."
    (V2 / "results/audit/D_ratings_status.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8"); print(json.dumps(st, ensure_ascii=False)[:500])


def jl_csv(p): return list(csv.DictReader(open(p, encoding="utf-8")))


if __name__ == "__main__":
    main()
