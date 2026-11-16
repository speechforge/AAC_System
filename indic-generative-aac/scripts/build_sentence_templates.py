"""Build instant public sentence previews from the EXISTING backend realizer and semantic gate.
No new words or heuristic sentences are authored by the browser. Unsupported/ambiguous frames are omitted.
"""
from pathlib import Path
import json,sys,itertools
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'backend'))
import aac_lexicon as L,templates,pipeline
from semantic import SemanticValidator
G=SemanticValidator();bank={};ids=list(L.BOARD)
pairs=list(itertools.product([i for i in ids if L.BOARD[i]['cat']=='actions'],L.OBJECTS))+list(itertools.product(L.FEELINGS,L.OBJECTS))+list(itertools.product(['HELP','CALL'],L.PEOPLE))+list(itertools.product(['GO'],L.PLACES))
for lg in L.LANGS:
 for seq in [[i] for i in ids]+[list(x) for x in pairs]:
  for neg in [False,True]:
   for more in [False,True]:
    selected=(['NO'] if neg else [])+(['MORE'] if more else [])+seq
    items=[dict(cid=i,label=L.BOARD[i][lg]) for i in selected];a=L.analyze_selection(items,lg)
    if a['ambiguous']:continue
    ctx=pipeline.normalize_request(dict(entities=[i['label'] for i in items],concept_ids=selected,language=lg,act=a['act'],act_source='client',negation=a['negation']))
    if ctx.get('clarification_reason'):continue
    result=templates.realize(items,lg)
    if result['status']!='ok':continue
    valid,_=G.validate(ctx,{},result['text'],lg)
    if not valid:continue
    content=[('MORE:' if x.get('more') else '')+x['cid'] for x in a['content']]
    key=json.dumps([lg,a['act'],a['negation'],content],ensure_ascii=False,separators=(',',':'))
    bank[key]=dict(text=result['text'],act=a['act'],negation=a['negation'],validated=True,outcome='sentence_template',route='local_checked_template')
p=R/'frontend/sentence-templates.json';p.write_text(json.dumps({'version':1,'source':'backend/templates.py + semantic gate','sentences':bank},ensure_ascii=False,separators=(',',':')));print('Checked public sentence previews:',len(bank))
