Results_10 - frozen baseline snapshot of all results, code and data (saved 2026-11-20).
Purpose: compare any later change (new experiments / app edits) against these numbers. Do NOT edit files here;
make new runs in a new folder (e.g. Results_11) and diff against this one.

Contents
  RESULTS_vs_baseline.txt           full report (English vs baseline paper + hi/mr/gu)
  IMPROVEMENT_PLAN.txt              plan + execution rounds 1 and 2 (shipped vs improved KSR, CIs)
  IMPROVEMENT_PLAN_INDEPTH.txt      in-depth plan with pre-registered success targets
  results_by_language/              per-language text results (en, hi, mr, gu)
  results_json/                     raw JSONs/logs (main_*, llm_en, gen, ablate_*, concept_*, improve_*, final_*)
  code/                             every experiment script used (lib.py, exp_*.py, ...)
  data/                             train/dev/test splits used (en, hi, mr, gu)
  SHA256SUMS.txt                    hashes of every file for integrity checks
Key numbers frozen here (avg KSR %, higher is better): shipped en 56.29 / hi 56.74 / mr 48.73 / gu 53.04;
improved CPU stack 56.82 / 57.94 / 49.38 / 54.25; English adapted OPT-125m (100+100 subsample) 61.88.
Interpreter used for GPU runs: miniconda env taac_env. Git commit at snapshot: 3501e98
