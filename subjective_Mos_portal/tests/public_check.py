"""Read JSON credentials from stdin; verify the live portal without creating participant data."""
import http.cookiejar,json,sys,urllib.request,urllib.error
config=json.load(sys.stdin)
base=config['public_url']
client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def call(path,body=None,headers=None):
 request=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':base,'User-Agent':'Mozilla/5.0 AAC-MOS-Study-Check',**(headers or {})})
 with client.open(request,timeout=30) as response:return response.status,response.read().decode(),dict(response.headers)
status,body,headers=call('/api/health');health=json.loads(body);assert status==200 and health['stimuli']==20
status,body,headers=call('/');assert 'registration-form' in body and 'AAC Speech Lab' in body
try:call('/api/admin/export/participants');raise AssertionError('Unauthenticated export was allowed')
except urllib.error.HTTPError as error:assert error.code==401
status,body,headers=call('/api/admin/login',{'username':config['username'],'password':config['password']});auth=json.loads(body)
assert 'Secure' in headers.get('set-cookie',headers.get('Set-Cookie',''))
status,body,headers=call('/api/admin/dashboard');dashboard=json.loads(body)
assert len(dashboard['files'])==20 and len(dashboard['languages'])==4
status,body,headers=call('/api/admin/export/participants')
assert body.lstrip('\ufeff').splitlines()[0]=='participant_id,name,email,age,gender,mother_tongue,organization,registered_iso,is_excluded,trials_completed'
status,body,headers=call('/__portal/origin',{'origin':config['origin']},{'Authorization':'Bearer '+config['origin_key']});assert status==200
call('/api/admin/logout',{},{'X-CSRF-Token':auth['csrf']})
print(json.dumps({'public_url':base,'health':health,'https_verified':True,'public_form':True,'admin_login':True,'secure_cookie':True,'unauthenticated_export_blocked':True,'participant_csv_schema':True,'registered_listeners':dashboard['counts']['registered'],'ratings':dashboard['counts']['ratings_all'],'origin_update':True,'created_test_participants':False}))
