"""Provision 20 current F5/IndicF5 stimuli through the existing AAC server; no model loading here."""
from pathlib import Path
import urllib.request,http.cookiejar,json,base64,hashlib,wave,io,time
ROOT=Path(__file__).resolve().parents[1]
TEXTS={
 'en':['I would like a glass of water, please.','I am hungry and I would like some food.','I do not want tea right now.','I feel happy when I am with my family.','Please help me explain what I need.'],
 'hi':['कृपया मुझे एक गिलास पानी दीजिए।','मुझे भूख लगी है और मुझे खाना चाहिए।','मुझे अभी चाय नहीं चाहिए।','अपने परिवार के साथ रहकर मुझे खुशी होती है।','कृपया अपनी बात समझाने में मेरी मदद कीजिए।'],
 'gu':['કૃપા કરીને મને એક ગ્લાસ પાણી આપો.','મને ભૂખ લાગી છે અને મને ખાવાનું જોઈએ છે.','મને અત્યારે ચા નથી જોઈતી.','મારા પરિવાર સાથે મને ખુશી થાય છે.','કૃપા કરીને મારી વાત સમજાવવામાં મને મદદ કરો.'],
 'mr':['कृपया मला एक ग्लास पाणी द्या.','मला भूक लागली आहे आणि मला जेवण पाहिजे.','मला आत्ता चहा नको आहे.','माझ्या कुटुंबासोबत मला आनंद होतो.','कृपया माझे म्हणणे समजावून सांगायला मला मदत करा.'],
}
def prepare():
 client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def post(path,body):
  request=urllib.request.Request('http://localhost:8000'+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  with client.open(request,timeout=180) as response:return json.load(response)
 post('/api/auth/login',{'username':'demo','password':'AACdemo@2026'})
 old=json.loads((ROOT/'config/stimuli.json').read_text()) if (ROOT/'config/stimuli.json').exists() else []
 entries=[]
 for lang,texts in TEXTS.items():
  for number,text in enumerate(texts,1):
   clip_id=f'{lang}-{number:02d}';path=ROOT/'audio'/(clip_id+'.wav')
   existing=next((x for x in old if x['id']==clip_id and x['text']==text),None)
   if existing and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==existing['sha256']:
    entries.append(existing);continue
   start=time.monotonic();result=post('/api/tts',{'text':text,'language':lang,'voice_id':lang})
   assert result.get('voice_source')=='default', 'Evaluation requires the default voice, not a personal upload'
   assert result['audio_kind']==('f5tts' if lang=='en' else 'indicf5'),result.get('audio_kind')
   raw=base64.b64decode(result['audio_b64']);path.write_bytes(raw)
   with wave.open(io.BytesIO(raw)) as wav:
    assert wav.getnchannels()==1 and wav.getframerate()==24000 and wav.getsampwidth()==2
    duration=wav.getnframes()/wav.getframerate()
   entry={'id':clip_id,'language':lang,'text':text,'file':clip_id+'.wav','duration_seconds':duration,'sample_rate':24000,'channels':1,'sha256':hashlib.sha256(raw).hexdigest(),'engine':result['audio_kind'],'voice_source':'default','source':'current AAC /api/tts','cache_hit':result.get('cache_hit',False),'generated_iso':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'generation_seconds':round(time.monotonic()-start,3),'review':'Authored text; native-reader and human audio review pending.'}
   entries.append(entry)
   (ROOT/'config/stimuli.json').write_text(json.dumps(entries+[x for x in old if x['id'] not in {e['id'] for e in entries}],ensure_ascii=False,indent=2)+'\n')
   print(clip_id,result['audio_kind'],round(duration,2),'s','cache_hit:',entry['cache_hit'],flush=True)
 (ROOT/'config/stimuli.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n')
 assert len(entries)==20
 print('Provisioned 20 real WAVs, five per language.',flush=True)
if __name__=='__main__':prepare()
