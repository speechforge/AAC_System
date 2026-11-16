/* Public vocabulary/authored audio only. Never cache APIs, sessions, or personal media. */
const POINTER = 'aac-public-vnext-1',
  ACTIVE = '/__aac-public-active';
async function installed() {
  const pointer = await caches.open(POINTER),
    entry = await pointer.match(ACTIVE);
  return entry ? caches.open(await entry.text()) : null;
}
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('message', event => {
  if (event.data?.type !== 'PROVISION') return;
  event.waitUntil((async () => {
    const port = event.ports[0],
      build = POINTER + '-build-' + crypto.randomUUID();
    try {
      const assets = await fetch('/static/public-assets.json', {
          cache: 'no-store'
        }).then(r => r.json()),
        pack = await fetch('/static/quick-pack.json', {
          cache: 'no-store'
        }).then(r => r.json());
      if (pack.phrases.length !== 16 || pack.phrases.some(p => !p.audio || !p.sha256)) throw Error('The complete 16-phrase audio pack is not available.');
      const stage = await caches.open(build);
      for (const path of assets.assets) {
        const r = await fetch(path, {
          cache: 'no-store',
          credentials: 'omit'
        });
        if (!r.ok) throw Error('Missing public asset: ' + path);
        await stage.put(path, r);
      }
      for (const item of pack.phrases) {
        const r = await fetch(item.audio, {
          cache: 'no-store',
          credentials: 'omit'
        });
        if (!r.ok) throw Error('Missing recording: ' + item.audio);
        const raw = await r.clone().arrayBuffer(),
          hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', raw))).map(x => x.toString(16).padStart(2, '0')).join('');
        if (hash !== item.sha256) throw Error('Recording hash mismatch: ' + item.audio);
        await stage.put(item.audio, r);
      }
      // One pointer write commits a fully verified pack; a failed build retains the last active pack.
      await (await caches.open(POINTER)).put(ACTIVE, new Response(build));
      for (const key of await caches.keys()) if (key.startsWith(POINTER + '-build-') && key !== build) await caches.delete(key);
      port.postMessage({
        ok: true,
        version: 1,
        clips: 16
      });
    } catch (e) {
      await caches.delete(build);
      port.postMessage({
        ok: false,
        error: e.message
      });
    }
  })());
});
self.addEventListener('fetch', event => {
  const u = new URL(event.request.url);
  if (u.origin !== location.origin || event.request.method !== 'GET') return;
  if (event.request.mode === 'navigate' && ['/', '/index.html'].includes(u.pathname)) {
    event.respondWith(fetch(event.request).catch(async () => {
      const c = await installed();
      return c && (await c.match('/')) || new Response('Open Indic AAC Studio online once and choose Set up offline phrases.', {
        status: 503,
        headers: {
          'Content-Type': 'text/plain;charset=utf-8'
        }
      });
    }));
    return;
  }
  if (u.pathname.startsWith('/static/') && !u.pathname.startsWith('/static/audio/') || u.pathname.startsWith('/static/audio/quick-v1/')) event.respondWith((async () => {
    const c = await installed();
    return c && (await c.match(event.request)) || fetch(event.request);
  })());
});
