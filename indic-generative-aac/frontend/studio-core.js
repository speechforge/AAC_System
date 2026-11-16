"use strict";
// Shared behaviour for EVERY page: ambient backdrop, comfort profiles, smooth page
// transitions, staggered reveal and accidental-tap protection. Rules: /DESIGN_RULES.md
(()=>{
 const root=document.documentElement, KEY='aac_comfort_v1';
 const PROFILES=['standard','calm','focus','large'];
 let saved={};try{saved=JSON.parse(localStorage.getItem(KEY)||'{}')||{}}catch(_){}
 let state={profile:PROFILES.includes(saved.profile)?saved.profile:'standard',readable:saved.readable===true,guard:saved.guard===true};
 const get=()=>({...state});
 function apply(){
  root.dataset.comfort=state.profile;root.dataset.readable=state.readable?'on':'off';root.dataset.tapGuard=state.guard?'on':'off';
  // Calm profile is a low-stimulation mode, so visual animation is forced off while it is active.
  if(state.profile==='calm')root.dataset.motion='off';
  window.dispatchEvent(new CustomEvent('aac-comfort-change',{detail:get()}));
 }
 window.AACComfort={get,profiles:PROFILES,set(next){
  if(PROFILES.includes(next.profile))state.profile=next.profile;
  if(typeof next.readable==='boolean')state.readable=next.readable;
  if(typeof next.guard==='boolean')state.guard=next.guard;
  try{localStorage.setItem(KEY,JSON.stringify(state))}catch(_){}
  if(window.AACMotion)window.AACMotion.set({});  // re-run motion so calm/standard resolve correctly
  apply();
 }};
 window.addEventListener('aac-motion-change',()=>{if(state.profile==='calm')root.dataset.motion='off'});
 window.addEventListener('storage',e=>{if(e.key!==KEY)return;try{const v=JSON.parse(e.newValue||'{}');state={profile:PROFILES.includes(v.profile)?v.profile:'standard',readable:v.readable===true,guard:v.guard===true};apply()}catch(_){}});
 apply();

 // ── Shared light/dark theme: one choice used by landing, sign-in, sign-up and the AAC studio. ──
 const TKEY='aac_theme_v1';
 function readTheme(){
  try{const t=localStorage.getItem(TKEY);if(t==='dark'||t==='light')return t}catch(_){}
  try{const c=JSON.parse(localStorage.getItem('aac_studio_cache_v1')||'{}');if(c&&c.darkMode===true)return 'dark'}catch(_){}
  return 'light';
 }
 let theme=readTheme();
 function applyTheme(){
  root.classList.toggle('dark',theme==='dark');root.dataset.theme=theme;
  const m=document.querySelector('meta[name=theme-color]');if(m)m.setAttribute('content',theme==='dark'?'#16131f':'#6044be');
  window.dispatchEvent(new CustomEvent('aac-theme-change',{detail:{theme}}));
 }
 window.AACTheme={get:()=>theme,set(next){if(next!=='dark'&&next!=='light'||next===theme)return;theme=next;try{localStorage.setItem(TKEY,theme)}catch(_){}applyTheme()}};
 window.addEventListener('storage',e=>{if(e.key===TKEY&&(e.newValue==='dark'||e.newValue==='light')){theme=e.newValue;applyTheme()}});
 applyTheme();

 function ready(fn){document.readyState==='loading'?document.addEventListener('DOMContentLoaded',fn):fn()}
 ready(()=>{

  // 0. Light/Dark picker with preview thumbnails on every non-app page (landing, sign-in, sign-up...).
  if(!document.getElementById('root')){
   const box=document.createElement('div');box.className='theme-picker';box.setAttribute('role','group');box.setAttribute('aria-label','Colour theme');
   const ICON={light:'<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M5.3 5.3 7 7M17 17l1.7 1.7M5.3 18.7 7 17M17 7l1.7-1.7"/></svg>',dark:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z"/></svg>'};
   box.innerHTML='<button type="button" class="theme-toggle" aria-pressed="false"></button>';
   const btn=box.querySelector('button');
   const host=document.querySelector('.site-header nav')||document.querySelector('.auth-intro');
   if(host)host.appendChild(box);else{box.classList.add('is-floating');document.body.appendChild(box)}
   const sync=()=>{const dark=theme==='dark';btn.innerHTML=dark?ICON.dark:ICON.light;btn.dataset.mode=theme;btn.setAttribute('aria-pressed',String(dark));const label=dark?'Switch to light mode':'Switch to dark mode';btn.setAttribute('aria-label',label);btn.title=label};
   btn.addEventListener('click',()=>window.AACTheme.set(theme==='dark'?'light':'dark'));
   window.addEventListener('aac-theme-change',sync);sync();
  }
  // 1. One ambient backdrop everywhere (landing/login already ship their own).
  if(!document.querySelector('.live-background')){
   const bg=document.createElement('div');bg.className='live-background';bg.setAttribute('aria-hidden','true');
   bg.innerHTML='<span class="live-orb live-orb-purple"></span><span class="live-orb live-orb-peach"></span><span class="live-orb live-orb-sage"></span><span class="live-ring live-ring-one"></span><span class="live-ring live-ring-two"></span><span class="live-spark live-spark-one"></span><span class="live-spark live-spark-two"></span>';
   document.body.prepend(bg);
  }
  // 2. Staggered reveal for cards/features that opt in or are auto-detected.
  const targets=[...document.querySelectorAll('.feature,.studio-page .card,.reveal-auto')];
  targets.forEach((el,i)=>{el.classList.add('reveal');el.style.setProperty('--reveal-i',String(i%6))});
  if('IntersectionObserver' in window){
   const io=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.classList.add('is-in');io.unobserve(e.target)}}),{threshold:.05});
   targets.forEach(el=>io.observe(el));
  }else targets.forEach(el=>el.classList.add('is-in'));
 });

 // 3. Smooth page-to-page transitions for same-origin navigation.
 document.addEventListener('click',e=>{
  const a=e.target.closest&&e.target.closest('a[href]');
  if(!a||e.defaultPrevented||e.button||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey||a.target||a.hasAttribute('download'))return;
  const url=new URL(a.href,location.href);
  if(url.origin!==location.origin||(url.pathname===location.pathname&&url.hash)||root.dataset.motion!=='on')return;
  e.preventDefault();root.classList.add('is-leaving');window.AACLoader&&window.AACLoader.show();
  setTimeout(()=>{location.href=url.href},170);
 });
 window.addEventListener('pageshow',e=>{if(e.persisted)root.classList.remove('is-leaving')});

 // 4. Accidental-tap protection: ignore a second activation of the same control within 450 ms.
 let lastEl=null,lastAt=0;
 document.addEventListener('click',e=>{
  if(state.guard!==true)return;
  const el=e.target.closest&&e.target.closest('button,[role=button]');
  if(!el||el.matches('input,textarea,select'))return;
  const now=performance.now();
  if(el===lastEl&&now-lastAt<450){e.stopImmediatePropagation();e.preventDefault();return}
  lastEl=el;lastAt=now;
 },true);
 // 5. Branded loading animation: translucent light veil + animated logo, on every page load and navigation.
 const LOGO='<svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="17" fill="#6044be"/><g transform="translate(5 3) scale(1.7)" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 7h14a4 4 0 0 1 4 4v8a4 4 0 0 1-4 4H13l-6 4V11a4 4 0 0 1 4-4Z"/><path class="ld-line ld-l1" d="M12 13h8"/><path class="ld-line ld-l2" d="M12 18h5"/></g></svg>';
 let loader=null,shownAt=0,hideTimer=0;
 function build(){
  if(loader)return loader;
  loader=document.createElement('div');loader.className='studio-loader';loader.setAttribute('role','status');loader.setAttribute('aria-live','polite');
  loader.innerHTML='<div class="ld-card"><div class="ld-logo"><span class="ld-ring"></span><span class="ld-ring ld-ring2"></span>'+LOGO+'</div><div class="ld-name">Indic AAC Studio</div><div class="ld-bars" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div><span class="ld-sr">Loading</span></div>';
  document.documentElement.appendChild(loader);return loader;
 }
 const loaderApi={
  show(){clearTimeout(hideTimer);const el=build();if(!el)return;shownAt=performance.now();el.classList.remove('is-out');el.classList.add('is-on')},
  hide(){const el=loader;if(!el)return;const wait=Math.max(0,550-(performance.now()-shownAt));clearTimeout(hideTimer);hideTimer=setTimeout(()=>{el.classList.add('is-out');el.classList.remove('is-on')},wait)}
 };
 window.AACLoader=loaderApi;
 // visible immediately on first paint (body may not exist yet when this script runs in <head>)
 if(document.body){loaderApi.show()}else{new MutationObserver((_,o)=>{if(document.body){o.disconnect();loaderApi.show()}}).observe(root,{childList:true})}
 const finish=()=>loaderApi.hide();
 document.readyState==='complete'?finish():window.addEventListener('load',finish);
 setTimeout(finish,6000); // never trap the user behind the veil
 window.addEventListener('pageshow',finish);
})();
