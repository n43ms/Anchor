"use client";

import { usePolling } from "./usePolling";
import { api } from "@/lib/api";

export function useTools() {
  return usePolling(api.listTools, 10_000);
}
