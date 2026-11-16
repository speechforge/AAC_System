"use strict";
const toggle=document.getElementById('motion-toggle');
function updateMotion(){const state=window.AACMotion.get();document.documentElement.classList.remove('motion-paused');toggle.setAttribute('aria-pressed',String(!state.enabled||state.reduced));toggle.textContent=state.reduced?'Reduced motion enabled':state.enabled?'Pause animation':'Resume animation';toggle.disabled=state.reduced;}
toggle.addEventListener('click',()=>window.AACMotion.set({enabled:!window.AACMotion.get().enabled}));window.addEventListener('aac-motion-change',updateMotion);updateMotion();
