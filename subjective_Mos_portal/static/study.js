'use strict';
const $ = id => document.getElementById(id);
const panels = ['welcome', 'return-card', 'study', 'complete'];
let instructionsUnderstood = false;
let state = null, returnCode = '', revision = 0, listened = 0, previousTime = 0, cycleStarted = false, busy = false, played = false;
const audio = $('trial-audio');
const languageNames = {en:'English',gu:'ગુજરાતી',hi:'हिन्दी',mr:'मराठी'};
const escapeHTML = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path, body) {
  let response;
  try { response = await fetch(path, {method:body === undefined ? 'GET':'POST', credentials:'same-origin', headers:body === undefined ? {}:{'Content-Type':'application/json'}, body:body === undefined ? undefined:JSON.stringify(body)}); }
  catch { throw new Error('Connection interrupted. Your saved ratings are safe. Reconnect and try again.'); }
  const data = await response.json();
  if (!response.ok) { const error = new Error(Array.isArray(data.detail) ? 'Please check the form fields and try again.' : data.detail || 'Please try again.'); error.status = response.status; throw error; }
  return data;
}
function show(panel) { for (const name of panels) $(name).hidden = name !== panel; $('global-status').textContent = ''; }
function tab(which) {
  const isNew = which === 'new'; $('registration-form').hidden = !isNew; $('resume-form').hidden = isNew;
  for (const [id, selected] of [['new-tab',isNew],['return-tab',!isNew]]) { $(id).setAttribute('aria-selected',String(selected)); $(id).tabIndex = selected ? 0 : -1; }
}
$('new-tab').onclick = () => tab('new'); $('return-tab').onclick = () => tab('return');
for (const id of ['new-tab','return-tab']) $(id).onkeydown = event => { if (['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) { event.preventDefault(); const next = event.key === 'Home' ? 'new' : event.key === 'End' ? 'return' : id === 'new-tab' ? 'return':'new'; tab(next); $(next+'-tab').focus(); } };
function formHandler(id, errorId, action) {
  $(id).onsubmit = async event => { event.preventDefault(); const button = event.currentTarget.querySelector('button[type=submit]'); button.disabled = true; $(errorId).textContent = '';
    try { await action(new FormData(event.currentTarget)); } catch(error) { $(errorId).textContent = error.message; } finally { button.disabled = false; }
  };
}
$('understand-instructions').onclick = () => { instructionsUnderstood = true; $('understand-instructions').setAttribute('aria-pressed','true'); $('understand-instructions').textContent = 'Understood ✓'; $('understanding-status').textContent = 'Thank you. You can now choose your mother tongue.'; const field = document.querySelector('[name=mother_tongue]'); field.disabled = false; field.focus(); };
formHandler('registration-form','register-error', async form => {
  if (!instructionsUnderstood) throw new Error('Please read the listening instructions and press I understand.');
  const body = Object.fromEntries(form); body.age = Number(body.age); body.consent = form.has('consent'); body.instructions_understood = instructionsUnderstood;
  state = await api('/api/register',body); returnCode = state.return_code;
  $('saved-participant').textContent = state.participant.participant_id; $('saved-code').textContent = returnCode;
  show('return-card'); $('begin-trials').focus();
});
formHandler('resume-form','resume-error', async form => { state = await api('/api/resume',Object.fromEntries(form)); render(); });
$('download-return').onclick = () => {
  const text = `AAC Speech Lab — private return details\n\nParticipant ID: ${state.participant.participant_id}\nReturn code: ${returnCode}\nStudy portal: ${location.origin}\n\nKeep this code private. You can also continue from this browser.\n`;
  const link = document.createElement('a'); const url = URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'})); link.href = url; link.download = 'AAC-listening-return-details.txt'; link.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
};
$('begin-trials').onclick = () => { returnCode = ''; render(); };
function clock(seconds) { seconds = Number.isFinite(seconds) ? Math.max(0,Math.floor(seconds)):0; return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`; }
function updateClock() {
  const duration = audio.duration || state?.current?.duration || 0;
  $('play-time').textContent = `${clock(audio.currentTime)} / ${clock(duration)}`;
  $('audio-progress').max = duration || 1; $('audio-progress').value = audio.currentTime || 0;
}
function render() {
  revision++; audio.pause(); audio.removeAttribute('src'); audio.load(); busy = false; listened = 0; previousTime = 0; cycleStarted = false;
  if (state.completed) {
    show('complete'); $('complete-id').textContent = `Participant ID: ${state.participant.participant_id}`;
    $('complete-languages').innerHTML = Object.entries(languageNames).map(([lang,name])=>`<span lang="${lang}">${name} · 5/5</span>`).join(''); $('finish-session').focus(); return;
  }
  show('study'); const clip = state.current; played = !!clip.played;
  $('progress-label').textContent = `${state.participant.trials_completed} of 20 ratings saved`;
  $('study-progress').value = state.participant.trials_completed;
  $('sample-number').textContent = `RECORDING ${String(clip.position).padStart(2,'0')} / 20`;
  $('sample-language').textContent = clip.language_label;
  $('language-progress').innerHTML = Object.entries(languageNames).map(([lang,name])=>`<div><span lang="${lang}">${name}</span><strong>${state.language_progress[lang]}/5</strong></div>`).join('');
  $('trial-error').textContent = ''; $('rating-field').disabled = !played;
  document.querySelectorAll('input[name=score]').forEach(input=>{input.checked=false;});
  $('submit-rating').disabled = true; $('submit-rating').innerHTML = `${clip.position === 20 ? 'Save my final rating':'Save rating &amp; continue'} <span aria-hidden="true">→</span>`;
  setPlayLabel(false); $('listen-status').textContent = played ? 'Full listen saved. You can replay or choose your score.':'Listen to the full recording to unlock the rating.';
  $('listen-status').classList.toggle('ready',played);
  audio.src = clip.audio_url; audio.volume = Number($('volume').value); audio.playbackRate = 1;
  updateClock();
}
function setPlayLabel(playing) {
  $('play-audio').innerHTML = playing ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h4v14H7zm6 0h4v14h-4z" fill="currentColor"/></svg><span>Pause recording</span>' : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7Z" fill="currentColor"/></svg><span>Play recording</span>';
  $('play-audio').setAttribute('aria-label',playing ? 'Pause recording':'Play recording');
}
function addListened() { const delta = audio.currentTime - previousTime; if (delta > 0 && delta < 1.5) listened += delta; previousTime = audio.currentTime; updateClock(); }
$('play-audio').onclick = async () => {
  if (!state?.current || busy) return;
  if (!audio.paused) {audio.pause(); return;}
  const thisRevision = revision, clipId = state.current.id;
  $('play-audio').disabled = true; $('trial-error').textContent = '';
  try {
    if (!cycleStarted || audio.ended) {
      listened = 0; previousTime = 0; audio.currentTime = 0;
      await api('/api/playback',{clip_id:clipId,event:'started'});
      if (revision !== thisRevision) return;
      cycleStarted = true;
    }
    await audio.play();
  } catch(error) { $('trial-error').textContent = error.message || 'Unable to play this recording. Please try again.'; }
  finally { $('play-audio').disabled = false; }
};
audio.onplay = () => setPlayLabel(true);
audio.onpause = () => setPlayLabel(false);
audio.ontimeupdate = addListened; audio.onloadedmetadata = updateClock;
audio.onerror = () => { if (audio.getAttribute('src')) $('trial-error').textContent = 'The recording could not be loaded. Check your connection and reload this page; your saved responses will remain.'; };
audio.onended = async () => {
  addListened(); cycleStarted = false; setPlayLabel(false);
  const thisRevision = revision, clipId = state.current.id;
  try {
    await api('/api/playback',{clip_id:clipId,event:'ended',listened_seconds:listened});
    if (revision !== thisRevision) return;
    played = true; $('rating-field').disabled = false; $('listen-status').textContent = 'Full listen saved. Choose your score below.'; $('listen-status').classList.add('ready');
    $('submit-rating').disabled = !document.querySelector('input[name=score]:checked');
  } catch(error) { if (revision === thisRevision) $('trial-error').textContent = error.message; }
};
$('volume').oninput = () => {audio.volume = Number($('volume').value);};
for (const radio of document.querySelectorAll('input[name=score]')) radio.onchange = () => {$('submit-rating').disabled = !played || busy;};
$('submit-rating').onclick = async () => {
  const selection = document.querySelector('input[name=score]:checked'); if (!selection || !played || busy) return;
  busy = true; $('submit-rating').disabled = true; $('trial-error').textContent = ''; audio.pause();
  try { state = await api('/api/rate',{clip_id:state.current.id,score:Number(selection.value)}); render(); if (!state.completed) $('play-audio').focus(); }
  catch(error) { $('trial-error').textContent = error.message; busy = false; $('submit-rating').disabled = false; }
};
async function leave() {
  audio.pause(); $('global-status').textContent = '';
  try { await api('/api/leave',{}); state = null; revision++; show('welcome'); tab('return'); $('resume-form input').focus(); }
  catch(error) { $('global-status').textContent = error.message; }
}
$('save-leave').onclick = leave; $('finish-session').onclick = leave;
(async()=>{ try { state = await api('/api/me'); render(); } catch(error) { show('welcome'); if(error.status !== 401) $('global-status').textContent = error.message; } })();
