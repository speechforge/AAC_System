/* One cancellation domain for explicit speech, tiles, Quick Express, and Stop. */
(() => {
  'use strict';

  let epoch = 0,
    controller = null,
    audio = null,
    locked = false,
    active = null;
  let bank = null;
  const emit = (status, extra = {}) => window.dispatchEvent(new CustomEvent('aac-playback', {
    detail: {
      status,
      ...extra
    }
  }));
  const allAudio = window.AACAudioElements || (window.AACAudioElements = new Set());
  function stop() {
    epoch++;
    controller?.abort();
    controller = null;
    if (audio) {
      audio.pause();
      audio.removeAttribute?.('src');
      audio = null;
    }
    try {
      speechSynthesis.cancel();
    } catch (_) {}
    for (const item of allAudio) { try { item.pause(); } catch (_) {} }
    allAudio.clear();
    document.querySelectorAll('audio').forEach(item => { try { item.pause(); } catch (_) {} });
    window.dispatchEvent(new Event('aac-stop-all'));
    locked = false;
    active = null;
    emit('stopped');
  }
  async function pack() {
    if (!bank) {
      const r = await fetch('/static/quick-pack.json');
      if (!r.ok) throw Error('Offline pack manifest unavailable');
      bank = await r.json();
    }
    return bank;
  }
  async function play(text, language, options = {}) {
    if (!text.trim() || options.kind === 'tile' && locked) return {
      started: false
    };
    stop();
    const ticket = epoch;
    locked = options.kind !== 'tile';
    controller = new AbortController();
    const ownController = controller;
    const id = options.eventId || crypto.randomUUID(),
      profile = options.profile || null;
    const start = performance.now();
    let began = false;
    const onStart = () => {
      if (ticket !== epoch || began) return;
      began = true;
      active = {
        text,
        language,
        eventId: id,
        profile
      };
      emit('playing', {
        ...active,
        onsetMs: performance.now() - start,
        kind: options.kind
      });
    };
    emit('loading', {
      text,
      language
    });
    try {
      let source;
      if (options.quick) {
        const manifest = await pack();
        const clip = manifest.phrases.find(p => p.key === options.quick && p.language === language && p.text === text);
        if (!clip?.audio) throw Error('Matching local audio is not installed. Show message or set up offline audio.');
        let r = null;
        if ('caches' in window) {
          const pointer = await (await caches.open('aac-public-vnext-1')).match('/__aac-public-active');
          if (pointer) {
            const installed = await caches.open(await pointer.text());
            r = await installed.match(clip.audio);
            if (!r) throw Error('Local recording missing. Set up offline audio.');
          }
        }
        // When a verified pack is installed, use its bytes directly; never replace a missing clip silently.
        if (!r) r = await fetch(clip.audio, {signal: ownController.signal});
        if (!r.ok) throw Error('Local recording missing. Set up offline audio.');
        const raw = await r.arrayBuffer();
        const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', raw))).map(b => b.toString(16).padStart(2, '0')).join('');
        if (hash !== clip.sha256) throw Error('Recording verification failed. Set up the audio pack again.');
        source = URL.createObjectURL(new Blob([raw], {
          type: 'audio/wav'
        }));
      } else {
        const r = await fetch('/api/tts', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json'
          },
          signal: ownController.signal,
          body: JSON.stringify({
            text,
            language,
            voice_id: options.voice || language
          })
        });
        const data = await r.json();
        if (!r.ok || !data.audio_b64) throw Error(typeof data.detail === 'string' ? data.detail : 'Speech unavailable for this message and language.');
        source = 'data:audio/wav;base64,' + data.audio_b64;
      }
      if (ticket !== epoch) {
        if (source.startsWith('blob:')) URL.revokeObjectURL(source);
        return {
          started: false
        };
      }
      const current = new Audio(source);
      audio = current;
      allAudio.add(current);
      current.playbackRate = options.rate || 1;
      current.preservesPitch = true;
      const clean = () => {
        allAudio.delete(current);
        if (source.startsWith('blob:')) URL.revokeObjectURL(source);
        if (ticket === epoch) {
          locked = false;
          emit('ended', {
            text,
            language
          });
        }
      };
      current.onplaying = onStart;
      current.onended = clean;
      current.onerror = () => {
        clean();
        if (ticket === epoch) emit('error', {
          text,
          language,
          message: 'Audio could not play. The full message is still available.'
        });
      };
      await current.play();
      return {
        started: began,
        eventId: id
      };
    } catch (error) {
      if (ticket === epoch) {
        locked = false;
        if (error.name !== 'AbortError') emit('error', {
          text,
          language,
          message: error.message
        });
      }
      return {
        started: false,
        eventId: id
      };
    }
  }
  function localVoice(text, language, options = {}) {
    const voices = window.speechSynthesis?.getVoices().filter(v => v.localService && v.lang.split('-')[0] === language) || [];
    if (!voices.length) {
      emit('error', {
        text,
        language,
        message: 'No matching on-device voice is available. Use Show message.'
      });
      return false;
    }
    stop();
    const ticket = epoch,
      u = new SpeechSynthesisUtterance(text);
    u.voice = voices[0];
    u.lang = u.voice.lang;
    u.rate = options.rate || 1;
    locked = true;
    u.onstart = () => {
      if (ticket === epoch) emit('playing', {
        text,
        language,
        eventId: crypto.randomUUID(),
        profile: options.profile,
        kind: 'system'
      });
    };
    u.onend = () => {
      if (ticket === epoch) {
        locked = false;
        emit('ended', {
          text,
          language
        });
      }
    };
    u.onerror = () => {
      if (ticket === epoch) {
        locked = false;
        emit('error', {
          text,
          language,
          message: 'On-device voice failed. Use Show message.'
        });
      }
    };
    speechSynthesis.speak(u);
    return true;
  }
  async function provision() {
    if (!('serviceWorker' in navigator)) throw Error('Offline setup requires service worker support on HTTPS or localhost.');
    const reg = await navigator.serviceWorker.register('/aac-sw.js', {
      scope: '/'
    });
    await reg.update();
    await navigator.serviceWorker.ready;
    const worker = reg.installing || reg.waiting || reg.active;
    if (worker.state !== 'activated') await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(Error('Offline worker activation timed out. Retry setup.')), 30000);
      worker.addEventListener('statechange', () => {
        if (worker.state === 'activated') {
          clearTimeout(timeout);
          resolve();
        } else if (worker.state === 'redundant') {
          clearTimeout(timeout);
          reject(Error('Offline worker was replaced. Retry setup.'));
        }
      });
    });
    return new Promise((resolve, reject) => {
      const channel = new MessageChannel(),
        timer = setTimeout(() => reject(Error('Offline setup timed out. Retry while online.')), 120000);
      channel.port1.onmessage = e => {
        clearTimeout(timer);
        e.data.ok ? resolve(e.data) : reject(Error(e.data.error));
      };
      worker.postMessage({
        type: 'PROVISION'
      }, [channel.port2]);
    });
  }
  async function readiness() {
    if (!('caches' in window)) return false;
    const pointer = await caches.open('aac-public-vnext-1'),
      entry = await pointer.match('/__aac-public-active');
    if (!entry) return false;
    const active = await caches.open(await entry.text());
    const manifest = await active.match('/static/quick-pack.json');
    if (!manifest) return false;
    const data = await manifest.json();
    return data.phrases.length === 16 && (await Promise.all(data.phrases.map(p => active.match(p.audio)))).every(Boolean);
  }
  window.AACPlayback = {
    stop,
    play,
    localVoice,
    pack,
    provision,
    readiness,
    get active() {
      return active;
    }
  };
  window.addEventListener('pagehide', stop);
})();
