"use client";

import { useCallback, useState } from "react";
import { usePolling } from "./usePolling";
import { api, ApiRequestError } from "@/lib/api";
import type { ChaosParams, ChaosReport, ChaosRun } from "@/lib/types";

const ACTIVE_RUN_POLL_INTERVAL_MS = 2_000;
const HISTORY_POLL_INTERVAL_MS = 5_000;

/**
 * The chaos console's launch control and the live status of whatever run
 * it started, if any. Polling only (`usePolling`) — no query library
 * (D-31) and no WebSocket channel is defined for chaos runs, so this
 * console page reads its own state back the same way every other polled
 * view in this console does.
 */
export function useChaosLaunch(): {
  activeRun: ChaosRun | null;
  launching: boolean;
  error: string | null;
  launch: (params: ChaosParams) => void;
} {
  const [activeRun, setActiveRun] = useState<ChaosRun | null>(null);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const poll = usePolling<ChaosRun>(
    useCallback(() => {
      if (activeRun === null) return Promise.resolve(activeRun as unknown as ChaosRun);
      // No GET /api/chaos/{id} exists for a single run's current status —
      // history already carries it, freshest-first, so this reads that
      // instead of inventing a second endpoint for one field.
      return api.listChaosRuns().then((history) => {
        const found = history.items.find((item) => item.id === activeRun.id);
        return (found ?? activeRun) as ChaosRun;
      });
    }, [activeRun]),
    ACTIVE_RUN_POLL_INTERVAL_MS,
    activeRun !== null && activeRun.status === "running",
  );

  const launch = (params: ChaosParams) => {
    setLaunching(true);
    setError(null);
    api
      .startChaos(params)
      .then((run) => setActiveRun(run))
      .catch((err: unknown) => {
        setError(err instanceof ApiRequestError ? err.message : "failed to launch chaos run");
      })
      .finally(() => setLaunching(false));
  };

  return { activeRun: poll.data ?? activeRun, launching, error, launch };
}

/** Chaos history (`GET /api/chaos`) — every past run with its final report,
 * retained permanently (§13.3). `report` is `null` for a run still in
 * progress or one that failed before producing one. */
export function useChaosHistory(): {
  items: Array<ChaosRun & { report: ChaosReport | null }>;
  stale: boolean;
  refresh: () => void;
} {
  const poll = usePolling<{ items: Array<ChaosRun & { report: ChaosReport | null }> }>(
    () => api.listChaosRuns(),
    HISTORY_POLL_INTERVAL_MS,
  );
  return { items: poll.data?.items ?? [], stale: poll.stale, refresh: poll.refresh };
}

/** The most recent completed report — absent (not a placeholder) when none
 * exists yet (FR-104, constitution Principle VIII). */
export function useLatestChaosReport(): { report: ChaosReport | null; loading: boolean } {
  const [loading, setLoading] = useState(true);
  const poll = usePolling<ChaosReport | null>(
    useCallback(
      () =>
        api
          .getLatestChaosReport()
          .then((r) => {
            setLoading(false);
            return r;
          })
          .catch((err: unknown) => {
            setLoading(false);
            if (err instanceof ApiRequestError && err.status === 404) return null;
            throw err;
          }),
      [],
    ),
    HISTORY_POLL_INTERVAL_MS,
  );
  return { report: poll.data ?? null, loading };
}
