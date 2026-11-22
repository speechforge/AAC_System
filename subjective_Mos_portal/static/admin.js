'use strict';
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let csrf = '', data = null, selectedParticipant = '', detailOpener = null, loading = false;
const langNames = {en:'English',gu:'Gujarati',hi:'Hindi',mr:'Marathi'};
const scoreNames = ['Bad','Poor','Fair','Good','Excellent'];
const fmt = (value,digits=2) => value === null || value === undefined ? '—' : Number(value).toFixed(digits);
async function api(path, body) {
  let response;
  try { response = await fetch(path,{method:body === undefined?'GET':'POST',credentials:'same-origin',headers:body === undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body === undefined?undefined:JSON.stringify(body)}); }
  catch {throw new Error('Connection interrupted. Reconnect and refresh the results.');}
  const result = await response.json();
  if (!response.ok) {const error = new Error(typeof result.detail === 'string'?result.detail:'Please check your input.');error.status=response.status;throw error;}
  return result;
}
function filters() {
  return new URLSearchParams({include_partial:String($('partial-filter').checked),include_excluded:String($('excluded-filter').checked),participant_id:$('subject-filter').value});
}
async function refresh() {
  if (loading) return; loading=true; $('dashboard-error').textContent=''; $('refresh-dashboard').disabled=true;
  try {
    data=await api('/api/admin/dashboard?'+filters());
    render(); $('last-updated').textContent='Updated '+new Date().toLocaleTimeString();
  } catch(error) {
    if(error.status===401){showLogin();$('login-error').textContent='Your session expired. Please sign in again.';}
    else $('dashboard-error').textContent=error.message;
  } finally {loading=false;$('refresh-dashboard').disabled=false;}
}
function showLogin() {$('admin-login').hidden=false;$('admin-dashboard').hidden=true;$('admin-logout').hidden=true;csrf='';}
function openDashboard() {$('admin-login').hidden=true;$('admin-dashboard').hidden=false;$('admin-logout').hidden=false;refresh();}
$('admin-login-form').onsubmit=async event=>{
  event.preventDefault();const form=event.currentTarget;const button=form.querySelector('button');button.disabled=true;$('login-error').textContent='';
  try {const result=await api('/api/admin/login',Object.fromEntries(new FormData(form)));csrf=result.csrf;form.reset();openDashboard();}
  catch(error){$('login-error').textContent=error.message;} finally{button.disabled=false;}
};
$('admin-logout').onclick=async()=>{try{await api('/api/admin/logout',{});data=null;showLogin();}catch(error){$('dashboard-error').textContent=error.message;}};
function render() {
  const c=data.counts;
  const summary=[['Overall MOS',fmt(data.overall.mos),`${data.overall.n} ratings in this view`],['Registered listeners',c.registered,`${c.excluded} explicitly excluded`],['Completed sessions',c.completed,'20 of 20 recordings rated'],['Saved ratings',c.ratings_all,`${c.in_progress} sessions in progress`]];
  $('summary-cards').innerHTML=summary.map(([label,value,note])=>`<article class="summary-card"><span>${label}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`).join('');
  $('language-cards').innerHTML=data.languages.map(row=>`<article class="language-card"><h3>${esc(row.label)}</h3><div class="mos-number">${fmt(row.mos)}<small>/ 5</small></div><p>${row.participants} listener${row.participants===1?'':'s'} · ${row.n} ratings · 5 files<br>SD ${fmt(row.std)}<br>95% CI ${row.ci95?`${fmt(row.ci95[0])} – ${fmt(row.ci95[1])}`:'—'}</p></article>`).join('');
  $('stats-method').textContent=data.method;
  const max=Math.max(1,...Object.values(data.distribution));
  $('score-distribution').innerHTML=Object.entries(data.distribution).map(([score,count])=>`<div class="distribution-row"><span>${score} · ${scoreNames[Number(score)-1]}</span><div class="distribution-track"><div class="distribution-fill" style="width:${count/max*100}%"></div></div><strong>${count}</strong></div>`).join('');
  $('distribution-total').textContent=data.overall.n+' ratings in this view';
  const old=$('subject-filter').value;
  $('subject-filter').innerHTML='<option value="">All participants</option>'+data.participants.map(p=>`<option value="${esc(p.participant_id)}">${esc(p.name)} · ${esc(p.participant_id)}</option>`).join('');
  $('subject-filter').value=old;
  renderPeople();renderFiles();
  const summaryParams=filters();
  document.querySelectorAll('.summary-export').forEach(link=>{link.href='/api/admin/export/'+link.dataset.kind+'?'+summaryParams;});
}
function renderPeople(){
  if(!data)return;const search=$('participant-search').value.trim().toLocaleLowerCase();
  const rows=data.participants.filter(p=>[p.name,p.email,p.participant_id,p.organization].join(' ').toLocaleLowerCase().includes(search));
  $('participant-rows').innerHTML=rows.length?rows.map(p=>`<tr><td><strong>${esc(p.name)}</strong><small>${esc(p.participant_id)}</small><small>${esc(p.email)}</small></td><td>${p.age} · ${esc(p.gender)}</td><td>${esc(p.mother_tongue)}</td><td>${esc(p.organization)}</td><td><strong>${p.trials_completed}/20</strong></td><td><span class="status-tag ${p.is_excluded?'excluded':p.trials_completed===20?'complete':''}">${p.is_excluded?'Excluded':p.trials_completed===20?'Completed':'In progress'}</span></td><td><button class="table-action" data-person="${esc(p.participant_id)}" aria-label="View ${esc(p.name)}">View details</button></td></tr>`).join(''):'<tr><td class="empty-row" colspan="7">'+(search?'No matching participants.':'No participants yet. Share the listener portal to begin collecting responses.')+'</td></tr>';
}
function renderFiles(){
  if(!data)return;const language=$('file-language').value;const rows=data.files.filter(row=>!language||row.language===language);
  $('file-rows').innerHTML=rows.map(row=>`<tr><td class="mono">${esc(row.id)}</td><td>${langNames[row.language]}</td><td lang="${row.language}">${esc(row.text)}</td><td>${row.n}</td><td><strong>${fmt(row.mos)}</strong></td><td>${fmt(row.std)}</td></tr>`).join('');
}
async function openDetails(id,opener){
  $('dashboard-error').textContent='';
  try{
    const result=await api('/api/admin/participants/'+encodeURIComponent(id));selectedParticipant=id;detailOpener=opener;
    const p=result.participant;$('detail-title').textContent=p.name+' · '+p.participant_id;
    const fields=[['Email',p.email],['Age / gender',`${p.age} · ${p.gender}`],['Mother tongue',p.mother_tongue],['Organization',p.organization],['Registered (UTC)',p.registered_iso],['Completed (UTC)',p.completed_iso||'In progress']];
    $('participant-details').innerHTML='<div class="detail-grid">'+fields.map(([label,value])=>`<div><small>${label}</small>${esc(value)}</div>`).join('')+'</div><div class="table-wrap"><table><thead><tr><th>Trial</th><th>Language</th><th>Spoken text</th><th>Score</th><th>Replays / plays</th><th>Rated (UTC)</th></tr></thead><tbody>'+result.trials.map(t=>`<tr><td>${t.position+1}</td><td>${langNames[t.language]}</td><td lang="${t.language}">${esc(t.text)}</td><td class="detail-score">${t.score??'—'}</td><td>${t.play_count}</td><td class="small">${esc(t.rated_iso||'Not rated')}</td></tr>`).join('')+'</tbody></table></div>';
    $('exclude-person').checked=!!p.is_excluded;$('exclusion-reason').value=p.exclusion_reason;$('exclusion-error').textContent='';$('participant-dialog').showModal();$('close-detail').focus();
  }catch(error){$('dashboard-error').textContent=error.message;}
}
$('participant-rows').onclick=event=>{const button=event.target.closest('[data-person]');if(button)openDetails(button.dataset.person,button);};
$('close-detail').onclick=()=>$('participant-dialog').close();
$('participant-dialog').onclose=()=>{if(detailOpener?.isConnected)detailOpener.focus();};
$('exclusion-form').onsubmit=async event=>{
  event.preventDefault();const button=event.currentTarget.querySelector('button');button.disabled=true;$('exclusion-error').textContent='';
  try{await api(`/api/admin/participants/${encodeURIComponent(selectedParticipant)}/exclusion`,{excluded:$('exclude-person').checked,reason:$('exclusion-reason').value});$('participant-dialog').close();await refresh();}
  catch(error){$('exclusion-error').textContent=error.message;}finally{button.disabled=false;}
};
$('participant-search').oninput=renderPeople;$('file-language').onchange=renderFiles;
for(const id of ['partial-filter','excluded-filter','subject-filter'])$(id).onchange=refresh;
$('refresh-dashboard').onclick=refresh;
setInterval(()=>{if(!$('admin-dashboard').hidden&&!document.hidden&&!$('participant-dialog').open&&!['INPUT','SELECT','TEXTAREA','BUTTON'].includes(document.activeElement?.tagName))refresh();},20000);
(async()=>{try{const result=await api('/api/admin/me');csrf=result.csrf;openDashboard();}catch{showLogin();}})();
