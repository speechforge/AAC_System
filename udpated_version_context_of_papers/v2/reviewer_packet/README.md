# Reviewer packet (status: PENDING; no ratings collected)
Built 2026-11-13T10:55:58Z from the holdout split, input mode 'rev', frozen system (config/freeze_manifest.json).
Files: packet_<lang>_R1.csv / _R2.csv (give one to each of two independent native raters per language), RATER_INSTRUCTIONS.md, ADJUDICATION.md,
KEY_DO_NOT_SHARE_WITH_RATERS.csv (maps neutral IDs to systems; analysts only), analyze_ratings.py (run after ratings return).
Items: 120 scenarios (all with both outputs); pairs per language R1/R2 each: 30. Fixtures are DRAFT until the same raters confirm gold concepts, act and polarity.

**Composition (analysts only).** 120 scenarios, 30 per language, each rated by two independent raters per language (30 rows per file, 8 files). In 88 of the 120 scenarios the hybrid fell back to the template, so both outputs are the same string (they stay in the packet as blind controls: a rater should answer 'tie'); in 32 scenarios the two outputs differ and carry the information about phrasing. The prespecified analysis reports (a) all assigned pairs and (b) the subset in which both outputs preserve meaning per the adjudicated judgments. Human outcomes: **PENDING** (`results/audit/D_ratings_status.json`).
