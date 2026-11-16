"use strict";
const FIREBASE_CONFIG = {
      apiKey: "AIzaSyC4UZOUCAiO18L_yZ4ZuwrefDQLBzBr7yA",
      authDomain: "indicaacsystemnaacl2026.firebaseapp.com",
      projectId: "indicaacsystemnaacl2026",
      storageBucket: "indicaacsystemnaacl2026.firebasestorage.app",
      messagingSenderId: "731997066981",
      appId: "1:731997066981:web:b1208f5c8bc971e099660c"
    };
let auth=null;
function loadScript(src){return new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=src;script.onload=resolve;script.onerror=()=>{script.remove();reject(Error('Google sign-in needs internet. Please retry or use your username and password.'));};document.head.append(script);});}
async function googleAuth(){if(auth)return auth;await loadScript('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js');await loadScript('https://www.gstatic.com/firebasejs/10.12.2/firebase-auth-compat.js');if(!firebase.apps.length)firebase.initializeApp(FIREBASE_CONFIG);return auth=firebase.auth();}
const form=document.getElementById('account-form'), status=document.getElementById('account-status');
function busy(value){document.querySelectorAll('button').forEach(b=>b.disabled=value);}
async function request(path,body){const response=await fetch(path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Please check the entered details.');return data;}
form.addEventListener('submit',async event=>{event.preventDefault();busy(true);status.textContent='Signing in…';try{const body=Object.fromEntries(new FormData(form));if(auth?.currentUser)await auth.signOut();await request('/api/auth/'+document.body.dataset.mode,body);window.location.replace('/');}catch(e){status.textContent=e.message;busy(false);}});
document.getElementById('google-login').addEventListener('click',async()=>{busy(true);status.textContent='Opening Google sign-in…';try{await googleAuth();const result=await auth.signInWithPopup(new firebase.auth.GoogleAuthProvider());await request('/api/session/google',{id_token:await result.user.getIdToken(true)});window.location.replace('/');}catch(e){status.textContent=e.message;busy(false);}});
fetch('/api/session',{credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(s=>{if(s&&['local','google'].includes(s.service))window.location.replace('/');}).catch(()=>{});

const passwordToggle=document.getElementById('toggle-password');
passwordToggle?.addEventListener('click',()=>{const input=document.getElementById('password');const shown=input.type==='password';input.type=shown?'text':'password';passwordToggle.textContent=shown?'Hide':'Show';passwordToggle.setAttribute('aria-pressed',String(shown));passwordToggle.setAttribute('aria-label',shown?'Hide password':'Show password');});
