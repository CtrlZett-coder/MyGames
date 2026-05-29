const CACHE = 'space-shooter-v4';

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', e => {
  // Delete stale caches from old SW versions
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (!url.protocol.startsWith('http')) return;

  const isCDN = url.hostname === 'pygame-web.github.io';

  if (isCDN) {
    // Cache-first: Pyodide/pygame-web files don't change; serve instantly from cache
    e.respondWith(caches.open(CACHE).then(async cache => {
      const hit = await cache.match(e.request);
      if (hit) return hit;
      const res = await fetch(e.request);
      if (res.ok) cache.put(e.request, res.clone());
      return res;
    }));
  } else {
    // Network-first: our game files; fall back to cache when offline
    e.respondWith(caches.open(CACHE).then(async cache => {
      try {
        const res = await fetch(e.request);
        if (res.ok) cache.put(e.request, res.clone());
        return res;
      } catch (_) {
        const hit = await cache.match(e.request);
        return hit || new Response('', {status: 503});
      }
    }));
  }
});