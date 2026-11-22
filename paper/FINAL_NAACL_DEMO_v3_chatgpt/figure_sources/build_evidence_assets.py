#!/usr/bin/env python3
"""Deterministically regenerate tables and qualitative traces from preserved results.
No holdout scores are read or included. Run from the repository root.
"""
from pathlib import Path
import csv,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'paper/FINAL_NAACL_DEMO_v3_chatgpt'
TEX=OUT/'latex_source_v3'
OLD=ROOT/'paper/CLAUDE_WRITTEN/naacl2027_demo/eval/results'
NEW=ROOT/'udpated_version_context_of_papers/v2'
def readcsv(p):return list(csv.DictReader(p.open()))
def readjsonl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def write(p,x):p.write_text(x,encoding='utf-8')
def esc(x):
 for a,b in [('\\',r'\textbackslash{}'),('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]:x=x.replace(a,b)
 return x
LANGS=['en','hi','gu','mr']; NAMES=dict(zip(LANGS,['English','Hindi','Gujarati','Marathi']))
def native(x,l):
 x=esc(x)
 return (r'\gu{'+x+'}') if l=='gu' else ((r'\hi{'+x+'}') if l in ['hi','mr'] else x)
old=readcsv(OLD/'scored.csv')
new=readcsv(NEW/'results/scored/legacy_scored.csv')
fixtures={x['id']:x for x in readjsonl(NEW/'fixtures/legacy/scenarios.jsonl')}
streams={x['id']:x for x in readjsonl(NEW/'results/streams/legacy_remote_g1rev_shard0of1.jsonl')}
# Table 2: original scoring retained; new scoring is a separate panel.
lines=[r'\begin{table*}[t]',r'\centering\small',r'\setlength{\tabcolsep}{5pt}',r'\begin{tabular}{@{}L{5.8cm}ccccc@{}}',r'\toprule',r'System / condition & English & Hindi & Gujarati & Marathi & Pooled \\',r'\midrule']
counts={}
for cond,label in [('ui','A. Archived web client; scorer v1'),('st','B. Archived explicit gold act and polarity; scorer v1')]:
 lines.append(r'\multicolumn{6}{@{}l}{\textit{'+label+r'}}\\')
 for system,name in [('naive_qwen','Unconstrained Qwen (diagnostic)'),('llm3_pre','Cascade before checking'),('deployed','Gate + retry + fallback'),('template_only','Matched template baseline')]:
  if cond=='st' and system=='naive_qwen':continue
  vals=[]
  for lang in LANGS:
   rs=[x for x in old if x['lang']==lang and x['system']==system and x['cond']==cond and x['code_mix']=='False' and x['overlap']=='False']
   assert rs,(cond,system,lang)
   vals.append((sum(x['success']=='True' for x in rs),len(rs)))
  vals.append(tuple(sum(v[i] for v in vals) for i in [0,1]))
  counts[f'{system}|{cond}']=vals
  lines.append(name+' & '+' & '.join(f'{a}/{b}' for a,b in vals)+r' \\')
 lines.append(r'\midrule')
lines.append(r'\multicolumn{6}{@{}l}{\textit{C. Revised browser path; scorer v2; regression only}}\\')
for system,name in [('revised_cascade_first','Revised cascade before checking'),('revised_hybrid','Revised gate + retry + checked fallback'),('template_revised','Repaired template baseline')]:
 rs=[x for x in new if x['system']==system and x['mode']=='rev' and x['code_mix']=='False']
 vals=[]
 for lang in LANGS:
  xs=[x for x in rs if x['lang']==lang];assert xs
  vals.append((sum(x['success']=='True' for x in xs),len(xs)))
 vals.append(tuple(sum(v[i] for v in vals) for i in [0,1]))
 counts[system+'|rev']=vals
 lines.append(name+' & '+' & '.join(f'{a}/{b}' for a,b in vals)+r' \\')
lines += [r'\bottomrule',r'\end{tabular}',r'\caption{Scenario success as counts over the same 175 selections. Panels A and B reproduce the archived lexical scorer; panel C is a scorer-v2 regression comparison on scenarios that informed the repairs. Scores across scorers are not directly comparable. English is a language reference; Hindi, Gujarati, and Marathi evaluate language extensions. The template is the method baseline in every language.}',r'\label{tab:results}',r'\end{table*}']
write(TEX/'generated/tab_results.tex','\n'.join(lines)+'\n')
# Table 3 from integer prediction counts, not rounded table cells.
pred=json.loads((OLD/'prediction.json').read_text());counts_pred=readcsv(NEW/'results/audit/A8_prediction_counts.csv')
hmm=json.loads((OLD/'hmm_eval.json').read_text())
lines=[r'\begin{table}[t]',r'\centering\footnotesize',r'\setlength{\tabcolsep}{3pt}',r'\begin{tabular}{@{}lrrrrrr@{}}',r'\toprule',r'&\multicolumn{3}{c}{English (reference)}&\multicolumn{3}{c}{Hindi}\\',r'\cmidrule(lr){2-4}\cmidrule(l){5-7}',r'Model & @1 & @5 & MRR & @1 & @5 & MRR \\',r'\midrule']
for system,name in [('unigram_frequency','Unigram'),('bigram_backoff','Bigram backoff'),('trigram_backoff','Trigram backoff'),('infinity_gram_deployed',r'Suffix trie ($\infty$-gram)')]:
 vals=[]
 for lang in ['en','hi']:
  q=next(x for x in counts_pred if x['language']==lang and x['system']==system)
  vals.extend([f"{100*int(q['hit1_count'])/int(q['n_items']):.1f}",f"{100*int(q['hit5_count'])/int(q['n_items']):.1f}",f"{pred[lang]['systems'][system]['mrr']['value']:.3f}"])
 lines.append(name+' & '+' & '.join(vals)+r' \\')
# Preserve the two independently evaluated HMM baselines from v2.
lines += [r'Gutenberg HMM & 6.7 & 15.5 & 0.105 & -- & -- & -- \\',r'Hindi AAC HMM & -- & -- & -- & 24.5 & 41.9 & 0.315 \\',r'\midrule',r'\multicolumn{7}{@{}l}{Gujarati: no matched evaluation; shelf returns English.}\\',r'\multicolumn{7}{@{}l}{Marathi: no matched evaluation; reuses Hindi predictor.}\\',r'\bottomrule',r'\end{tabular}',r'\caption{Next-word prediction on AAC-user utterances from 60 of 300 source conversations per evaluated language (240 training; every fifth source held out). There are 2,220 English and 2,437 Hindi prediction contexts. Hit@1 and hit@5 are percentages; MRR is truncated at rank 10. Unigram is the frequency baseline. Dashes denote unmeasured cells, not zero performance.}',r'\label{tab:pred}',r'\end{table}']
write(TEX/'generated/tab_pred.tex','\n'.join(lines)+'\n')
# Representative recorded traces: same selection in each of four languages.
trace_data=[]; case_data=[]
groups=['T1_request_object-WATER','T2_refuse_object-NO+PIZZA','T3_feeling-TIRED','T4_negated_feeling-NO+HAPPY','T5_action_object-DRINK+WATER','T6_help_person-CALL+MOTHER']
for group in groups:
 for lang in LANGS:
  ident=lang+'-'+group
  result=next(x for x in new if x['id']==ident and x['system']=='revised_hybrid' and x['mode']=='rev')
  f=fixtures[ident];t=streams[ident]
  d=dict(id=ident,group=group,language=lang,labels=f['labels'],act=f['gold_act'],negative=f['gold_neg'],candidate=t['attempts'][0]['text'],attempts=[a['text'] for a in t['attempts']],returned=result['text'],route=result['route'],gate_reasons=result['gate_reasons'],lexical_success=result['success'],source_stream='results/streams/legacy_remote_g1rev_shard0of1.jsonl',source_scored='results/scored/legacy_scored.csv',scorer='v2',scope='regression, native review pending')
  case_data.append(d)
  if group in groups[:2]:trace_data.append(d)
write(OUT/'evidence/figure4_traces.json',json.dumps(trace_data,ensure_ascii=False,indent=2)+'\n')
write(OUT/'evidence/appendix_cases.json',json.dumps(case_data,ensure_ascii=False,indent=2)+'\n')
lines=[r'\begingroup\footnotesize',r'\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.15}',r'\begin{tabular}{@{}L{1.3cm}L{2.2cm}L{4.1cm}L{2.9cm}L{4.0cm}@{}}',r'\toprule',r'Language & 1. Selection & 2. First candidate & 3. Check / route & 4. Returned text \\',r'\midrule']
for group,head in [(groups[0],'A. Water request (positive polarity)'),(groups[1],'B. Pizza refusal (negative polarity)')]:
 lines.append(r'\multicolumn{5}{@{}l}{\textbf{'+head+r'}}\\')
 for d in [x for x in trace_data if x['group']==group]:
  l=d['language'];candidate=native(d['candidate'],l)
  if l=='en' and group==groups[0]:candidate=r'I need \bad{food}.\newline\bad{[added: food; water missing]}'
  elif l=='en' and group==groups[1]:candidate=r'I cannot \bad{eat out} because I am .\newline\bad{[added: action/reason; pizza missing]}'
  else:candidate=r'\good{'+candidate+'}'
  if d['route']=='model_first':decision=r'Pass; model text'
  elif 'negation_missing' in d['gate_reasons']:decision=r'Reject: negation missing; checked template'
  else:decision=r'Reject: concept mismatch; checked template'
  name=NAMES[l]+(r'\newline\textit{reference}' if l=='en' else r'\newline\textit{extension}')
  labels=native(' + '.join(d['labels']),l)
  final=r'\kept{'+native(d['returned'],l)+'}'
  lines.append(name+' & '+labels+' & '+candidate+' & '+decision+' & '+final+r' \\')
 lines.append(r'\midrule')
lines[-1]=r'\bottomrule'
lines += [r'\end{tabular}',r'\endgroup']
write(TEX/'generated/trace_panel.tex','\n'.join(lines)+'\n')
# Table 4: six scenario families, all four languages, including an accepted awkward output.
lines=[r'\begin{table*}[t]',r'\centering\footnotesize',r'\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.13}',r'\begin{tabular}{@{}L{2.7cm}L{3.7cm}L{8.5cm}@{}}',r'\toprule',r'Selection / intended act & English returned text & Indic selections $\longrightarrow$ returned text \\',r'\midrule']
heads=['Water / request','No + Pizza / refusal','Tired / feeling','No + Happy / negated feeling','Drink + Water / action request','Call + Mother / call request']
for group,head in zip(groups,heads):
 en=next(x for x in case_data if x['group']==group and x['language']=='en')
 cells=[]
 for l in ['hi','gu','mr']:
  d=next(x for x in case_data if x['group']==group and x['language']==l)
  short={'hi':'HI','gu':'GU','mr':'MR'}[l]
  cells.append(r'\textbf{'+short+'} '+native(' + '.join(d['labels']),l)+r' $\rightarrow$ \good{'+native(d['returned'],l)+'}')
 lines.append(esc(head)+' & '+r'\good{'+esc(en['returned'])+'} & '+r'\newline '.join(cells)+r' \\')
lines += [r'\bottomrule',r'\end{tabular}',r'\caption{Representative recorded revised-browser regression cases: one underlying message per archived family, shown in all four languages. HI: Hindi; GU: Gujarati; MR: Marathi. Act and polarity are supplied separately from the visible labels. These are exact system outputs, including awkward accepted constructions (e.g., the Marathi tiredness report and Hindi call request). Colour indicates an example, not human validation.}',r'\label{tab:cases}',r'\end{table*}']
write(TEX/'generated/tab_cases.tex','\n'.join(lines)+'\n')
# Original captures are copied without altering their content.
for src,dst in [('2_rejection_and_fallback.png','ui_fallback.png'),('3_clarification.png','ui_clarification.png')]:
 shutil.copy2(NEW/'reviewer_packet/demo_captures'/src,TEX/'figures'/dst)
# Source copies for the numerical audit. No draft holdout score is packaged.
for file in ['A1_claims_check.csv','A3_failure_classification.csv','A3_classification_summary.json','A6_feeling_denominator.json','A7_paired_ci_recomputed.json','A8_prediction_counts.csv','A8_prediction_audit.json','B_speech_path.json','D_clean_env_test.json','D_ratings_status.json']:
 shutil.copy2(NEW/'results/audit'/file,OUT/'evidence'/file)
for file in ['T1_success_legacy.csv','T2_paired_legacy.csv']:
 shutil.copy2(NEW/'results/tables'/file,OUT/'evidence'/file)
for file in ['prediction.json','hmm_eval.json','summary.json']:
 shutil.copy2(OLD/file,OUT/'evidence'/('archived_'+file))
provenance={'scope':'archived v1 and regression v2 only; no holdout performance','table2_counts':counts,'sources':[]}
for p in [OLD/'scored.csv',OLD/'prediction.json',OLD/'hmm_eval.json',NEW/'results/scored/legacy_scored.csv',NEW/'results/streams/legacy_remote_g1rev_shard0of1.jsonl',NEW/'fixtures/legacy/scenarios.jsonl']:
 provenance['sources'].append({'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
write(OUT/'evidence/assets.source.json',json.dumps(provenance,indent=2)+'\n')
print('Regenerated Tables 2--4, Figure 4, exact trace JSON, and evidence provenance.')
