/* aac-access.js - access methods for people who cannot tap precisely (standard in AAC devices).
   Off (default) | Switch scanning: one switch (Space or Enter) - the highlight moves automatically, press to choose.
                   Two switches: Space moves, Enter chooses.  Group -> row -> button, like row-column scanning.
                 | Dwell: rest the pointer (mouse, head pointer or eye tracker) on a button to press it.
   Settings are kept per device in localStorage. No dependencies; works on the live React page. */
(function () {
  'use strict';
  var KEY = 'aac_access_v1';
  var GROUPS = ['.prediction-shelf', '.draft-actions', '.composer-actions', '.category-tabs', '.symbol-grid', '.quick-express'];
  var S = { mode: 'off', speed: 1200, dwell: 1000, colours: true, twoSwitch: false };
  try { Object.assign(S, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) {}
  function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} }

  function visible(el) { var r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; }
  function buttons(root) { return Array.prototype.filter.call(root.querySelectorAll('button:not([disabled]),[role="button"]'), visible); }
  function groups() {
    var out = [];
    GROUPS.forEach(function (sel) { document.querySelectorAll(sel).forEach(function (g) { if (visible(g) && buttons(g).length && out.indexOf(g) < 0) out.push(g); }); });
    return out;
  }
  function rows(items) {               // split a group's buttons into visual rows
    var r = [], top = null;
    items.forEach(function (b) { var t = Math.round(b.getBoundingClientRect().top); if (top === null || Math.abs(t - top) > 8) { r.push([]); top = t; } r[r.length - 1].push(b); });
    return r;
  }

  // ---------------- switch scanning ----------------
  var level = 0, list = [], idx = -1, timer = null, laps = 0, hl = [];
  function clearHl() { hl.forEach(function (e) { e.classList.remove('aac-scan-group', 'aac-scan-item'); }); hl = []; }
  function mark(target) {
    clearHl();
    var els = Array.isArray(target) ? target : [target];
    els.forEach(function (e) { e.classList.add(els.length > 1 || level === 0 ? 'aac-scan-group' : 'aac-scan-item'); hl.push(e); });
    var first = els[0]; if (first && first.scrollIntoView) first.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }
  function load(newLevel, items) { level = newLevel; list = items; idx = -1; laps = 0; }
  function top() { load(0, groups()); }
  function step() {
    if (!list.length) { top(); if (!list.length) return; }
    idx++;
    if (idx >= list.length) { idx = 0; laps++; if (level > 0 && laps >= 2) { top(); idx = 0; } }
    var t = list[idx];
    if (!t || (t.nodeType === 1 && !document.contains(t))) { top(); return; }
    mark(t);
  }
  function choose() {
    if (idx < 0 || !list[idx]) { step(); return; }
    var t = list[idx];
    if (level === 0) {                                    // group chosen -> rows (or buttons if one row)
      var r = rows(buttons(t));
      if (r.length > 1) load(1, r); else load(2, r[0] || []);
    } else if (level === 1) {
      load(2, t);
    } else {                                              // button chosen -> press it, start again from the top
      clearHl(); t.click(); top();
    }
    step(); restart();
  }
  function restart() { clearInterval(timer); timer = null; if (S.mode === 'scan' && !S.twoSwitch) timer = setInterval(step, S.speed); }
  function typing(e) { var t = e.target; return t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable) && !t.closest('.aac-access-panel'); }
  document.addEventListener('keydown', function (e) {
    if (S.mode !== 'scan' || typing(e) || e.target.closest && e.target.closest('.aac-access-panel')) return;
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      if (e.repeat) return;                              // a held switch counts once (tremor)
      if (S.twoSwitch && e.key === ' ') { step(); return; }
      choose();
    } else if (e.key === 'Escape') { top(); step(); }
  }, true);

  // ---------------- dwell ----------------
  var dwellEl = null, dwellT = null, fired = null;
  function stopDwell() { if (dwellEl) dwellEl.classList.remove('aac-dwell'); clearTimeout(dwellT); dwellEl = null; }
  document.addEventListener('pointerover', function (e) {
    if (S.mode !== 'dwell') return;
    var b = e.target.closest && e.target.closest('button,[role="button"]');
    if (!b || b === dwellEl || b.disabled || b.closest('.aac-access-panel,.aac-access-btn')) return;
    if (b === fired) return;                            // move off and back on to press the same button again
    stopDwell(); dwellEl = b; b.style.setProperty('--aac-dwell-ms', S.dwell + 'ms'); b.classList.add('aac-dwell');
    dwellT = setTimeout(function () { var x = dwellEl; stopDwell(); if (x && document.contains(x)) { fired = x; x.click(); } }, S.dwell);
  });
  document.addEventListener('pointerout', function (e) {
    var b = e.target.closest && e.target.closest('button,[role="button"]');
    if (!b) return;
    if (e.relatedTarget && b.contains(e.relatedTarget)) return;
    if (b === dwellEl) stopDwell();
    if (b === fired) fired = null;
  });

  // ---------------- settings panel ----------------
  function apply() {
    document.documentElement.setAttribute('data-aac-colours', S.colours ? 'on' : 'off');
    stopDwell(); clearHl();
    if (S.mode === 'scan') { top(); step(); }
    restart();
  }
  function opt(v, label, cur) { return '<option value="' + v + '"' + (String(v) === String(cur) ? ' selected' : '') + '>' + label + '</option>'; }
  function build() {
    var btn = document.createElement('button');
    btn.className = 'aac-access-btn'; btn.type = 'button'; btn.textContent = 'Access'; btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Access settings: switch scanning, dwell, word colours');
    var p = document.createElement('div');
    p.className = 'aac-access-panel'; p.hidden = true; p.setAttribute('role', 'dialog'); p.setAttribute('aria-label', 'Access settings');
    p.innerHTML =
      '<h2>How do you choose a button?</h2>' +
      '<fieldset><legend>Selection</legend>' +
      '<label><input type="radio" name="aac-mode" value="off"> Tap or click</label>' +
      '<label><input type="radio" name="aac-mode" value="scan"> Switch scanning (Space / Enter)</label>' +
      '<label><input type="radio" name="aac-mode" value="dwell"> Dwell (hold the pointer still)</label></fieldset>' +
      '<fieldset><legend>Timing</legend>' +
      '<label>Scan speed <select id="aac-speed">' + [800, 1200, 1600, 2200, 3000].map(function (v) { return opt(v, (v / 1000) + ' s', S.speed); }).join('') + '</select></label>' +
      '<label>Dwell time <select id="aac-dwell">' + [600, 1000, 1500, 2000, 3000].map(function (v) { return opt(v, (v / 1000) + ' s', S.dwell); }).join('') + '</select></label>' +
      '<label><input type="checkbox" id="aac-two"> Two switches (Space moves, Enter chooses)</label></fieldset>' +
      '<fieldset><legend>Board</legend><label><input type="checkbox" id="aac-colours"> Colour words by type</label></fieldset>' +
      '<p>Green: actions. Orange: things and places. Blue: describing words. Yellow: people. Pink: social words. Red: no, and urgent words.</p>';
    document.body.appendChild(btn); document.body.appendChild(p);
    p.querySelectorAll('input[name="aac-mode"]').forEach(function (r) { r.checked = r.value === S.mode; r.addEventListener('change', function () { S.mode = r.value; save(); apply(); }); });
    var sp = p.querySelector('#aac-speed'), dw = p.querySelector('#aac-dwell'), two = p.querySelector('#aac-two'), col = p.querySelector('#aac-colours');
    two.checked = !!S.twoSwitch; col.checked = !!S.colours;
    sp.addEventListener('change', function () { S.speed = +sp.value; save(); apply(); });
    dw.addEventListener('change', function () { S.dwell = +dw.value; save(); apply(); });
    two.addEventListener('change', function () { S.twoSwitch = two.checked; save(); apply(); });
    col.addEventListener('change', function () { S.colours = col.checked; save(); apply(); });
    btn.addEventListener('click', function () { p.hidden = !p.hidden; btn.setAttribute('aria-expanded', String(!p.hidden)); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !p.hidden) { p.hidden = true; btn.setAttribute('aria-expanded', 'false'); btn.focus(); } });
  }
  function init() {
    if (!document.querySelector('#communication-board')) { setTimeout(init, 500); return; }   // wait for the React board
    build(); apply();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
  window.AACAccess = { settings: function () { return Object.assign({}, S); } };
})();
