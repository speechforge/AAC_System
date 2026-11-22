#!/usr/bin/env python3
"""Regenerate manuscript tables and exact recorded traces from bundled evidence."""
from pathlib import Path
import json, hashlib

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / 'latex_source_v3' if (ROOT / 'latex_source_v3').is_dir() else ROOT
E = ROOT / 'evidence'
summary = json.loads((E/'archived_summary_v1.json').read_text())
pred = json.loads((E/'prediction.json').read_text())
audit = json.loads((E/'prediction_audit.json').read_text())
traces = json.loads((E/'trace_samples.json').read_text())

def write(name, text):
    p = PAPER/name
    p.parent.mkdir(exist_ok=True, parents=True)
    p.write_text(text+'\n')

def tex(s):
    for a,b in [('\\',r'\textbackslash{}'),('&',r'\&'),('%',r'\%'),('_',r'\_'),('#',r'\#')]:
        s=s.replace(a,b)
    return s

def native(lang, s):
    s=tex(s)
    return ('\\gu{'+s+'}') if lang=='gu' else ('\\hi{'+s+'}') if lang in ('hi','mr') else s

def row(key, label):
    rs=[summary['by_lang'][x][key] for x in ['en','hi','gu','mr']]
    n=sum(x['n'] for x in rs)
    return label+' & '+' & '.join(str(x['success'])+'/'+str(x['n']) for x in rs)+f" & {sum(x['success'] for x in rs)}/{n} & {sum(x['concepts_present'] for x in rs)}/{sum(x['concept_instances'] for x in rs)} & {sum(x['n']-x['polarity_ok'] for x in rs)} & {sum(x['act_wrong'] for x in rs)} & {sum(x['unsupported'] for x in rs)} & {sum(x['offtask'] for x in rs)} \\\\\n"

table=r'''\begin{table*}[t]
\centering\footnotesize
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}lcccccccccc@{}}
\toprule
 & \multicolumn{5}{c}{Scenario success ($k/N$)} & \multicolumn{5}{c}{Pooled diagnostics}\\
\cmidrule(lr){2-6}\cmidrule(l){7-11}
System & EN & HI & GU & MR & All & Kept$\uparrow$ & Pol.$\downarrow$ & Act$\downarrow$ & Added$\downarrow$ & Off-task$\downarrow$\\
\midrule
\multicolumn{11}{@{}l}{\emph{Actual archived browser: act and polarity inferred from labels; scorer v1}}\\
'''
for key,label in [('literal_join|any','Literal join'),('naive_qwen|ui','Single-prompt Qwen'),('llm3_pre|ui','Cascade before gate'),('deployed|ui','Archived policy'),('template_only|ui','Template baseline')]:table+=row(key,label)
table+=r'''\midrule
\multicolumn{11}{@{}l}{\emph{Explicit gold act and polarity: controlled diagnostic; scorer v1}}\\
'''
for key,label in [('llm3_pre|st','Cascade before gate'),('deployed|st','Archived policy'),('template_only|st','Template baseline')]:table+=row(key,label)
table+=r'''\bottomrule
\end{tabular}
\caption{Archived primary comparison. Kept counts required concept instances (215); Pol., Act, Added, and Off-task count scenarios (175) with polarity errors, wrong acts, detected additions, and off-task outputs. Error categories overlap, and missing act cues can also cause failure. Success is lexical scorer-v1 success, not human-assessed meaning. All eight gold-field template failures are Gujarati negated feelings subsequently identified as scorer gaps.}
\label{tab:results}
\end{table*}'''
write('generated/tab_results.tex',table)

defs={}
for name,key in [('WebCascade','llm3_pre|ui'),('WebPolicy','deployed|ui'),('WebTemplate','template_only|ui'),('GoldCascade','llm3_pre|st'),('GoldPolicy','deployed|st'),('GoldTemplate','template_only|st'),('Naive','naive_qwen|ui')]:
    rs=[summary['by_lang'][l][key] for l in ['en','hi','gu','mr']]
    defs[name]=str(sum(x['success'] for x in rs))+'/'+str(sum(x['n'] for x in rs))
write('generated/numbers.tex','\n'.join('\\newcommand{\\'+k+'}{'+v+'}' for k,v in defs.items()))

