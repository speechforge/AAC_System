#!/usr/bin/env python3
"""Integrity checks over the scored output of one split: unique keys, scenario pairing, totals and denominators, version consistency, split overlap,
freeze consistency, and the exit codes of the CPU commands.  Writes results/checks/integrity_<split>.json and exits 1 on any failure.
Usage: python check_all.py --split holdout [--run-commands]"""
import argparse, collections, csv, json, subprocess, sys
from common import *


def main(split, run_cmds):
    rep, fails = {}, []
    rows = list(csv.DictReader(open(V2 / "results/scored" / f"{split}_scored.csv", encoding="utf-8")))
    keys = collections.Counter((r["id"], r["system"], r["mode"], r["seed"], r["stage"]) for r in rows)
    dup = [k for k, v in keys.items() if v > 1]; rep["rows"] = len(rows); rep["duplicate_keys"] = len(dup)
    if dup: fails.append(f"{len(dup)} duplicate keys")
    scs = {r["id"]: r for r in jl(V2 / "fixtures" / split / "scenarios.jsonl")}
    unknown = {r["id"] for r in rows} - set(scs); rep["rows_with_unknown_scenario"] = len(unknown)
    if unknown: fails.append("unknown scenario ids")
    # pairing: every compared (system, mode) pair covers the same scenarios
    by = collections.defaultdict(set)
    for r in rows:
        if not r["code_mix"] == "True" and r["expected_outcome"] == "sentence": by[(r["system"], r["mode"])].add(r["id"])
    det_ids = {i for i, s in scs.items() if s["expected_outcome"] == "sentence" and not s.get("code_mix")}
    cov = {f"{k[0]}|{k[1]}": (len(v), len(det_ids)) for k, v in sorted(by.items())}
    rep["determinate_coverage_by_system_mode (n_scored, n_determinate)"] = cov
    partial = [k for k, (a, b) in cov.items() if a != b]
    rep["systems_not_covering_all_determinate_scenarios"] = partial
    # totals and denominators: per-language counts add up to the pooled count
    t1 = list(csv.DictReader(open(V2 / "results/tables" / f"T1_success_{split}.csv", encoding="utf-8")))
    bad_tot = []
    for r in t1:
        s = sum(float(r.get(f"{l}_k") or 0) for l in LANGS); n = sum(int(r.get(f"{l}_n") or 0) for l in LANGS)
        if abs(s - float(r["ALL_k"])) > 1e-6 or n != int(r["ALL_n"]): bad_tot.append(r["system"] + "|" + r["mode"])
    rep["tables_whose_language_counts_do_not_sum"] = bad_tot
    if bad_tot: fails.append("totals mismatch")
    # version consistency
    rep["scorer_versions"] = sorted({r["scorer"] for r in rows}); rep["model_revision_in_freeze"] = json.loads((V2 / "config/freeze_manifest.json").read_text())["config"]["model_revision"] if (V2 / "config/freeze_manifest.json").exists() else None
    if len(rep["scorer_versions"]) != 1: fails.append("multiple scorer versions")
    fr = subprocess.run([sys.executable, str(V2 / "src/freeze.py"), "--check"], capture_output=True, text=True)
    rep["freeze_check"] = (fr.stdout + fr.stderr).strip()
    if split == "holdout" and fr.returncode != 0: fails.append("freeze violated")
    # split overlap results
    for s in ("dev", "legacy", "holdout"):
        p = V2 / "results/checks" / f"fixture_checks_{s}.json"
        if p.exists(): rep[f"fixture_checks_{s}_violations"] = json.loads(p.read_text())["violations"]
    # command exits
    if run_cmds:
        exits = {}
        for name, cmd in (("gate_probes", ["eval_gate_probes.py"]), ("rescore_archived", ["rescore_archived.py"]), ("fixture_checks", ["check_fixtures.py", split])):
            exits[name] = subprocess.run([sys.executable, str(V2 / "src" / cmd[0]), *cmd[1:]], capture_output=True, text=True, cwd=str(V2 / "src")).returncode
        rep["command_exit_codes"] = exits
        if any(exits.values()): fails.append(f"command exits {exits}")
    rep["failures"] = fails
    (V2 / "results/checks").mkdir(exist_ok=True, parents=True)
    (V2 / "results/checks" / f"integrity_{split}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k != "determinate_coverage_by_system_mode (n_scored, n_determinate)"}, ensure_ascii=False)[:900]); sys.exit(1 if fails else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--split", required=True); ap.add_argument("--run-commands", action="store_true"); a = ap.parse_args(); main(a.split, a.run_commands)
