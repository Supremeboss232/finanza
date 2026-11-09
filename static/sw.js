const CACHE_NAME = 'finanza-pwa-v1';
const STATIC_ASSETS = [
  '/manifest.json',
  '/static/css/mobile.css',
  '/static/css/admin-portal.css',
  '/static/js/admin-guard.js?v=3',
  '/static/js/admin-shell.js?v=3',
  '/static/js/toast-utils.js',
  '/static/js/pwa-init.js',
  '/static/img/icon-192.png',
  '/static/img/icon-512.png',
  '/static/img/apple-touch-icon.png'
];

const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Finanza — Reconnecting</title>
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
      color: #fff;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      padding: 24px;
      text-align: center;
    }
    .card {
      background: rgba(255,255,255,0.08);
      border: 1px solid rgba(255,255,255,0.16);
      border-radius: 16px;
      padding: 32px 24px;
      max-width: 380px;
      width: 100%;
      backdrop-filter: blur(12px);
    }
    .logo {
      width: 64px;
      height: 64px;
      border-radius: 16px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 30px;
      font-weight: 800;
      margin-bottom: 16px;
    }
    h2 { margin: 0 0 8px; font-size: 1.35rem; }
    p { margin: 0 0 20px; color: #cbd5e1; font-size: 0.92rem; line-height: 1.5; }
    button {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: #fff;
      border: none;
      padding: 12px 24px;
      border-radius: 10px;
      font-weight: 700;
      font-size: 0.95rem;
      cursor: pointer;
      width: 100%;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">F</div>
    <h2>Connection Interrupted</h2>
    <p>Finanza is waiting for your network or server tunnel to reconnect. Your session is safe.</p>
    <button onclick="window.location.reload()">Retry Connection</button>
  </div>
</body>
</html>`;

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  // Never cache API calls — always go to network
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/')) {
    return;
  }

  // Navigation requests (HTML pages): network-first, fallback to cached copy or offline screen
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE_NAME).then((c) => c.put(req, copy)).catch(() => {});
          return res;
        })
        .catch(() =>
          caches.match(req).then(
            (cached) =>
              cached ||
              new Response(OFFLINE_HTML, {
                status: 200,
                headers: { 'Content-Type': 'text/html; charset=utf-8' }
              })
          )
        )
    );
    return;
  }

  // Static assets: stale-while-revalidate
  if (url.pathname.startsWith('/static/') || url.pathname === '/manifest.json') {
    event.respondWith(
      caches.match(req).then((cached) => {
        const networkFetch = fetch(req)
          .then((res) => {
            if (res && res.status === 200) {
              const copy = res.clone();
              caches.open(CACHE_NAME).then((c) => c.put(req, copy)).catch(() => {});
            }
            return res;
          })
          .catch(() => cached);
        return cached || networkFetch;
      })
    );
  }
});
