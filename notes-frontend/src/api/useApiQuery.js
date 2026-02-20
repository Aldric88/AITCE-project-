import { useCallback, useEffect, useRef, useState } from "react";
import { cachedGet } from "./queryCache";

export function useApiQuery(
  key,
  fetcher,
  {
    enabled = true,
    staleTimeMs = 15000,
    refetchIntervalMs = 0,
    onError = null,
  } = {},
) {
  const [data, setData] = useState(null);
  const [isLoading, setIsLoading] = useState(Boolean(enabled));
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  const run = useCallback(
    async (force = false) => {
      if (!enabled) return null;
      setIsLoading(true);
      setError(null);
      try {
        const result = await fetcher({ force, staleTimeMs });
        if (mountedRef.current) setData(result);
        return result;
      } catch (err) {
        if (mountedRef.current) {
          setError(err);
          if (onError) onError(err);
        }
        return null;
      } finally {
        if (mountedRef.current) setIsLoading(false);
      }
    },
    [enabled, fetcher, staleTimeMs, onError],
  );

  useEffect(() => {
    mountedRef.current = true;
    run();
    return () => {
      mountedRef.current = false;
    };
  }, [key, run]);

  useEffect(() => {
    if (!enabled || !refetchIntervalMs) return undefined;
    const id = setInterval(() => {
      run();
    }, refetchIntervalMs);
    return () => clearInterval(id);
  }, [enabled, refetchIntervalMs, run]);

  return { data, isLoading, error, refetch: () => run(true), refresh: () => run(true) };
}

export function apiCachedFetcher(url) {
  return async ({ force = false, staleTimeMs = 15000 } = {}) =>
    cachedGet(url, { ttlMs: staleTimeMs, force }).then((res) => res.data);
}
