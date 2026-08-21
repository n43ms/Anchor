/**
 * Present at all times (constitution → Console Surface and Deployment
 * Modes). Also the one place staleness of the health read itself is worth
 * saying out loud, since every capability gate downstream depends on it.
 */
"use client";

import { useHealth } from "@/hooks/useHealth";

export function ModeBanner() {
  const { data, stale } = useHealth();

  if (!data) {
    return (
      <div className="border-b border-gridline bg-surface-panel/80 px-4 py-1.5 text-xs text-ink-muted flex items-center justify-between" data-testid="mode-banner">
        <span>connecting to the api…</span>
      </div>
    );
  }

  const modeLabel = data.deployment_mode === "demonstration" ? "demonstration mode" : "local mode";

  return (
    <div
      className="flex items-center justify-between border-b border-gridline bg-surface-panel/90 px-4 py-1.5 text-xs backdrop-blur-md"
      data-testid="mode-banner"
      data-deployment-mode={data.deployment_mode}
    >
      <div className="flex items-center gap-2">
        <span className={`inline-block h-2 w-2 rounded-full ${data.database_reachable ? "bg-status-good animate-pulse" : "bg-status-critical"}`} />
        <span className="text-ink-secondary font-medium">{modeLabel}</span>
      </div>

      <div className="flex items-center gap-3">
        {!data.database_reachable && (
          <span className="rounded bg-status-critical/15 px-2 py-0.5 text-status-critical font-medium border border-status-critical/30">
            database unreachable — execution halted
          </span>
        )}
        {stale && (
          <span className="rounded bg-status-warning/15 px-2 py-0.5 text-status-warning font-medium border border-status-warning/30">
            stale — last health check failed
          </span>
        )}
        {data.database_reachable && !stale && (
          <span className="text-[11px] text-ink-muted">
            fleet: <strong className="text-ink-primary font-data">{data.worker_count}</strong> worker{data.worker_count === 1 ? "" : "s"}
          </span>
        )}
      </div>
    </div>
  );
}
