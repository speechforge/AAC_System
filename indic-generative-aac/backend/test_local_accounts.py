import json,unittest,uuid
from fastapi import FastAPI
from fastapi.testclient import TestClient
import personal_service as p
import local_accounts as a

class AccountsTest(unittest.TestCase):
 def setUp(self):
  self.old=p.PREFIX;p.PREFIX='aac:auth-test:'+uuid.uuid4().hex+':'
  options=dict(p.redis_connection().connection_pool.connection_kwargs);options['db']=15
  self.db=p.SessionStore(p.redis.Redis(**options));app=FastAPI();p.install(app);app.include_router(a.router)
  app.dependency_overrides[p.get_store]=lambda:self.db
  self.client=TestClient(app);self.app=app
 def tearDown(self):
  keys=list(self.db.redis.scan_iter(p.PREFIX+'*'))
  if keys:self.db.redis.delete(*keys)
  self.db.redis.close();p.PREFIX=self.old
 def test_signup_logout_login_and_persistence(self):
  body={'username':'Ravindra','password':'mysecurepassword','name':'Ravindra'}
  result=self.client.post('/api/auth/signup',json=body);self.assertEqual(result.status_code,200,result.text)
  headers={'X-CSRF-Token':result.json()['csrf_token']}
  raw=json.loads(self.db.redis.get(a.key('ravindra')))
  self.assertNotIn('password',raw);self.assertNotEqual(raw['password_hash'],body['password'])
  self.assertEqual(self.client.post('/api/personal/bookmarks',headers=headers,json={'text':'I want water.','language':'en'}).status_code,200)
  cookie=self.client.cookies.get(p.COOKIE)
  self.assertEqual(self.client.delete('/api/session',headers=headers).status_code,200)
  self.assertFalse(self.db.redis.exists(self.db.session_key(cookie)))
  self.assertEqual(self.client.get('/api/session').status_code,401)
  self.assertEqual(self.client.post('/api/auth/signup',json=body).status_code,409)
  self.assertEqual(self.client.post('/api/auth/login',json={'username':'ravindra','password':'wrongpass'}).status_code,401)
  r=self.client.post('/api/auth/login',json={'username':'RAVINDRA','password':body['password']});self.assertEqual(r.status_code,200)
  self.assertEqual(len(self.client.get('/api/personal/dashboard?language=en').json()['bookmarks']),1)
  other=TestClient(self.app);r=other.post('/api/auth/login',json={'username':a.DEMO_USERNAME,'password':a.DEMO_PASSWORD});self.assertEqual(r.status_code,200)
  self.assertEqual(other.get('/api/personal/dashboard?language=en').json()['bookmarks'],[])
 def test_origin_and_rate_limit(self):
  body={'username':'demo','password':a.DEMO_PASSWORD}
  self.assertEqual(self.client.post('/api/auth/login',json=body,headers={'Origin':'https://foreign.test'}).status_code,403)
  for i in range(20):self.assertEqual(self.client.post('/api/auth/login',json={'username':'missing','password':'invalidpass'}).status_code,401)
  self.assertEqual(self.client.post('/api/auth/login',json=body).status_code,429)
if __name__=='__main__':unittest.main()
