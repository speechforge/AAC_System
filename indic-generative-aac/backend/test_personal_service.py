"""Account isolation/session controls against real Redis; no GPU or LLM required."""
import concurrent.futures
import json
import statistics
import time
import unittest
import uuid
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
import personal_service as service


class PersonalServiceTests(unittest.TestCase):
    def setUp(self):
        # Separate logical DB and random key prefix. Never flush a shared DB.
        self.old_prefix = service.PREFIX
        service.PREFIX = 'aac:test:' + uuid.uuid4().hex + ':'
        connection = service.redis_connection()
        options = dict(connection.connection_pool.connection_kwargs)
        options['db'] = 15
        self.db = service.SessionStore(service.redis.Redis(**options))
        self.db.redis.ping()
        self.app = FastAPI()
        service.install(self.app)
        self.app.dependency_overrides[service.get_store] = lambda: self.db
        self.client = TestClient(self.app)
        self.headers = self.guest(self.client)

    def tearDown(self):
        keys = list(self.db.redis.scan_iter(service.PREFIX + '*'))
        if keys:
            self.db.redis.delete(*keys)
        self.db.redis.close()
        service.PREFIX = self.old_prefix

    def guest(self, client):
        result = client.post('/api/session/guest')
        self.assertEqual(result.status_code, 200, result.text)
        return {'X-CSRF-Token': result.json()['csrf_token']}

    def event(self, client=None, headers=None, language='gu', text='પાણી', kind='word', event_id=None):
        return (client or self.client).post('/api/personal/activity', headers=headers or self.headers,
            json=dict(event_id=event_id or str(uuid.uuid4()), kind=kind, text=text, language=language))

    def test_guest_accounts_do_not_share_data(self):
        self.assertEqual(self.event().status_code, 200)
        self.event(kind='conversation', text='મને પાણી જોઈએ છે.')
        self.client.post('/api/personal/bookmarks',json={'text':'મને પાણી જોઈએ છે.','language':'gu'},headers=self.headers)
        other = TestClient(self.app)
        self.guest(other)
        dashboard=other.get('/api/personal/dashboard?language=gu').json()
        for section in ('recent_conversations','frequent_words','bookmarks'):
            self.assertEqual(dashboard[section],[])
        own = self.client.get('/api/personal/frequent-words?language=gu').json()['items']
        self.assertEqual(own[0]['word'], 'પાણી')

    def test_english_account_sections_and_language_isolation(self):
        self.assertEqual(self.event(language='en',text='Water').status_code,200)
        self.assertEqual(self.event(language='en',text='I want water.',kind='conversation').status_code,200)
        result=self.client.post('/api/personal/bookmarks',headers=self.headers,
                                json={'text':'I want water.','language':'en'})
        self.assertEqual(result.status_code,200)
        dashboard=self.client.get('/api/personal/dashboard?language=en').json()
        self.assertEqual(dashboard['frequent_words'][0]['word'],'Water')
        self.assertEqual(dashboard['recent_conversations'][0]['text'],'I want water.')
        self.assertEqual(dashboard['bookmarks'][0]['text'],'I want water.')
        for language in ('hi','gu','mr'):
            data=self.client.get('/api/personal/dashboard?language='+language).json()
            for section in ('frequent_words','recent_conversations','bookmarks'):
                self.assertEqual(data[section],[])
        self.assertEqual(self.event(language='en',text='पानी').status_code,422)

    def test_language_isolation(self):
        self.event()
        self.event(language='mr', text='औषध')
        gu = self.client.get('/api/personal/dashboard?language=gu').json()
        mr = self.client.get('/api/personal/dashboard?language=mr').json()
        self.assertEqual([i['word'] for i in gu['frequent_words']], ['પાણી'])
        self.assertEqual([i['word'] for i in mr['frequent_words']], ['औषध'])

    def test_csrf_and_origin_checks(self):
        payload = dict(kind='word', text='પાણી', language='gu')
        self.assertEqual(self.client.post('/api/personal/activity', json=payload).status_code, 403)
        headers = {**self.headers, 'Origin': 'https://unrelated.example'}
        self.assertEqual(self.client.post('/api/personal/activity', json=payload, headers=headers).status_code, 403)
        self.assertEqual(self.client.post('/api/session/guest', headers={'Origin':'https://unrelated.example'}).status_code, 403)

    def test_retry_does_not_double_count(self):
        self.event(event_id='same-event-123')
        response = self.event(event_id='same-event-123')
        self.assertFalse(response.json()['recorded'])
        items = self.client.get('/api/personal/frequent-words?language=gu').json()['items']
        self.assertEqual(items[0]['count'], 1)

    def test_concurrent_writes_do_not_lose_counts(self):
        session = self.db.read(self.client.cookies[service.COOKIE])
        def add(i):
            self.db.record(session, service.Activity(event_id=f'concurrent-{i}', kind='word', language='mr', text='पाणी'))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(add, range(40)))
        self.assertEqual(self.db.frequent(session, 'mr')[0]['count'], 40)

    def test_recent_conversations_bounded_and_ordered(self):
        session = self.db.read(self.client.cookies[service.COOKIE])
        for i in range(105):
            self.db.record(session, service.Activity(event_id=f'conversation-{i}',kind='conversation',text=f'મને પાણી જોઈએ છે. {i}',language='gu'))
        items = self.db.recent(session, 'gu')
        self.assertEqual(len(items), 50)
        self.assertTrue(items[0]['text'].endswith('104'))
        self.assertEqual(self.db.redis.llen(self.db.data_key(session,'gu','conversation')), 100)

    def test_bookmark_dedup_delete_and_restore_after_login(self):
        payload = dict(text='મને પાણી જોઈએ છે.',language='gu')
        first = self.client.post('/api/personal/bookmarks',json=payload,headers=self.headers).json()
        second = self.client.post('/api/personal/bookmarks',json=payload,headers=self.headers).json()
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(self.client.delete('/api/session',headers=self.headers).status_code,200)
        self.headers = self.guest(self.client)
        items = self.client.get('/api/personal/bookmarks?language=gu').json()['items']
        self.assertEqual(len(items),1)
        self.assertEqual(self.client.delete('/api/personal/bookmarks/'+first['id']+'?language=mr',headers=self.headers).status_code,404)
        self.assertEqual(self.client.delete('/api/personal/bookmarks/'+first['id']+'?language=gu',headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/api/personal/bookmarks?language=gu').json()['items'],[])

    def test_session_revoked_after_logout(self):
        old = self.client.cookies[service.COOKIE]
        self.client.delete('/api/session',headers=self.headers)
        response = self.client.get('/api/session',headers={'Cookie':service.COOKIE+'='+old})
        self.assertEqual(response.status_code,401)

    def test_refresh_preserves_guest_session_for_other_tabs(self):
        old = self.client.cookies[service.COOKIE]
        self.guest(self.client)
        self.assertEqual(self.client.cookies[service.COOKIE],old)
        self.assertEqual(self.event().status_code,200)

    def test_expired_session_is_rejected(self):
        key = self.db.session_key(self.client.cookies[service.COOKIE])
        value = json.loads(self.db.redis.get(key));value['expires_at']=time.time()-1
        self.db.redis.set(key,json.dumps(value))
        self.assertEqual(self.client.get('/api/personal/dashboard?language=gu').status_code,401)

    def test_cookie_controls(self):
        response = self.client.post('/api/session/guest')
        cookie = response.headers.get('set-cookie','')
        # Existing session reuse does not need to issue another cookie.
        fresh = TestClient(self.app).post('/api/session/guest')
        self.assertIn('HttpOnly',fresh.headers['set-cookie'])
        self.assertIn('SameSite=lax',fresh.headers['set-cookie'])
        self.assertNotIn(self.client.cookies[service.COOKIE],response.text)
        self.assertEqual(response.headers['cache-control'],'no-store')

    def test_google_accounts_are_verified_and_separate(self):
        self.event()
        for uid,expected_empty in [('alice',True),('bob',True),('alice',False)]:
            with patch.object(service,'verify_google_token',return_value={'sub':uid,'exp':time.time()+3600}):
                response = self.client.post('/api/session/google',json={'id_token':'verified-test-token-value'})
            self.assertEqual(response.status_code,200)
            headers={'X-CSRF-Token':response.json()['csrf_token']}
            items=self.client.get('/api/personal/frequent-words?language=gu').json()['items']
            self.assertEqual(not items,expected_empty)
            dashboard=self.client.get('/api/personal/dashboard?language=gu').json()
            for section in ('recent_conversations','bookmarks'):
                self.assertEqual(not dashboard[section],expected_empty)
            self.event(headers=headers)
            self.event(headers=headers,kind='conversation',text='મને પાણી જોઈએ છે.')
            self.client.post('/api/personal/bookmarks',json={'text':'મને પાણી જોઈએ છે.','language':'gu'},headers=headers)
        # Google mutations must not alter the guest profile.
        guest_headers=self.guest(self.client)
        items=self.client.get('/api/personal/frequent-words?language=gu').json()['items']
        self.assertEqual(items[0]['count'],1)

    def test_forged_google_identity_not_accepted(self):
        with patch('google.oauth2.id_token.verify_firebase_token',side_effect=ValueError('bad signature')):
            response=self.client.post('/api/session/google',json={'id_token':'forged-invalid-token-value'})
        self.assertEqual(response.status_code,401)

    def test_wrong_issuer_or_provider_rejected(self):
        for claims in [dict(iss='wrong',sub='alice',exp=time.time()+100,firebase={'sign_in_provider':'google.com'}),
                       dict(iss='https://securetoken.google.com/'+service.PROJECT_ID,sub='alice',exp=time.time()+100,firebase={'sign_in_provider':'password'})]:
            with patch('google.oauth2.id_token.verify_firebase_token',return_value=claims):
                self.assertEqual(self.client.post('/api/session/google',json={'id_token':'invalid-provider-test-token'}).status_code,401)

    def test_native_scripts_and_payload_validation(self):
        self.assertEqual(self.event(text='water').status_code,422)
        self.assertEqual(self.event(language='gu',text='पानी').status_code,422)
        self.assertEqual(self.event(language='mr',text='પાણી').status_code,422)
        self.assertEqual(self.event(language='kn').status_code,422)
        self.assertEqual(self.event(text='પા'*100).status_code,422)

    def test_storage_failure_is_explicit(self):
        with patch.object(self.db.redis,'get',side_effect=service.redis.ConnectionError('unavailable')):
            response=self.client.get('/api/personal/dashboard?language=gu')
        self.assertEqual(response.status_code,503)
        self.assertNotIn('unavailable',response.text.lower().replace('is unavailable',''))

    def test_new_connection_retains_all_data(self):
        self.event(); self.event(text='મને પાણી જોઈએ છે.',kind='conversation')
        self.client.post('/api/personal/bookmarks',json=dict(text='મને પાણી જોઈએ છે.',language='gu'),headers=self.headers)
        session=self.db.read(self.client.cookies[service.COOKIE])
        other=service.SessionStore(service.redis.Redis(**self.db.redis.connection_pool.connection_kwargs))
        data=other.dashboard(session,'gu');other.redis.close()
        self.assertEqual(len(data['recent_conversations']),1)
        self.assertEqual(len(data['frequent_words']),1)
        self.assertEqual(len(data['bookmarks']),1)

    def test_personalized_rankings_for_gujarati_and_marathi(self):
        session=self.db.read(self.client.cookies[service.COOKIE])
        for lang,text in [('gu','પાણી'),('mr','औषध')]:
            self.db.record(session,service.Activity(kind='word',language=lang,text=text))
            self.assertEqual(self.db.frequent(session,lang)[0]['word'],text)

if __name__=='__main__': unittest.main()
