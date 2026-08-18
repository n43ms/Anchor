"use client";

import { usePolling } from "./usePolling";
import { api } from "@/lib/api";
import type { Health } from "@/lib/types";

const HEALTH_POLL_INTERVAL_MS = 5_000;

/** Deployment mode and fleet health are read live — never assumed or cached
 * past a page load, since the mode banner and Environment-page gating both
 * depend on it being current (constitution §31 — capability gating is by
 * deployment mode, read from the server, never inferred client-side). */
export function useHealth() {
  return usePolling<Health>(api.health, HEALTH_POLL_INTERVAL_MS);
}
