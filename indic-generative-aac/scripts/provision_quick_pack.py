"""Provision authored public phrases. Reuse exact-text WAVs; synthesize missing clips only on explicit invocation.
Audio/text are machine checked, not native-reader reviewed. No personal utterances are included.
"""
from pathlib import Path
import json,hashlib,wave,urllib.request,http.cookiejar,base64,argparse
root=Path(__file__).resolve().parents[1];front=root/'frontend';bank=json.loads((front/'demo/sentences.json').read_text())
texts={
'en':['Please help me.','I want water.','I need to use the bathroom.','I am in pain.'],
'hi':['कृपया मेरी मदद कीजिए।','मुझे पानी चाहिए।','मुझे बाथरूम जाना है।','मुझे दर्द हो रहा है।'],
'gu':['કૃપા કરીને મને મદદ કરો.','મને પાણી જોઈએ છે.','મારે બાથરૂમ જવું છે.','મને દુખાવો થાય છે.'],
'mr':['कृपया मला मदत करा.','मला पाणी हवे आहे.','मला शौचालयात जायचे आहे.','मला वेदना होत आहेत.']}
args=argparse.ArgumentParser();args.add_argument('--synthesize-missing',action='store_true');opts=args.parse_args()
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def post(path,body):
 r=opener.open(urllib.request.Request('http://localhost:8000'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=240);return json.load(r)
if opts.synthesize_missing:post('/api/auth/login',{'username':'demo','password':'AACdemo@2026'})
out=[];dest=front/'audio/quick-v1';dest.mkdir(parents=True,exist_ok=True)
for lg,phrases in texts.items():
 for key,text in zip(['help','water','bathroom','pain'],phrases):
  item={'key':key,'language':lg,'text':text,'review':'machine-checked; native/audio-listener review pending'}
  hit=next((x for x in bank if x['language']==lg and x['text']==text),None);target=dest/(lg+'-'+key+'.wav')
  if hit:target.write_bytes((front/'demo'/hit['audio']).read_bytes())
  elif not target.exists() and opts.synthesize_missing:
   try:target.write_bytes(base64.b64decode(post('/api/tts',{'text':text,'language':lg})['audio_b64']))
   except Exception as e:print('MISSING',lg,key,str(e))
  if target.exists():
   with wave.open(str(target)) as w:
    assert w.getnframes()>0 and w.getframerate()>0;item.update(duration_seconds=w.getnframes()/w.getframerate(),sample_rate=w.getframerate())
   item.update(audio='/static/audio/quick-v1/'+target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest())
  out.append(item)
(front/'quick-pack.json').write_text(json.dumps({'version':1,'phrases':out},ensure_ascii=False,indent=2))
print('Quick pack:',sum('audio'in x for x in out),'/',len(out),'clips')
