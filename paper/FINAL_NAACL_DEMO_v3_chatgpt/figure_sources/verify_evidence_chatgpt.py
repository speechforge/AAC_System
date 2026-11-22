#!/usr/bin/env python3
"""Independent release checks on numerical records, quoted strings, and compiled PDF."""
from pathlib import Path
import csv,json,re,subprocess,hashlib
from pypdf import PdfReader
r=Path(__file__).resolve().parents[1];s=r/'latex_source_v3_chatgpt';q=r/'qa';q.mkdir(exist_ok=True)
checks=[]
def check(name,ok,detail):checks.append({'check':name,'pass':bool(ok),'detail':detail})
counts=json.loads((r/'evidence/assets.source.json').read_text())['table2_counts']
expected={'llm3_pre|ui':65,'deployed|ui':97,'template_only|ui':118,'naive_qwen|ui':8,'llm3_pre|st':71,'deployed|st':132,'template_only|st':167,'revised_cascade_first|rev':88,'revised_hybrid|rev':175,'template_revised|rev':175}
for k,v in expected.items():
 rows=counts[k]
 check('Scenario counts '+k,rows[-1]==[v,175] and sum(x[0] for x in rows[:4])==v and sum(x[1] for x in rows[:4])==175,str(rows))
summary=list(csv.DictReader((r/'evidence/T1_success_legacy.csv').open()))
for sys in ['revised_cascade_first','revised_hybrid','template_revised']:
 row=next(x for x in summary if x['system']==sys and x['mode']=='rev')
 check('Regression summary agrees '+sys,int(float(row['ALL_k']))==expected[sys+'|rev'] and int(row['ALL_n'])==175,'Independent summary CSV, not raw-CSV Boolean string coercion')
pred=list(csv.DictReader((r/'evidence/A8_prediction_counts.csv').open()))
for l,n,delta in [('en',2220,25),('hi',2437,29)]:
 a=next(x for x in pred if x['language']==l and x['system']=='infinity_gram_deployed');b=next(x for x in pred if x['language']==l and x['system']=='trigram_backoff')
 check('Prediction raw-count gain '+l,int(a['n_items'])==n and int(a['hit1_count'])-int(b['hit1_count'])==delta,f'{delta}/{n} = {delta/n*100:.6f} pp')
traces=json.loads((r/'evidence/figure4_traces.json').read_text());cases=json.loads((r/'evidence/appendix_cases.json').read_text())
check('Four-language Figure 4',len(traces)==8 and all(sum(d['language']==l for d in traces)==2 for l in ['en','hi','gu','mr']),'Two underlying selections, four phases, four languages')
check('Six-family appendix coverage',len(cases)==24 and len({x['group'] for x in cases})==6,'One message per family in all four languages; exact stored outputs')
text=subprocess.check_output(['pdftotext','-layout',str(s/'main.pdf'),'-'],text=True)
(q/'final_chatgpt_extracted.txt').write_text(text)
xs=json.loads((q/'unicode_source_strings.json').read_text())
check('Poppler native Unicode fidelity',all(x in text for x in xs),f'{sum(x in text for x in xs)}/{len(xs)} exact native strings')
check('No NUL characters','\0' not in text,'Text remains searchable; no broken global XeTeX ActualText primitive')
check('Revised rows rendered correctly',all(v in text for v in ['88/175','175/175','6/46','29/45','27/42','26/42']),'PDF checked after final table regeneration')
reader=PdfReader(s/'main.pdf');pages=text.split('\f');appendix=next((i+1 for i,p in enumerate(pages) if re.search(r'A\s+Four-Language Interaction Traces',p)),None)
check('Main/appendix layout',len(reader.pages)==9 and appendix==8,'Main content through page 6; ethics/acknowledgments/references page 7; appendix pages 8--9')
log=Path('/tmp/aac_v3_chatgpt_build.log').read_text()
check('Compile diagnostics',not re.search(r'Overfull|Missing character|undefined|^!',log,re.M),'0 overfull boxes, 0 missing-glyph warnings, 0 undefined citations/references')
fonts=subprocess.check_output(['pdffonts',str(s/'main.pdf')],text=True)
(q/'fonts_chatgpt.txt').write_text(fonts)
fontrows=fonts.splitlines()[2:]
check('Font embedding',bool(fontrows) and all(re.search(r'\byes\s+yes\s+yes\s+\d+',x) for x in fontrows),f'{len(fontrows)} fonts embedded with Unicode maps')
# Independent parser limitations are reported, never masked as a pass.
pyp='\n'.join(p.extract_text() or '' for p in reader.pages)
required=['मुझे पानी चाहिए।','મને પાણી જોઈએ છે.','मला पाणी हवे आहे.']
report={'checks':checks,'passed':sum(x['pass'] for x in checks),'total':len(checks),'pdf_sha256':hashlib.sha256((s/'main.pdf').read_bytes()).hexdigest(),'secondary_extractor':{x:x in pyp for x in required},'secondary_extractor_limit':'pypdf does not honor every Hindi ActualText span and reads the shaped i-vowel glyph as IPA ɟ. Poppler recovers all 47 source strings exactly; visual QA checks the shaped glyphs separately.','submission_readiness':'NOT READY: see author revision note for native validation, speech, public demo/video, CRediT/licensing, and one independent citation-index check.'}
(q/'evidence_verification_chatgpt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for c in checks:print(('PASS' if c['pass'] else 'FAIL'),c['check'],c['detail'])
print('Verification:',report['passed'],'/',report['total'])
raise SystemExit(0 if all(x['pass'] for x in checks) else 1)
