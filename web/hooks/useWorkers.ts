"use client";

import { useFleetStream } from "./useFleetStream";
import { usePolling } from "./usePolling";
import { api } from "@/lib/api";
import type { Worker } from "@/lib/types";

const WORKERS_POLL_INTERVAL_MS = 4_000;

/** Prefers the live stream; falls back to polling when the socket is down
 * (Redis is a delivery mechanism only — execution is unaffected either way). */
export function useWorkers(): { workers: Worker[]; stale: boolean; degraded: boolean } {
  const stream = useFleetStream();
  const poll = usePolling<{ items: Worker[] }>(api.listWorkers, WORKERS_POLL_INTERVAL_MS, !stream.connected);

  if (stream.connected) {
    return { workers: stream.workers, stale: stream.stale, degraded: stream.degraded };
  }
  return { workers: poll.data?.items ?? [], stale: poll.stale, degraded: false };
}