table=r'''\begin{table}[t]
\centering\footnotesize
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}lrrrrrr@{}}
\toprule
 & \multicolumn{3}{c}{English reference} & \multicolumn{3}{c}{Hindi extension}\\
\cmidrule(lr){2-4}\cmidrule(l){5-7}
Predictor & @1 & @5 & MRR & @1 & @5 & MRR\\
\midrule
'''
for key,label in [('unigram_frequency','Unigram frequency'),('bigram_backoff','Bigram backoff'),('trigram_backoff','Trigram backoff'),('infinity_gram_deployed','Suffix trie')]:
    vals=[]
    for lang in ['en','hi']:
        counts=audit[lang]['counts'][key]
        vals.extend([f"{100*counts['hit1']/counts['n']:.1f}",f"{100*counts['hit5']/counts['n']:.1f}",f"{pred[lang]['systems'][key]['mrr']['value']:.3f}"])
    table+=label+' & '+' & '.join(vals)+r'\\'+'\n'
table+=r'''\midrule
\multicolumn{7}{@{}l}{\emph{Gujarati: not evaluated; Marathi: not evaluated.}}\\
\bottomrule
\end{tabular}
\caption{Next-word prediction on AAC-user utterances from 60 of 300 source conversations per language (240 used for training): 2,220 English and 2,437 Hindi contexts. @1/@5 are hit rates (\%); MRR is reciprocal rank truncated at ten. All predictors use the same language-specific training split. Gujarati and Marathi realization results do not establish predictor performance.}
\label{tab:pred}
\end{table}'''
write('generated/tab_pred.tex',table)

langs={'en':'English reference','hi':'Hindi extension','gu':'Gujarati extension','mr':'Marathi extension'}
table=r'''\small
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.15}
\begin{tabular}{@{}L{2.1cm}L{2.4cm}L{4.0cm}L{2.1cm}L{3.65cm}@{}}
\toprule
Language & 1. Selection & 2. First candidate & 3. Gate / route & 4. Returned text\\
\midrule
'''
for g,title in [('T1_request_object-WATER',r"Request: \emph{``I want water.''}"),('T4_negated_feeling-NO+HAPPY',r"Negated feeling: \emph{``I am not happy.''}")]:
    table+=r'\multicolumn{5}{@{}l}{\textbf{'+title+r'}}\\[2pt]'+'\n'
    for t in (x for x in traces if x['group']==g):
        lang=t['lang']; candidate=native(lang,t['candidate'])
        if lang=='en' and g=='T1_request_object-WATER':candidate='I need '+r'\bad{food}.'+r'\newline\emph{[added: food; water omitted]}'
        elif t['route']!='model_first':candidate=r'\bad{'+candidate+'}'
        else:candidate=r'\good{'+candidate+'}'
        labels=native(lang,' + '.join(t['labels']))
        route='Accept model' if t['route']=='model_first' else 'Reject; checked template'
        table+=r'\lang{'+langs[lang]+'} & '+labels+' & '+candidate+' & '+route+' & '+r'\kept{'+native(lang,t['returned'])+'}'+r'\\[3pt]'+'\n'
    table+=r'\midrule'+'\n'
table=table.rsplit(r'\midrule',1)[0]+r'\bottomrule'+'\n'+r'\end{tabular}'
write('figures/traces.tex',table)

families=[('T2_refuse_object-NO+PIZZA','Refusal'),('T3_feeling-TIRED','Feeling'),('T5_action_object-DRINK+WATER','Action + object'),('T6_help_person-CALL+MOTHER','Call + person')]
table=r'''\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.16}
\begin{tabular}{@{}L{1.85cm}L{1.25cm}L{3.4cm}L{7.7cm}@{}}
\toprule
Family & Language & Selected labels & Recorded returned text (model or template)\\
\midrule
'''
for g,title in families:
    for i,t in enumerate(x for x in traces if x['group']==g):
        lab={'en':'English','hi':'Hindi','gu':'Gujarati','mr':'Marathi'}[t['lang']]
        route='M' if t['route']=='model_first' else 'T'
        table+=(title if i==0 else '')+' & '+lab+' & '+native(t['lang'],' + '.join(t['labels']))+' & '+r'\good{'+native(t['lang'],t['returned'])+'} ('+route+')'+r'\\'+'\n'
    table+=r'\addlinespace[3pt]'+'\n'
table+=r'\bottomrule'+'\n'+r'\end{tabular}'
write('generated/appendix_cases.tex',table)
sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in E.iterdir() if p.is_file() and p.suffix in ('.json','.csv')}
(ROOT/'figure_sources/evidence.source.json').write_text(json.dumps({'sources':sources,'selection_rule':'Water request and negated happy for all four languages; one common message per other legacy family. Illustrative regression traces, not a representative performance estimate.','native_review':'pending','seed':11},indent=2))
print('Generated Table 2, Table 3, Figure 4, case samples, and numeric macros from recorded evidence.')
