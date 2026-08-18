"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface PollingState<T> {
  data: T | null;
  error: Error | null;
  stale: boolean;
}

/**
 * Fallback for when the WebSocket is unavailable (Redis down, per contracts/websocket.md —
 * "Redis is a delivery mechanism and nothing more"). Staleness is surfaced explicitly rather
 * than hidden behind the last-known-good value.
 */
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number, enabled = true): PollingState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [stale, setStale] = useState(false);
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const poll = useCallback(() => {
    fetcherRef.current()
      .then((result) => {
        setData(result);
        setError(null);
        setStale(false);
      })
      .catch((err: Error) => {
        setError(err);
        setStale(true);
      });
  }, []);

  useEffect(() => {
    if (!enabled) return;
    poll();
    const timer = window.setInterval(poll, intervalMs);
    return () => window.clearInterval(timer);
  }, [enabled, intervalMs, poll]);

  return { data, error, stale };
}
