#!/usr/bin/env bash
# Rebuild the working source, run every QA check, and copy the final deliverables into after_the_proof_reading_final_version/.
set -euo pipefail
BASE=/home/linux/Documents/aac_system_november_11/AAC_System_merged/paper/FINAL_NAACL_DEMO_v3
WORK=$BASE/latex_paper_here; SRC=$WORK/latex_source_v3; FIN=$BASE/after_the_proof_reading_final_version; QA=$FIN/qa_scripts
export TECTONIC=${TECTONIC:-/usr/lib/chatgpt/resources/plugins/openai-bundled/plugins/latex/bin/tectonic}
export PATH=$PATH:/home/linux/miniconda3/bin
cd "$SRC" && ./build.sh >/tmp/finalize_build.log 2>&1 || { echo "BUILD FAILED"; tail -20 /tmp/finalize_build.log; exit 1; }
PAGES=$(pdfinfo main.pdf | awk '/Pages/{print $2}')
echo "pages: $PAGES"
echo "--- float/ref audit";            { python3 $QA/xref_audit.py "$SRC" 2>/dev/null | tail -5; } || true
echo "--- native text in PDF";         python3 $QA/native_text_check.py "$SRC" main.pdf 2>/dev/null
echo "--- Table 2 recount";            python3 $QA/numbers_check.py /home/linux/Documents/aac_system_november_11/AAC_System_merged/paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results/scored.csv "$SRC/generated/tab_results.tex" | tail -1
echo "--- MOS table recount";           python3 -I $WORK/mos_eval/check_mos.py "$SRC/generated/tab_mos.tex" || true
echo "--- where the body ends";       for p in 6 7; do echo "page $p, first words:"; { pdftotext -f $p -l $p -layout main.pdf - | head -2; } || true; done
echo "--- fonts not embedded:";        pdffonts main.pdf | tail -n +3 | awk '{print $(NF-4)}' | grep -vc yes || true
echo "--- LaTeX problems";             grep -c "Missing character" main.log || true; grep -n "undefined" main.log | grep -v "Font shape" | head -3 || true
# deliverables
rm -rf "$FIN/latex_source_final"; mkdir -p "$FIN/latex_source_final"
rsync -a --exclude='main.aux' --exclude='main.log' --exclude='main.blg' --exclude='main.bbl' --exclude='main.out' "$SRC"/ "$FIN/latex_source_final"/
cp main.pdf "$FIN/Indic_AAC_Studio_NAACL2027_Demo_v3_final.pdf"
cp main.pdf "$WORK/Indic_AAC_Studio_NAACL2027_Demo_v3.pdf"
rm -rf "$FIN/figure_sources"; cp -r "$WORK/figure_sources" "$FIN/figure_sources"
rm -rf "$FIN/mos_eval"; cp -r "$WORK/mos_eval" "$FIN/mos_eval"
rm -rf "$FIN/citation_records"; cp -r "$WORK/citation_records" "$FIN/citation_records"
bash $QA/make_overleaf_zip.sh "$SRC" "$FIN/Indic_AAC_Studio_NAACL2027_Overleaf_v3_final.zip"
cp "$FIN/Indic_AAC_Studio_NAACL2027_Overleaf_v3_final.zip" "$WORK/Indic_AAC_Studio_NAACL2027_Overleaf_v3.zip"
echo "FINALIZED into $FIN"
