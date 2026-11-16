from pathlib import Path
import urllib.request,http.cookiejar,json,time
client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def post(path,data):
 r=client.open(urllib.request.Request('http://localhost:8000'+path,json.dumps(data).encode(),headers={'Content-Type':'application/json'}),timeout=60);return json.load(r)
post('/api/auth/login',{'username':'demo','password':'AACdemo@2026'});board=json.loads(Path('indic-generative-aac/backend/board_concepts.json').read_text())['concepts'];results=[]
for lg in ['en','hi','gu','mr']:
 start=time.perf_counter();data=post('/generate',{'entities':[board['NO'][lg],board['TEA'][lg]],'concept_ids':['NO','TEA'],'language':lg,'act':'REQUEST','act_source':'client','negation':True,'include_audio':False,'policy':'template_only'})
 assert data['outcome']=='sentence_template' and data['validated'] and not data['audio_b64'] and data['metrics']['t_tts']==0,(lg,data)
 results.append({'language':lg,'duration_ms':(time.perf_counter()-start)*1000,'response':data});print(lg,'text-only validated refusal:',data['text'])
Path('docs/aac-redesign/evidence/live-text-only.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
