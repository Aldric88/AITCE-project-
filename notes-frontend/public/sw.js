const CACHE_NAME = "notes-market-shell-v1";
const CORE_ASSETS = ["/", "/manifest.webmanifest", "/vite.svg"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_NAME)
          .map((k) => caches.delete(k)),
      ),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  event.respondWith(
    caches.match(req).then((cached) => {
      if (cached) return cached;
      return fetch(req)
        .then((res) => {
          const url = new URL(req.url);
          // Cache static assets and app shell; skip API routes.
          if (!url.pathname.startsWith("/api") && req.url.includes(self.location.origin)) {
            const cloned = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, cloned));
          }
          return res;
        })
        .catch(() => caches.match("/"));
    }),
  );
});
