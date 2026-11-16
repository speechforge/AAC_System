/* Explicit online/offline mode; shared preferences, profile-scoped IndexedDB speech pairs. */
(()=>{'use strict';const KEY='aac_access_v1',OWNER='aac_offline_owner_v1';let database;
function settings(){try{return {mode:'online',history:true,vibration:false,saveSpeech:true,...JSON.parse(localStorage.getItem(KEY)||'{}')}}catch(_){return{mode:'online',history:true,vibration:false,saveSpeech:true}}}
function configure(patch){const next={...settings(),...patch};localStorage.setItem(KEY,JSON.stringify(next));window.dispatchEvent(new CustomEvent('aac-connection-change',{detail:next}));return next}
function open(){return database?Promise.resolve(database):new Promise((resolve,reject)=>{const r=indexedDB.open('indic_aac_offline_v1',1);r.onupgradeneeded=()=>{for(const store of['speech','sentences','history'])r.result.createObjectStore(store,{keyPath:'id'})};r.onsuccess=()=>resolve(database=r.result);r.onerror=()=>reject(r.error)})}
async function request(store,method,value){const db=await open();return new Promise((resolve,reject)=>{const tx=db.transaction(store,method==='get'||method==='getAll'?'readonly':'readwrite'),r=tx.objectStore(store)[method](value);r.onsuccess=()=>{if(method==='get'||method==='getAll')resolve(r.result)};r.onerror=()=>reject(r.error);tx.oncomplete=()=>resolve(r.result);tx.onerror=()=>reject(tx.error)})}
const textKey=(text,language)=>language+'|'+text.normalize('NFC').trim();const scope=owner=>owner||localStorage.getItem(OWNER)||'public';
function sentenceKey(payload){return JSON.stringify([payload.language,payload.act,!!payload.negation,payload.concept_ids,payload.entities])}
async function save(text,language,data,owner){if(!data.audio_b64)return;await request('speech','put',{id:scope(owner)+'|'+textKey(text,language),owner:scope(owner),text,language,audio_b64:data.audio_b64,audio_kind:data.audio_kind||'local_recording',sample_rate:data.sample_rate||24000,voice_id:data.voice_id||language,saved_at:Date.now()})}
async function get(text,language,owner){const own=await request('speech','get',scope(owner)+'|'+textKey(text,language));return own||await request('speech','get','public|'+textKey(text,language))}
async function rememberSentence(payload,data,owner){if(data.validated!==true)return;await request('sentences','put',{id:scope(owner)+'|'+sentenceKey(payload),data,saved_at:Date.now()})}
async function sentence(payload,owner){return(await request('sentences','get',scope(owner)+'|'+sentenceKey(payload)))?.data||null}
async function stats(owner){const all=await request('speech','getAll');const visible=all.filter(x=>['public',scope(owner)].includes(x.owner));return{pairs:visible.length,bytes:visible.reduce((sum,x)=>sum+Math.floor(x.audio_b64.length*.75),0)}}
async function install(owner,progress=()=>{}){
 if(owner)localStorage.setItem(OWNER,owner);
 await window.AACPlayback.provision();
 const bank=await fetch('/static/demo/sentences.json').then(r=>{if(!r.ok)throw Error('Recorded sentence pack missing');return r.json()}),quick=await fetch('/static/quick-pack.json').then(r=>r.json());
 const clips=[...bank.map(x=>({...x,audio:'/static/demo/'+x.audio})),...quick.phrases];let done=0;
 for(const item of clips){const r=await fetch(item.audio);if(!r.ok)throw Error('Missing recording: '+item.audio);const raw=new Uint8Array(await r.arrayBuffer());if(item.sha256){const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw))).map(x=>x.toString(16).padStart(2,'0')).join('');if(hash!==item.sha256)throw Error('Recording verification failed: '+item.audio)}let binary='';for(const byte of raw)binary+=String.fromCharCode(byte);await save(item.text,item.language,{audio_b64:btoa(binary),audio_kind:'local_recording'},'public');progress(++done,clips.length)}
 return stats(owner);
}
async function record(event,owner){if(!settings().history)return;const item={...event,id:crypto.randomUUID(),owner:scope(owner),created_at:Date.now()/1000};await request('history','put',item)}
async function history(owner,language){return(await request('history','getAll')).filter(x=>x.owner===scope(owner)&&x.language===language).sort((a,b)=>b.created_at-a.created_at).slice(0,50)}
window.AACOffline={settings,configure,save,get,rememberSentence,sentence,install,stats,scope,record,history,forgetOwner:()=>localStorage.removeItem(OWNER)};
})();
