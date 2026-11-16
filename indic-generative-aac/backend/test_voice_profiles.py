import unittest,uuid,tempfile,io,json
from pathlib import Path
from unittest.mock import patch
import numpy as np,soundfile as sf
from fastapi import FastAPI
from fastapi.testclient import TestClient
import personal_service as p
import voice_profiles as v
import audio_cache as cache
class VoiceProfilesTest(unittest.TestCase):
 def setUp(self):
  self.old=p.PREFIX;p.PREFIX='aac:voice-test:'+uuid.uuid4().hex+':'
  options=dict(p.redis_connection().connection_pool.connection_kwargs);options['db']=15
  self.db=p.SessionStore(p.redis.Redis(**options));self.tmp=tempfile.TemporaryDirectory()
  self.patches=[patch.object(v,'ROOT',Path(self.tmp.name)/'voices'),patch.object(p,'store',self.db),patch.object(cache,'ROOT',Path(self.tmp.name)/'audio'),patch.object(cache,'CACHE',Path(self.tmp.name)/'cache')]
  for x in self.patches:x.start()
  app=FastAPI();p.install(app);app.include_router(v.router);app.dependency_overrides[p.get_store]=lambda:self.db
  self.a=TestClient(app);self.b=TestClient(app);self.sa=self.a.post('/api/session/guest').json();self.sb=self.b.post('/api/session/guest').json()
  self.headers={'X-CSRF-Token':self.sa['csrf_token']};buf=io.BytesIO();sf.write(buf,.1*np.sin(np.arange(96000)*.07),24000,format='WAV');self.wav=buf.getvalue()
 def tearDown(self):
  keys=list(self.db.redis.scan_iter(p.PREFIX+'*'))
  if keys:self.db.redis.delete(*keys)
  for x in reversed(self.patches):x.stop()
  self.tmp.cleanup();self.db.redis.close();p.PREFIX=self.old
 def test_upload_account_isolation_switch_delete_and_cache(self):
  r=self.a.post('/api/personal/voice/en',headers=self.headers,files={'audio':('voice.wav',self.wav)},data={'transcript':'Hello world.'});self.assertEqual(r.status_code,200,r.text)
  record=r.json()['voice'];self.assertTrue(record['active']);self.assertNotIn('path',record)
  self.assertIsNone(self.b.get('/api/personal/voice/en').json()['voice'])
  session=self.db.read(self.a.cookies[p.COOKIE]);ref=v.resolve(session,'en');self.assertTrue(ref['audio'].read(4)==b'RIFF')
  config={'_voice_owner':ref['owner'],'_voice_id':ref['voice_id']}
  base=cache.ROOT/'demo_library';base.mkdir(parents=True);(base/'sentences.json').write_text(json.dumps([{'language':'en','text':'Hello world.','id':'en-01'}]));(base/'en-01.wav').write_bytes(self.wav)
  self.assertIsNotNone(cache.load('Hello world.','en',{}));self.assertIsNone(cache.load('Hello world.','en',config))
  wave=np.array([100,-100,200],dtype=np.int16);cache.save('Hello world.','en',config,wave,24000)
  self.assertIsNotNone(cache.load('Hello world.','en',config))
  self.a.patch('/api/personal/voice/en',headers=self.headers,json={'active':False});self.assertIsNone(v.resolve(session,'en'))
  self.a.delete('/api/personal/voice/en',headers=self.headers);self.assertIsNone(self.a.get('/api/personal/voice/en').json()['voice']);self.assertEqual(len(list(cache.CACHE.glob('*.wav'))),0)
 def test_validation_and_csrf(self):
  self.assertEqual(self.a.post('/api/personal/voice/en',files={'audio':('x.wav',self.wav)},data={'transcript':'hello'}).status_code,403)
  for data in [b'not audio',b'RIFF']:
   self.assertEqual(self.a.post('/api/personal/voice/en',headers=self.headers,files={'audio':('x.wav',data)},data={'transcript':'hello'}).status_code,422)
  self.assertEqual(self.a.post('/api/personal/voice/gu',headers=self.headers,files={'audio':('x.wav',self.wav)},data={'transcript':'English text'}).status_code,422)
if __name__=='__main__':unittest.main()
