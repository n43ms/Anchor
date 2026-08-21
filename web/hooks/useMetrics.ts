"use client";

import { usePolling } from "./usePolling";
import { api } from "@/lib/api";
import type { Metrics } from "@/lib/types";

const METRICS_POLL_INTERVAL_MS = 5_000;

export function useMetrics(window = "24h") {
  return usePolling<Metrics>(() => api.getMetrics(window), METRICS_POLL_INTERVAL_MS);
}
