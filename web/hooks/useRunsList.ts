"use client";

import { usePolling } from "./usePolling";
import { api } from "@/lib/api";
import type { RunListItem, RunStatus } from "@/lib/types";

const RUNS_POLL_INTERVAL_MS = 3_000;

export function useRunsList(status?: RunStatus[]) {
  return usePolling<{ items: RunListItem[]; next_cursor: string | null }>(
    () => api.listRuns(status ? { status } : undefined),
    RUNS_POLL_INTERVAL_MS,
  );
}
