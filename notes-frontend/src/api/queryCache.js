import api from "./axios";

const cache = new Map();

function now() {
  return Date.now();
}

export async function cachedGet(url, { ttlMs = 30000, force = false } = {}) {
  const key = `GET:${url}`;
  const existing = cache.get(key);

  if (!force && existing && existing.expiresAt > now()) {
    return existing.value;
  }
  if (!force && existing?.promise) {
    return existing.promise;
  }

  const promise = api.get(url).then((res) => {
    cache.set(key, {
      value: res,
      expiresAt: now() + ttlMs,
    });
    return res;
  }).catch((err) => {
    cache.delete(key);
    throw err;
  });

  cache.set(key, { promise, expiresAt: now() + ttlMs });
  return promise;
}

export function invalidateGet(url) {
  cache.delete(`GET:${url}`);
}

export function invalidatePrefix(prefix) {
  for (const key of cache.keys()) {
    if (key.startsWith(`GET:${prefix}`)) cache.delete(key);
  }
}
