"""Pure Phase 1 checks; model and speech engines are not loaded."""
import sys,json,subprocess,unittest,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
import aac_lexicon as L,pipeline,templates
class PhaseOne(unittest.TestCase):
 def test_registry_generated(self):subprocess.run([sys.executable,str(ROOT/'scripts/build_board_asset.py'),'--check'],check=True)
 def test_legacy_board_parity(self):
  code="const fs=require('fs'),vm=require('vm');let h=fs.readFileSync('frontend/index.html','utf8'),a=h.indexOf('const SYMBOL_DATABASE ='),b=h.indexOf('function visualItem',a);console.log(vm.runInNewContext(h.slice(a,b)+';JSON.stringify(SYMBOL_DATABASE)'));"
  legacy=json.loads(subprocess.run(['node','-e',code],cwd=ROOT,text=True,capture_output=True,check=True).stdout)
  flat={item['k']:{'cat':cat,'emoji':item['e'],**item['labels']} for cat,items in legacy.items() for item in items}
  self.assertEqual(flat,L.BOARD)
 def test_analyzer_parity(self):
  cases=[]
  for lg in L.LANGS:
   for ids in [['NO'],['NO','TEA'],['NO','HAPPY'],['ANGRY','FOOD'],['EAT','FOOD'],['NO','NO','TEA'],['WATER'],['MORE','WATER'],['NAMASTE'],['WANT','MOTHER']]:
    for forced in [None,'REQUEST','FEELING','FEELING_REQUEST','QUESTION']:
     cases.append(dict(language=lg,forced=forced,items=[dict(cid=cid,label=L.BOARD[cid][lg]) for cid in ids]))
   cases.extend([dict(language=lg,forced=None,items=[dict(cid=None,label='Ravindra')]),dict(language=lg,forced=None,items=[dict(cid=None,label=L.BOARD['FOOD'][lg]),dict(cid='WATER',label=L.BOARD['WATER'][lg])])])
  code="global.window=global;require('./frontend/board-registry.js');require('./frontend/vnext-logic.js');let input='';process.stdin.on('data',x=>input+=x);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(input).map(c=>AACVNext.analyze(c.items,c.language,c.forced)))));"
  js=json.loads(subprocess.run(['node','-e',code],cwd=ROOT,input=json.dumps(cases),text=True,capture_output=True,check=True).stdout)
  failures=[]
  for case,actual in zip(cases,js):
   expected=L.analyze_selection(case['items'],case['language'],case['forced'])
   for key in ['act','negation','ambiguous','frame','n_negators','content']:
    if expected[key]!=actual[key]:failures.append((case,key,expected[key],actual[key]))
  self.assertEqual(failures,[]);print('JS/Python parity:',len(cases),'cases')
 def test_refusals_and_ambiguity(self):
  items=lambda ids,lg:[dict(cid=i,label=L.BOARD[i][lg]) for i in ids]
  result=templates.realize(items(['NO','TEA'],'gu'),'gu');self.assertEqual(result['text'],'મને ચા નથી જોઈતી.')
  self.assertEqual(templates.realize(items(['NO','HAPPY'],'mr'),'mr')['status'],'ok')
  for ids,reason in [(['NO','NO','TEA'],'repeated_negation'),(['ANGRY','FOOD'],'angry_food')]:
   ctx=pipeline.normalize_request(dict(entities=[L.BOARD[i]['en'] for i in ids],concept_ids=ids,language='en',act='REQUEST',act_source='client'))
   result=pipeline.decide(ctx,'en',lambda _:self.fail('Ambiguity must not generate'),object(),None)
   self.assertEqual(result['outcome'],'clarification');self.assertEqual(result['route'],reason)
 def test_text_only_default_and_gate(self):
  tree=ast.parse((ROOT/'backend/app.py').read_text());req=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='AACRequest')
  node=next(n for n in req.body if isinstance(n,ast.AnnAssign) and n.target.id=='include_audio');self.assertIs(node.value.value,True)
  guard=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='speak_ok and req.include_audio');self.assertTrue(guard.body)
 def test_pack_integrity(self):
  import hashlib,wave
  pack=json.loads((ROOT/'frontend/quick-pack.json').read_text());self.assertEqual(len(pack['phrases']),16)
  for item in pack['phrases']:
   path=ROOT/'frontend'/item['audio'].removeprefix('/static/');self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),item['sha256'])
   with wave.open(str(path)) as w:self.assertGreater(w.getnframes(),0)
if __name__=='__main__':unittest.main()
