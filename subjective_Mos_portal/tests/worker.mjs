import assert from 'node:assert/strict';
import {webcrypto,timingSafeEqual} from 'node:crypto';
import worker from '../cloudflare/worker.mjs';
globalThis.crypto=webcrypto;
// Node fixture for Cloudflare's documented Web Crypto extension.
crypto.subtle.timingSafeEqual=(a,b)=>timingSafeEqual(Buffer.from(a),Buffer.from(b));
const values=new Map();const env={ORIGIN_KEY:'test-key-only',INITIAL_ORIGIN:'https://fixture.trycloudflare.com',ROUTING:{get:async k=>values.get(k),put:async(k,v)=>values.set(k,v)}};
const nativeFetch=globalThis.fetch;let captured;
try{
 assert.equal((await worker.fetch(new Request('https://portal.example/__portal/origin',{method:'POST',body:JSON.stringify({origin:'https://new.trycloudflare.com'})}),env)).status,401);
 assert.equal((await worker.fetch(new Request('https://portal.example/__portal/origin',{method:'POST',headers:{Authorization:'Bearer test-key-only'},body:JSON.stringify({origin:'http://127.0.0.1'})}),env)).status,400);
 assert.equal((await worker.fetch(new Request('https://portal.example/__portal/origin',{method:'POST',headers:{Authorization:'Bearer test-key-only'},body:JSON.stringify({origin:'https://new.trycloudflare.com'})}),env)).status,200);
 globalThis.fetch=async(request,options)=>{captured={request,options};return new Response('audio-body',{status:206,headers:{'Set-Cookie':'mos_listener=opaque; Secure; HttpOnly; SameSite=Lax; Path=/','Content-Range':'bytes 0-9/30'}})};
 const response=await worker.fetch(new Request('https://portal.example/api/audio/en-01',{headers:{Cookie:'mos_listener=opaque',Range:'bytes=0-9','CF-Connecting-IP':'192.0.2.1'}}),env);
 assert.equal(response.status,206);assert.equal(captured.request.url,'https://new.trycloudflare.com/api/audio/en-01');assert.equal(captured.request.headers.get('range'),'bytes=0-9');assert.equal(captured.request.headers.get('cookie'),'mos_listener=opaque');assert.equal(captured.request.headers.get('x-mos-origin-key'),'test-key-only');assert.equal(captured.options.redirect,'manual');assert(response.headers.get('set-cookie').includes('Secure'));assert.equal(await response.text(),'audio-body');
 await worker.fetch(new Request('https://portal.example//untrusted.example/path'),env);assert.equal(new URL(captured.request.url).host,'new.trycloudflare.com');
 globalThis.fetch=async()=>{throw new Error('Fixture disconnected')};assert.equal((await worker.fetch(new Request('https://portal.example/api/me'),env)).status,503);
 console.log('PASS Worker origin authentication, SSRF restriction, streaming/range/cookie forwarding and unavailable-origin response.');
}finally{globalThis.fetch=nativeFetch}
