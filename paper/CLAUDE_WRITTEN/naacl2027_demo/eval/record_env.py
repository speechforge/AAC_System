#!/usr/bin/env python3
"""Record the exact software/hardware/data state the evaluation ran against."""
import json, subprocess, sys, platform, hashlib, pathlib, importlib, urllib.request
HERE = pathlib.Path(__file__).resolve().parent; ROOT = HERE.parents[2]
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True, cwd=ROOT).stdout.strip()
env = dict(
  date=sh("date -Is"), git_commit=sh("git rev-parse HEAD"), git_branch=sh("git rev-parse --abbrev-ref HEAD"),
  git_dirty_files=sh("git status --short | grep -v '^??' | head"), python=sys.version.split()[0], platform=platform.platform(),
  gpu=sh("nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader"),
  scenarios_sha256=hashlib.sha256((HERE/'fixtures/scenarios.jsonl').read_bytes()).hexdigest(),
  lexicon_sha256=hashlib.sha256((HERE/'fixtures/lexicon.json').read_bytes()).hexdigest(),
  backend_files_sha256={f: hashlib.sha256((ROOT/'indic-generative-aac/backend'/f).read_bytes()).hexdigest()[:16]
                        for f in ['app.py','llm.py','semantic.py','hmm.py','infinity_gram.py','tts.py']},
  frontend_sha256=hashlib.sha256((ROOT/'indic-generative-aac/frontend/index.html').read_bytes()).hexdigest()[:16],
)
for m in ["torch", "transformers", "fastapi", "uvicorn", "numpy", "playwright"]:
    try: env[m] = importlib.import_module(m).__version__
    except Exception as e: env[m] = f"n/a ({type(e).__name__})"
try: env["backend_health"] = json.loads(urllib.request.urlopen("http://localhost:8000/api/hmm_info", timeout=5).read())
except Exception as e: env["backend_health"] = repr(e)
(HERE/"results/env.json").write_text(json.dumps(env, indent=1, ensure_ascii=False)); print(json.dumps(env, indent=1, ensure_ascii=False)[:1800])
