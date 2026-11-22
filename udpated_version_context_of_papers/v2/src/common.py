"""Shared paths and helpers for the v2 experiment harness (Indic AAC Studio).

Conventions (kept from the archived harness): one JSON object per line for raw outputs, one CSV row per
(scenario, system, condition) for scored output, a summary JSON for aggregates.
The ARCHIVED system is the pinned snapshot in archived_system/ (commit fe4e185); the REVISED system is the working tree.
"""
import csv, datetime, hashlib, importlib.util, json, pathlib, sys

ROOT = pathlib.Path("/home/linux/Documents/aac_system_november_11/AAC_System_merged")
V2 = ROOT / "udpated_version_context_of_papers" / "v2"
ARCH = ROOT / "paper/CLAUDE_WRITTEN/naacl2027_demo/eval"            # archived fixtures, scorer, raw outputs
ARCH_SYS = V2 / "archived_system" / "indic-generative-aac"           # original backend + client at the pinned commit
REPO = ROOT / "indic-generative-aac"                                 # working tree (revised system)
LANGS = ["en", "hi", "gu", "mr"]
LANG_NAME = {"en": "English", "hi": "Hindi", "gu": "Gujarati", "mr": "Marathi"}
BOOT_SEED = 20261111          # archived bootstrap seed (kept for the reproduction check)
BOOT_SEED_V2 = 20261113       # seed for all new intervals
BOOT_N = 10000
SEEDS = [11, 23, 47]          # prespecified generation seeds for stochastic (English / code-mixed) paths


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def jl(path):
    p = pathlib.Path(path)
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def write_jl(path, rows, mode="w"):
    with open(path, mode, encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def append_jl(path, row):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def payload_key(p):
    return hashlib.sha256(json.dumps(p, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def load_module(name, path):
    """Import a module from an explicit path under a unique name (lets archived and revised code coexist)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def write_csv(path, rows, cols=None):
    cols = cols or (list(rows[0].keys()) if rows else [])
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def log(msg, name="EXPERIMENT_LOG.md"):
    """Append a timestamped line to the experiment log (the audit trail of what ran when)."""
    with open(V2 / "logs" / name, "a", encoding="utf-8") as f:
        f.write(f"- {now_utc()}  {msg}\n")
