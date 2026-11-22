#!/usr/bin/env python3
"""Write (or verify) config/freeze_manifest.json: SHA-256 of every rule, prompt, decoding, metric and scorer file of the revised system.
`python freeze.py`         -> write the manifest (run once, after tuning on the development split and BEFORE the holdout is generated)
`python freeze.py --check` -> verify that nothing changed since the freeze (run before the holdout analysis)"""
import json, subprocess, sys
from common import *

FILES = [
    "indic-generative-aac/backend/aac_lexicon.py", "indic-generative-aac/backend/templates.py", "indic-generative-aac/backend/semantic.py",
    "indic-generative-aac/backend/pipeline.py", "indic-generative-aac/backend/llm.py", "indic-generative-aac/backend/app.py",
    "indic-generative-aac/backend/tts.py", "indic-generative-aac/backend/board_concepts.json", "indic-generative-aac/frontend/index.html",
    "udpated_version_context_of_papers/v2/src/score_v2.py", "udpated_version_context_of_papers/v2/src/build_fixtures.py",
    "udpated_version_context_of_papers/v2/src/run_streams.py", "udpated_version_context_of_papers/v2/src/run_onepass.py",
    "udpated_version_context_of_papers/v2/fixtures/PREREGISTRATION.md",
]
CFG = dict(seeds=SEEDS, bootstrap_seed=BOOT_SEED_V2, bootstrap_resamples=BOOT_N, scorer="scorer-v2", gate="gate-v2",
           model="Qwen/Qwen2.5-0.5B-Instruct", model_revision="7ae557604adf67be50417f59c2c2f167def9a775", dtype="float16",
           decoding="realiser: Indic few-shot greedy (temperature 0.01, max_new_tokens 75); English/code-mixed temperature 0.1 (max_new_tokens 60); LLM-2 temperature 0.05 greedy (60); LLM-3 temperature 0.0 (120); retry MAX_RETRIES=2",
           metrics="strict full-scenario success on determinate scenarios (scorer v2); denominators per table")


def git(*a):
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True).stdout.strip()


def build():
    return dict(frozen_at_utc=now_utc(), source_commit=git("rev-parse", "HEAD"), dirty_status=git("status", "--short").splitlines(),
                files={f: sha256(ROOT / f) for f in FILES}, config=CFG)


if __name__ == "__main__":
    p = V2 / "config/freeze_manifest.json"
    if "--check" in sys.argv:
        m = json.loads(p.read_text()); bad = [f for f, h in m["files"].items() if sha256(ROOT / f) != h]
        print("FREEZE OK" if not bad else f"FREEZE VIOLATED: {bad}"); sys.exit(1 if bad else 0)
    if p.exists(): sys.exit("manifest already exists (freeze once); delete it deliberately to re-freeze")
    p.write_text(json.dumps(build(), indent=1)); log("system freeze written (config/freeze_manifest.json)"); print("frozen", p)
