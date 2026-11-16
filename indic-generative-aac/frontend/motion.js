"use strict";
// Visual animation preferences are independent of speech playback speed.
(()=>{
 const speeds=[.25,.5,.75,1,1.25,1.5,1.75,2], key='aac_motion_v1';
 let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')||{}}catch(_){}
 let enabled=saved.enabled!==false, speed=speeds.includes(saved.speed)?saved.speed:1;
 const media=matchMedia('(prefers-reduced-motion: reduce)');
 const get=()=>({enabled,speed,reduced:media.matches});
 function apply(){
  const root=document.documentElement;
  root.dataset.motion=enabled&&!media.matches?'on':'off';root.dataset.motionSpeed=String(speed);
  for(const [name,ms] of Object.entries({spin:1000,sound:900,fast:160,enter:280,drawer:320,float:7000,wave:2000,draw:1200,hero:800,board:1000}))root.style.setProperty('--motion-'+name,ms/speed+'ms');
  window.dispatchEvent(new CustomEvent('aac-motion-change',{detail:get()}));
 }
 window.AACMotion={get,speeds,set(value){if(typeof value.enabled==='boolean')enabled=value.enabled;if(speeds.includes(value.speed))speed=value.speed;try{localStorage.setItem(key,JSON.stringify({enabled,speed}))}catch(_){}apply()}};
 media.addEventListener('change',apply);
 window.addEventListener('storage',event=>{if(event.key!==key)return;try{const v=JSON.parse(event.newValue||'{}');enabled=v.enabled!==false;speed=speeds.includes(v.speed)?v.speed:1;apply()}catch(_){}});
 apply();
})();
