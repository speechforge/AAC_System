import csv,io,json,tempfile,unittest,sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app,ROOT,PARTICIPANT_COLUMNS,Store

class PortalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.app=create_app(ROOT,Path(self.tmp.name));self.store=self.app.state.store
  self.client=TestClient(self.app);self.admin=TestClient(self.app)
  password=next(x.removeprefix('Password: ') for x in (ROOT/'.state/ADMIN_CREDENTIALS.txt').read_text().splitlines() if x.startswith('Password: '))
  login=self.admin.post('/api/admin/login',json={'username':'mos_admin','password':password});self.assertEqual(login.status_code,200);self.csrf=login.json()['csrf']
 def tearDown(self):self.client.close();self.admin.close();self.tmp.cleanup()
 def register(self,client=None,email='listener@example.org',name='Test Listener'):
  response=(client or self.client).post('/api/register',json={'name':name,'email':email,'age':24,'gender':'Female','mother_tongue':'Gujarati','organization':'Speech Lab','consent':True,'instructions_understood':True})
  self.assertEqual(response.status_code,200,response.text);return response.json()
 def listen(self,client,clip):
  self.assertEqual(client.post('/api/playback',json={'clip_id':clip['id'],'event':'started'}).status_code,200)
  # Explicit timing fixture. Unit checks do not claim real audio playback.
  with self.store.write() as db:db.execute('UPDATE trials SET play_started=play_started-? WHERE clip_id=?',(clip['duration']+1,clip['id']))
  response=client.post('/api/playback',json={'clip_id':clip['id'],'event':'ended','listened_seconds':clip['duration']});self.assertEqual(response.status_code,200,response.text)
 def complete(self,client,state,score):
  while not state['completed']:
   clip=state['current'];self.listen(client,clip);r=client.post('/api/rate',json={'clip_id':clip['id'],'score':score});self.assertEqual(r.status_code,200,r.text);state=r.json()
  return state
 def test_registration_schema_assignment_and_empty_statistics(self):
  state=self.register();pid=state['participant']['participant_id'];self.assertEqual(state['participant']['trials_completed'],0)
  with self.store.connect() as db:rows=db.execute('SELECT clip_id,position FROM trials WHERE participant_id=?',(pid,)).fetchall()
  self.assertEqual(len(rows),20);self.assertEqual(len({r['clip_id'] for r in rows}),20)
  for lang in ('en','hi','gu','mr'):self.assertEqual(sum(r['clip_id'].startswith(lang+'-') for r in rows),5)
  self.assertEqual(next(csv.reader([(self.store.directory/'participants.csv').read_text().splitlines()[0]])),PARTICIPANT_COLUMNS)
  report=self.admin.get('/api/admin/dashboard').json();self.assertIsNone(report['overall']['mos']);self.assertEqual(report['counts']['registered'],1);self.assertTrue(all(x['mos'] is None for x in report['languages']))
 def test_playback_required_and_scores_are_strict_integers(self):
  clip=self.register()['current'];self.assertEqual(self.client.post('/api/rate',json={'clip_id':clip['id'],'score':4}).status_code,400)
  for score in (0,6,True,3.5,'4'):self.assertEqual(self.client.post('/api/rate',json={'clip_id':clip['id'],'score':score}).status_code,422)
  self.client.post('/api/playback',json={'clip_id':clip['id'],'event':'started'})
  self.assertEqual(self.client.post('/api/playback',json={'clip_id':clip['id'],'event':'ended','listened_seconds':clip['duration']}).status_code,400)
  self.listen(self.client,clip);saved=self.client.post('/api/rate',json={'clip_id':clip['id'],'score':4});self.assertEqual(saved.status_code,200);self.assertEqual(saved.json()['participant']['trials_completed'],1)
 def test_retry_concurrency_does_not_double_count(self):
  clip=self.register()['current'];self.listen(self.client,clip)
  def submit(_):return self.client.post('/api/rate',json={'clip_id':clip['id'],'score':4}).status_code
  with ThreadPoolExecutor(max_workers=5) as pool:self.assertEqual(list(pool.map(submit,range(5))),[200]*5)
  self.assertEqual(self.client.get('/api/me').json()['participant']['trials_completed'],1)
  self.assertEqual(self.client.post('/api/rate',json={'clip_id':clip['id'],'score':2}).status_code,409)
 def test_resume_and_storage_persist(self):
  state=self.register();clip=state['current'];self.listen(self.client,clip);self.client.post('/api/rate',json={'clip_id':clip['id'],'score':3})
  current=self.client.get('/api/me').json()['current']['id'];self.client.post('/api/leave',json={});self.assertEqual(self.client.get('/api/me').status_code,401)
  body={'participant_id':state['participant']['participant_id'],'code':state['return_code']}
  self.assertEqual(self.client.post('/api/resume',json={**body,'code':'WRONG-CODE'}).status_code,401)
  self.assertEqual(self.client.post('/api/resume',json=body).json()['current']['id'],current)
  fresh=Store(self.store.directory)
  with fresh.connect() as db:self.assertEqual(db.execute('SELECT trials_completed FROM participants').fetchone()[0],1)
  self.assertNotIn(state['return_code'],(self.store.directory/'participants.csv').read_text())
 def test_language_mos_bootstrap_and_exclusion(self):
  first=self.register();self.complete(self.client,first,1);other=TestClient(self.app);second=self.register(other,email='second@example.org');self.complete(other,second,5)
  report=self.admin.get('/api/admin/dashboard').json();self.assertEqual(report['overall']['mos'],3);self.assertEqual(report['overall']['n'],40);self.assertEqual(report['counts']['completed'],2)
  for lang in report['languages']:
   self.assertEqual(lang['mos'],3);self.assertEqual(lang['n'],10);self.assertEqual(lang['participants'],2);self.assertEqual(lang['ci95'],[1,5])
  export=self.admin.get('/api/admin/export/languages?participant_id='+first['participant']['participant_id']).text.lstrip('\ufeff')
  self.assertTrue(all(float(r['mos'])==1 for r in csv.DictReader(io.StringIO(export))))
  path='/api/admin/participants/'+first['participant']['participant_id']+'/exclusion'
  self.assertEqual(self.admin.post(path,json={'excluded':True,'reason':'Calibration'}).status_code,403)
  self.assertEqual(self.admin.post(path,json={'excluded':True,'reason':''},headers={'X-CSRF-Token':self.csrf}).status_code,400)
  self.assertEqual(self.admin.post(path,json={'excluded':True,'reason':'Calibration'},headers={'X-CSRF-Token':self.csrf}).status_code,200)
  self.assertEqual(self.client.get('/api/me').status_code,403);self.assertEqual(self.admin.get('/api/admin/dashboard').json()['overall']['mos'],5)
  rows=list(csv.DictReader(io.StringIO(self.admin.get('/api/admin/export/ratings').text.lstrip('\ufeff'))));self.assertEqual(len(rows),40)
  self.assertIn('Calibration',self.admin.get('/api/admin/export/audit').text);other.close()
 def test_incomplete_sessions_are_explicitly_filtered(self):
  state=self.register();self.listen(self.client,state['current']);self.client.post('/api/rate',json={'clip_id':state['current']['id'],'score':2})
  self.assertIsNone(self.admin.get('/api/admin/dashboard').json()['overall']['mos'])
  report=self.admin.get('/api/admin/dashboard?include_partial=true').json();self.assertEqual(report['overall']['mos'],2);self.assertIsNone(report['overall']['ci95'])
 def test_private_routes_origin_and_csv_formula_safety(self):
  anon=TestClient(self.app)
  for path in ('/api/admin/dashboard','/api/admin/export/participants','/api/audio/en-01'):self.assertEqual(anon.get(path).status_code,401)
  for path in ('/.data/portal.sqlite3','/.state/ADMIN_CREDENTIALS.txt'):self.assertEqual(anon.get(path).status_code,404)
  self.assertEqual(anon.post('/api/admin/login',json={'username':'x','password':'x'},headers={'Origin':'https://foreign.example'}).status_code,403)
  self.assertEqual(anon.get('/api/health',headers={'Host':'unknown.trycloudflare.com'}).status_code,403)
  self.assertEqual(anon.post('/api/admin/login',json={'username':'अ','password':'x'}).status_code,401)
  self.register(name='=IMPORTDATA("test")')
  row=next(csv.DictReader(io.StringIO(self.admin.get('/api/admin/export/participants').text.lstrip('\ufeff'))));self.assertTrue(row['name'].startswith("'="));anon.close()
 def test_instruction_acknowledgement_and_shuffled_orders(self):
  body={'name':'New Listener','email':'instructions@example.org','age':24,'gender':'Female','mother_tongue':'Gujarati','organization':'Lab','consent':True}
  self.assertEqual(self.client.post('/api/register',json=body).status_code,400)
  first=self.register();other=TestClient(self.app);second=self.register(other,email='shuffle@example.org')
  with self.store.connect() as db:
   def order(pid):return [r[0] for r in db.execute('SELECT clip_id FROM trials WHERE participant_id=? ORDER BY position',(pid,))]
   a=order(first['participant']['participant_id']);b=order(second['participant']['participant_id'])
  self.assertEqual(set(a),set(b));self.assertNotEqual(a,b);other.close()
 def test_duplicate_email_and_invalid_registration(self):
  self.register();body={'name':'Another Listener','email':'LISTENER@example.org','age':25,'gender':'Male','mother_tongue':'Hindi','organization':'Lab','consent':True,'instructions_understood':True}
  self.assertEqual(self.client.post('/api/register',json=body).status_code,409)
  for patch,status in [({'email':'new@example.org','consent':False},400),({'email':'bad'},422),({'email':'new@example.org','age':3.5},422),({'email':'new@example.org','mother_tongue':' '},400)]:self.assertEqual(self.client.post('/api/register',json={**body,**patch}).status_code,status)

if __name__=='__main__':unittest.main()
