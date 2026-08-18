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
      <div className="border-b border-gridline bg-surface-panel px-4 py-1.5 text-xs text-ink-muted" data-testid="mode-banner">
        connecting to the api…
      </div>
    );
  }

  const modeLabel = data.deployment_mode === "demonstration" ? "demonstration mode" : "local mode";

  return (
    <div
      className="flex items-center justify-between border-b border-gridline bg-surface-panel px-4 py-1.5 text-xs"
      data-testid="mode-banner"
      data-deployment-mode={data.deployment_mode}
    >
      <span className="text-ink-secondary">{modeLabel}</span>
      {!data.database_reachable && <span className="text-status-critical">database unreachable — execution halted</span>}
      {stale && <span className="text-status-warning">stale — last health check failed</span>}
    </div>
  );
}
