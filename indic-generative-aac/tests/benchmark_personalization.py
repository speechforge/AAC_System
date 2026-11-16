"""Controlled personalization checks, not a general language-model accuracy benchmark."""
import http.cookiejar
import json
from pathlib import Path
import statistics
import sys
import time
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'indic-generative-aac/backend'))
from personal_service import store, COOKIE, PREFIX

results=[];timings=[]
for language,target in [('gu','પાણી'),('gu','દવા'),('mr','पाणी'),('mr','औषध')]:
    jar=http.cookiejar.CookieJar()
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    csrf=None
    def request(path,body=None):
        headers={'Content-Type':'application/json'}
        if csrf:headers['X-CSRF-Token']=csrf
        req=urllib.request.Request('http://localhost:8000'+path,
                                  data=json.dumps(body).encode() if body is not None else None,headers=headers)
        with opener.open(req,timeout=10) as response:return json.load(response)
    session=request('/api/session/guest',{})
    csrf=session['csrf_token']
    token=next(c.value for c in jar if c.name==COOKIE)
    owner=store.read(token)
    try:
        before=request('/predict_next',{'language':language,'current_words':[]})['suggestions'][0]['word']
        for _ in range(3):
            request('/api/personal/activity',dict(event_id=str(uuid.uuid4()),kind='word',text=target,language=language))
        after=request('/predict_next',{'language':language,'current_words':[]})['suggestions'][0]['word']
        assert after==target
        for _ in range(20):
            start=time.perf_counter();request('/api/personal/dashboard?language='+language)
            timings.append((time.perf_counter()-start)*1000)
        results.append(dict(language=language,target=target,before_top1=before,after_top1=after,
                            before_correct=before==target,after_correct=after==target))
    finally:
        keys=list(store.redis.scan_iter(PREFIX+'account:'+owner['owner']+':*'))
        keys.append(store.session_key(token));store.redis.delete(*keys)
report=dict(scope='Four controlled adaptation cases: repeating a word should rank it first for that account/language; not a held-out natural-language accuracy result.',
            cases=results,before_passed=sum(x['before_correct'] for x in results),
            after_passed=sum(x['after_correct'] for x in results),total=len(results),
            dashboard_http_latency_ms=dict(samples=len(timings),median=round(statistics.median(timings),2),
                p95=round(sorted(timings)[int(len(timings)*.95)-1],2)))
(ROOT/'.runtime/reports/personalization-after.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
