"use client";

import { usePolling } from "./usePolling";
import { api } from "@/lib/api";

const POLL_INTERVAL_MS = 4_000;

export function useNeedsReview() {
  return usePolling(() => api.listRuns({ status: ["needs_review"] }), POLL_INTERVAL_MS);
}
