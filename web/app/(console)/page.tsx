/**
 * anchor-spec.md §13.3 — fleet health at a glance. The duplicate-effect
 * count is the one figure permitted to render large here (§22.5); it reads
 * 0 explicitly, never hidden or blank (constitution Principle VIII).
 */
"use client";

import { useHealth } from "@/hooks/useHealth";
import { useMetrics } from "@/hooks/useMetrics";
import { StatTile } from "@/components/primitives/StatTile";

export default function DashboardPage() {
  const { data: health, stale: healthStale, error: healthError } = useHealth();
  const { data: metrics, stale: metricsStale } = useMetrics();

  if (healthError && !health) {
    return <p className="text-sm text-status-critical" data-testid="dashboard-error">could not reach the api</p>;
  }
  if (!health) {
    return <p className="text-sm text-ink-muted" data-testid="dashboard-loading">loading…</p>;
  }

  return (
    <div data-testid="dashboard">
      <h1 className="mb-4 font-ui text-base text-ink-primary">dashboard</h1>
      {(healthStale || metricsStale) && (
        <p className="mb-3 text-xs text-status-warning" data-testid="dashboard-stale">
          data may be stale — last refresh failed
        </p>
      )}
      <div className="grid grid-cols-4 gap-4">
        <StatTile label="duplicate side effects" value={metrics?.duplicate_side_effects ?? 0} emphasize />
        <StatTile label="active runs" value={health.running_run_count ?? 0} />
        <StatTile label="workers" value={health.worker_count} />
        <StatTile
          label="steps/sec"
          value={metrics?.steps_per_second !== undefined ? metrics.steps_per_second.toFixed(1) : "—"}
          sparkline={metrics?.run_state_distribution?.map((b) => Object.values(b.counts).reduce((a, c) => a + c, 0))}
        />
      </div>
    </div>
  );
}
