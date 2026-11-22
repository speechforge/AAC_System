# Patches: archived system (commit fe4e185) -> repaired system (working tree)
* `revised_system_tracked_files.patch`: `git diff` of the five modified tracked files (backend `app.py`, `llm.py`, `semantic.py`, `tts.py`; frontend `index.html`).
* `new_files/`: four new backend files (`aac_lexicon.py` locale rules and selection analysis, `templates.py` compositional templates, `pipeline.py` request normalisation and decision policy, `board_concepts.json` concept registry).
* The archived originals are in `../archived_system/` (hash list in `../config/archived_system_sha256.txt`). The repaired files are frozen by `../config/freeze_manifest.json` (SHA-256).
Apply to a clean checkout of fe4e185: `git apply revised_system_tracked_files.patch && cp new_files/* indic-generative-aac/backend/`.
