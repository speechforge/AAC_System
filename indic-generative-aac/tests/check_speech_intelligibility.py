"""Optional local ASR sanity check. This is not a human speech-quality/MOS test.
Run from this checkout with --download-asr once; all downloaded assets stay inside it.
"""
from pathlib import Path
import argparse
import base64
import json
import os
import re
import unicodedata
import urllib.request
ROOT=Path(__file__).resolve().parents[2]
os.environ.setdefault('HF_HOME',str(ROOT/'.runtime/hf-home'))
CASES=[('en','Hello. I need some water. Please help me.'),
       ('hi','नमस्ते। मुझे पानी चाहिए। कृपया मेरी मदद करें।'),
       ('gu','નમસ્તે. મને પાણી જોઈએ છે. કૃપા કરીને મારી મદદ કરો.'),
       ('mr','नमस्कार. मला पाणी पाहिजे. कृपया मला मदत करा.')]


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFC',text).casefold() if unicodedata.category(c)[0] in 'LMN')


def cer(reference,hypothesis):
    a,b=normalized(reference),normalized(hypothesis)
    previous=list(range(len(b)+1))
    for i,left in enumerate(a,1):
        current=[i]
        for j,right in enumerate(b,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(left!=right)))
        previous=current
    return previous[-1]/max(1,len(a))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download-asr',action='store_true')
    parser.add_argument('--prefix',default='quality')
    args=parser.parse_args()
    import numpy as np
    import soundfile as sf
    import torch
    from scipy.signal import resample_poly
    from math import gcd
    from transformers import WhisperProcessor,WhisperForConditionalGeneration
    directory=ROOT/'.runtime/asr/whisper-turbo'
    if args.download_asr:
        from huggingface_hub import snapshot_download
        snapshot_download('openai/whisper-large-v3-turbo',local_dir=directory,
            allow_patterns=['*.json','*.txt','model.safetensors'])
    if not (directory/'model.safetensors').exists():
        raise SystemExit('Run with --download-asr to install the optional local ASR judge.')
    output=ROOT/'.runtime/reports/speech-quality';output.mkdir(parents=True,exist_ok=True)
    # Capture first, then load ASR to avoid competing synthesis/ASR GPU activations.
    captures=[]
    for language,text in CASES:
        request=urllib.request.Request('http://localhost:8000/api/tts',
            data=json.dumps({'text':text,'language':language}).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=180) as response:result=json.load(response)
        expected='f5tts' if language=='en' else 'indicf5'
        if result.get('audio_kind')!=expected:raise RuntimeError('Unexpected speech engine')
        path=output/(args.prefix+'-'+language+'.wav');path.write_bytes(base64.b64decode(result['audio_b64']))
        captures.append((language,text,path,expected))
    device='cuda' if torch.cuda.is_available() else 'cpu'
    processor=WhisperProcessor.from_pretrained(directory,local_files_only=True)
    model=WhisperForConditionalGeneration.from_pretrained(directory,local_files_only=True,
        torch_dtype=torch.float32,attn_implementation='sdpa').to(device).eval()
    results=[]
    for language,text,path,engine in captures:
        samples,rate=sf.read(path,dtype='float32')
        divisor=gcd(rate,16000)
        samples=resample_poly(samples,16000//divisor,rate//divisor)
        inputs=processor(samples,sampling_rate=16000,return_tensors='pt',return_attention_mask=True)
        with torch.inference_mode():
            tokens=model.generate(**{k:v.to(device) for k,v in inputs.items()},language=language,
                                  task='transcribe',do_sample=False,max_new_tokens=256)
        hypothesis=processor.batch_decode(tokens,skip_special_tokens=True)[0].strip()
        result=dict(language=language,engine=engine,reference=text,transcript=hypothesis,
                    character_error_rate=round(cer(text,hypothesis),4))
        print(json.dumps(result,ensure_ascii=False),flush=True);results.append(result)
    (output/(args.prefix+'-asr.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print('ASR is an imperfect diagnostic. Human listening is required to assess distortion and naturalness.')


if __name__=='__main__':main()
