"""Persistent PCM cache; bundled demo recordings survive clearing generated cache."""
from pathlib import Path
import hashlib,json,os,tempfile,unicodedata
import numpy as np
import soundfile as sf
ROOT=Path(__file__).resolve().parents[2]/'audio_datastore'
CACHE=ROOT/'cache'
def norm(text):return ' '.join(unicodedata.normalize('NFC',text).split())
def key(text,lang,config):
    prefix=(config['_voice_owner']+'.'+config['_voice_id']+'.') if config.get('_voice_owner') else ''
    return prefix+hashlib.sha256(json.dumps(['speech-quality-v3',lang,norm(text),config],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def load(text,lang,config):
    path=CACHE/(key(text,lang,config)+'.wav')
    if not path.exists() and not config.get('_voice_owner'):
        manifest=ROOT/'demo_library/sentences.json'
        if manifest.exists():
            match=next((x for x in json.loads(manifest.read_text()) if x['language']==lang and norm(x['text'])==norm(text)),None)
            if match:path=ROOT/'demo_library'/(match['id']+'.wav')
    if path.exists():
        try:
            audio,rate=sf.read(path,dtype='int16')
            if rate==24000 and audio.size and audio.ndim==1:return audio,rate
        except (OSError,RuntimeError):pass
    return None

def save(text,lang,config,audio,rate):
    CACHE.mkdir(parents=True,exist_ok=True)
    target=CACHE/(key(text,lang,config)+'.wav')
    fd,tmp=tempfile.mkstemp(suffix='.wav',dir=CACHE);os.close(fd)
    try:
        sf.write(tmp,audio,rate,subtype='PCM_16');os.replace(tmp,target)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    files=sorted(CACHE.glob('*.wav'),key=lambda p:p.stat().st_mtime)
    for path in files[:-500]:path.unlink(missing_ok=True)

def stats():
    files=list(CACHE.glob('*.wav')) if CACHE.exists() else []
    return {'generated_files':len(files),'generated_bytes':sum(x.stat().st_size for x in files),'bundled_files':len(list((ROOT/'demo_library').glob('*.wav')))}
def clear():
    files=list(CACHE.glob('*.wav')) if CACHE.exists() else []
    for path in files:path.unlink(missing_ok=True)
    return {'removed':len(files),'bundled_audio_preserved':True}
