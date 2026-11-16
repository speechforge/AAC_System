"""Private account/language reference voices; metadata in Redis, WAVs outside static files."""
from pathlib import Path
import io,json,hashlib,uuid,math,threading
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Form
from pydantic import BaseModel
import personal_service as p
import audio_cache
ROOT=p.ROOT/'.runtime/voice_profiles'
LOCK=threading.RLock()
router=APIRouter(prefix='/api/personal/voice',tags=['Personal voice'])
def owner(session):return p.digest(session['owner'])
def dbkey(session,lang):return p.PREFIX+'voice:'+owner(session)+':'+lang

def info(session,lang,db):
 raw=db.redis.get(dbkey(session,lang))
 return json.loads(raw) if raw else None

def public(record):
 return {k:v for k,v in record.items() if k in ['id','language','label','transcript','duration','active']} if record else None

def remove_files(session,record):
 if record:
  (ROOT/owner(session)/(record['id']+'.wav')).unlink(missing_ok=True)
  for f in audio_cache.CACHE.glob(owner(session)+'.'+record['id']+'.*.wav'):f.unlink(missing_ok=True)

def resolve(session,lang):
 with LOCK:
  record=info(session,lang,p.store)
  if not record or not record['active']:return None
  path=ROOT/owner(session)/(record['id']+'.wav')
  if not path.exists():raise HTTPException(503,'Your voice recording is missing. Upload it again or select the default voice.')
  return dict(audio=io.BytesIO(path.read_bytes()),text=record['transcript'],duration=record['duration'],
              fingerprint=record['fingerprint'],voice_id=record['id'],owner=owner(session))

@router.get('/{language}')
def get_profile(language:p.LANGUAGES,session=Depends(p.require_session),db=Depends(p.get_store)):
 with LOCK:return {'voice':public(info(session,language,db))}

@router.post('/{language}')
async def upload(language:p.LANGUAGES,audio:UploadFile=File(...),transcript:str=Form(...),label:str=Form('My voice'),session=Depends(p.require_write),db=Depends(p.get_store)):
 text=transcript.strip()
 if not text or len(text)>2000:raise HTTPException(422,'Enter the exact transcript (up to 2000 characters).')
 text=p.validate_native(text,language)
 raw=await audio.read(20*1024*1024+1)
 if len(raw)>20*1024*1024:raise HTTPException(413,'The WAV file must be smaller than 20 MB.')
 try:
  file=sf.SoundFile(io.BytesIO(raw))
  with file:
   duration=len(file)/file.samplerate
   if file.format not in ('WAV','WAVEX','RF64') or not 8000<=file.samplerate<=96000 or file.channels not in (1,2) or not 3<=duration<=12:
    raise ValueError('Use a 3–12 second mono or stereo WAV, at 8–96 kHz.')
   rate=file.samplerate;wave=file.read(dtype='float32',always_2d=True).mean(axis=1)
  if not np.isfinite(wave).all() or np.sqrt(np.mean(wave**2))<.003:raise ValueError('The recording is silent or too quiet. Upload clear speech.')
 except (RuntimeError,ValueError,OSError) as exc:raise HTTPException(422,str(exc))
 divisor=math.gcd(rate,24000);wave=resample_poly(wave,24000//divisor,rate//divisor)
 peak=float(np.max(np.abs(wave)))
 if peak>0.95:wave*=0.95/peak
 if text[-1] not in '.!?।':text+='.'
 record=dict(id=uuid.uuid4().hex,language=language,label=label.strip()[:80] or 'My voice',transcript=text,duration=len(wave)/24000,active=True)
 encoded=io.BytesIO();sf.write(encoded,wave,24000,format='WAV',subtype='PCM_16');data=encoded.getvalue()
 record['fingerprint']=hashlib.sha256(data+text.encode()).hexdigest()
 with LOCK:
  old=info(session,language,db);folder=ROOT/owner(session);folder.mkdir(parents=True,exist_ok=True,mode=0o700)
  path=folder/(record['id']+'.wav');path.write_bytes(data);path.chmod(0o600)
  try:db.redis.set(dbkey(session,language),json.dumps(record))
  except Exception:path.unlink(missing_ok=True);raise
  remove_files(session,old)
 return {'voice':public(record)}

class Selection(BaseModel):active:bool
@router.patch('/{language}')
def select(language:p.LANGUAGES,body:Selection,session=Depends(p.require_write),db=Depends(p.get_store)):
 with LOCK:
  record=info(session,language,db)
  if not record:raise HTTPException(404,'Upload a voice recording first.')
  record['active']=body.active;db.redis.set(dbkey(session,language),json.dumps(record));return {'voice':public(record)}

@router.delete('/{language}')
def delete(language:p.LANGUAGES,session=Depends(p.require_write),db=Depends(p.get_store)):
 with LOCK:
  record=info(session,language,db);db.redis.delete(dbkey(session,language));remove_files(session,record)
 return {'voice':None}
