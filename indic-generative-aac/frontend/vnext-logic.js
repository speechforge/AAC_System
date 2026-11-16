/* Phase 1: concept meaning and stable layout slots are independent. Pure, browser/Node testable. */
(function (root) {
  'use strict';

  const board = root.AAC_CONCEPTS,
    langs = ['en', 'hi', 'gu', 'mr'];
  const anchors = {
    0: 'YES',
    1: 'NO',
    2: 'WANT',
    4: 'MORE',
    5: 'STOP'
  };
  const norm = s => (s || '').normalize('NFC').toLowerCase().replace(/[़઼‍‌]/g, '').replace(/ँ/g, 'ं').replace(/[.,!?;:।"“”‘’()\[\]/\\|•]/g, ' ').replace(/\s+/g, ' ').trim();
  const feelings = ['HAPPY', 'SAD', 'ANGRY', 'TIRED', 'SICK', 'SCARED', 'LOVE', 'EXCITED', 'PAIN'];
  const objects = Object.keys(board).filter(id => board[id].cat === 'food').concat('MEDICINE');
  function candidates(label, lg) {
    const n = norm(label),
      all = Object.keys(board).filter(id => langs.some(l => board[id][l].split(/\s*\/\s*/).some(v => norm(v) === n) || norm(board[id][l]) === n));
    const own = all.filter(id => norm(board[id][lg]) === n || board[id][lg].split(/\s*\/\s*/).some(v => norm(v) === n));
    return own.length ? own : all;
  }
  function analyze(items, lg = 'en', forced = null) {
    let count = 0,
      want = false,
      more = false,
      content = [];
    const resolved = items.map(it => ({
      cid: it.cid || null,
      label: it.label || '',
      cands: it.cid ? [] : candidates(it.label, lg)
    }));
    resolved.forEach((it, i) => {
      let cid = it.cid;
      if (!cid && it.cands.length) {
        const obj = it.cands.filter(c => objects.includes(c)),
          act = it.cands.filter(c => board[c].cat === 'actions');
        const otherObj = resolved.some((x, j) => j !== i && objects.includes(x.cid || x.cands[0]));
        cid = act.length && otherObj ? act[0] : obj[0] || it.cands[0];
      }
      if (!cid && ['no', 'not', 'नहीं', 'नही', 'ना', 'ના', 'नाही', 'नको'].includes(norm(it.label))) cid = 'NO';
      if (cid === 'NO') {
        count++;
        return;
      }
      if (cid === 'WANT') {
        want = true;
        return;
      }
      if (['PLEASE', 'YES', 'ME'].includes(cid)) return;
      if (cid === 'MORE') {
        more = true;
        return;
      }
      content.push({
        cid,
        label: it.label,
        cat: cid ? board[cid].cat : 'custom',
        more: false
      });
    });
    if (more) {
      const c = content.find(c => ['food', 'emergency'].includes(c.cat));
      if (c) c.more = true;
    }
    let negation = count % 2 === 1,
      amb = count > 1,
      act = 'UNKNOWN',
      frame = null;
    let feel = content.filter(c => feelings.includes(c.cid) || ['FEELING', 'FEELING_REQUEST'].includes(forced) && ['GOOD', 'BAD'].includes(c.cid)),
      objs = content.filter(c => objects.includes(c.cid)),
      acts = content.filter(c => c.cat === 'actions'),
      ppl = content.filter(c => c.cat === 'people'),
      help = content.filter(c => ['HELP', 'HELP_EMERGENCY'].includes(c.cid)),
      custom = content.filter(c => !c.cid);
    const known = [...feel, ...objs, ...acts, ...ppl, ...help, ...custom],
      other = content.filter(c => !known.includes(c));
    if (want && !feel.length && !acts.length && !help.length && !objs.length && (ppl.length || custom.length) && !other.length) {
      objs = [...ppl, ...custom];
      ppl = [];
      custom = [];
    }
    if (amb || !content.length) amb = true;else if (other.length) {
      amb = content.length === 1;
      if (content.some(c => ['NAMASTE', 'THANKS', 'BYE'].includes(c.cid)) && content.length <= 2) {
        act = 'GREETING';
        amb = false;
      } else if (acts.some(c => c.cid === 'GO')) act = 'REQUEST';
    } else if (feel.length) {
      if (feel.length > 1 || negation) {
        if (content.length === 1) {
          act = 'FEELING';
          frame = 'feeling';
        } else amb = true;
      } else if (content.length === 1) {
        act = 'FEELING';
        frame = 'feeling';
      } else {
        act = 'FEELING_REQUEST';
        frame = 'feeling_request';
      }
    } else if (help.length) {
      act = 'REQUEST';
      frame = 'help';
    } else if (acts.length) {
      act = 'REQUEST';
      frame = 'action';
    } else if (objs.length) {
      act = 'REQUEST';
      frame = 'object';
    } else amb = true;
    if (forced) {
      act = forced;
      amb = false;
      frame = forced === 'FEELING' && feel.length === 1 && content.length === 1 ? 'feeling' : forced === 'FEELING_REQUEST' && feel.length === 1 && content.length > 1 && !other.length ? 'feeling_request' : forced === 'REQUEST' && !other.length && !feel.length ? help.length ? 'help' : acts.length ? 'action' : objs.length || custom.length ? 'object' : null : null;
    }
    const angryFood = content.some(c => c.cid === 'ANGRY') && content.some(c => c.cid === 'FOOD');
    return {
      act,
      negation,
      ambiguous: amb || act === 'UNKNOWN',
      frame,
      content,
      n_negators: count,
      angryFood
    };
  }
  function slots(category) {
    const home = Object.keys(board).filter(id => board[id].cat === 'core');
    if (category === 'core') return home.map((cid, i) => ({
      slot: 'legacy:cell-' + i,
      cid
    }));
    const topic = Object.keys(board).filter(id => board[id].cat === category && !Object.values(anchors).includes(id)),
      out = [];
    let i = 0;
    for (let cell = 0; cell < Math.max(10, topic.length + 5); cell++) {
      const cid = anchors[cell] || topic[i++];
      out.push({
        slot: 'legacy:cell-' + cell,
        cid: cid || null
      });
    }
    return out;
  }
  function eligibility(data) {
    return ['sentence_model', 'sentence_template'].includes(data?.outcome) && data.validated === true;
  }
  root.AACVNext = {
    version: 1,
    board,
    langs,
    anchors,
    slots,
    analyze,
    eligible: eligibility,
    norm
  };
})(typeof window !== 'undefined' ? window : globalThis);
