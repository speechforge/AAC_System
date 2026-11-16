"""Frozen deterministic replay, not a model comparison or human study. All attempts are retained."""
from pathlib import Path
import sys,json,types,tarfile,time,random,statistics,hashlib
ROOT=Path(__file__).resolve().parents[2];REPO=ROOT.parent;sys.path.insert(0,str(ROOT/'backend'))
import aac_lexicon as L,pipeline,templates
from semantic import SemanticValidator
E=REPO/'docs/aac-redesign/evidence';archive=tarfile.open(E/'baseline-source.tar.gz');before=types.ModuleType('before_pipeline');exec(compile(archive.extractfile('indic-generative-aac/backend/pipeline.py').read(),'baseline/pipeline.py','exec'),before.__dict__)
class Realizer:
 def realize_template(self,ctx,language):
  content=[]
  for item in ctx['content']:
   if item.get('more'):content.append({'cid':'MORE','label':''})
   content.append(item)
  return templates.realize(content,language,ctx['act'] if ctx['act']!='UNKNOWN' else None,ctx['negation'])
source=REPO/'paper/CLAUDE_WRITTEN/naacl2027_demo/eval/fixtures/scenarios.jsonl';cases=[json.loads(x) for x in source.read_text().splitlines()];rows=[];gate=SemanticValidator()
for case in cases:
 for mode in ['inferred','explicit']:
  ids=case['concept_ids'];lg=case['lang'];items=[{'cid':cid,'label':label} for cid,label in zip(ids,case['labels'])];an=L.analyze_selection(items,lg)
  act=case['gold_act'].upper() if mode=='explicit' else an['act'];payload=dict(entities=case['labels'],concept_ids=ids,language=lg,act=act,act_source='user' if mode=='explicit' else 'client',negation=case['gold_neg'],code_mix=case.get('code_mix',False))
  for condition,module in [('before',before),('after',pipeline)]:
   start=time.perf_counter();ctx=module.normalize_request(payload);result=module.decide(ctx,lg,lambda _:None,gate,Realizer(),policy='template_only');elapsed=(time.perf_counter()-start)*1000
   text=result.get('text') or '';ok,detail=gate.validate(ctx,{},text,lg);reasons=detail.get('violations_detected',[]);complete=result['outcome'] in ['sentence_template','sentence_model'] and result['validated']
   rows.append(dict(scenario=case['id'],language=lg,mode=mode,condition=condition,outcome=result['outcome'],text=text,success=bool(complete),all_concepts=bool(complete and not any('missing_concept' in r for r in reasons)),correct_act=bool(complete and not any('act_' in r for r in reasons)),correct_polarity=bool(complete and not any('negation_' in r for r in reasons)),added_concepts=any('added_concept' in r for r in reasons),reasons=reasons,duration_ms=elapsed))
(E/'realization-attempts.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));(E/'realization-source.json').write_text(json.dumps({'path':str(source.relative_to(REPO)),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'scenarios':len(cases),'modes':['explicit','inferred'],'policy':'template_only','model_attempts':0,'seed':2026,'exclusions':0},indent=2));print('Deterministic replay:',len(rows),'attempts across',len(cases),'frozen scenarios; explicit/inferred separate.')
