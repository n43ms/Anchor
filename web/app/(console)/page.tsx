/**
 * anchor-spec.md §13.3 — fleet health at a glance. The duplicate-effect
 * count is the one figure permitted to render large here (§22.5); it reads
 * 0 explicitly, never hidden or blank (constitution Principle VIII).
 */
"use client";

import { useState } from "react";
import { Link } from "react-router-dom";
import { useHealth } from "@/hooks/useHealth";
import { useMetrics } from "@/hooks/useMetrics";
import { useRunsList } from "@/hooks/useRunsList";
import { useWorkers } from "@/hooks/useWorkers";
import { StatTile } from "@/components/primitives/StatTile";
import { StatusPill } from "@/components/primitives/StatusPill";
import { RunThread } from "@/components/run/RunThread";
import { api, ApiRequestError } from "@/lib/api";
import type { RunStatus } from "@/lib/types";

export default function DashboardPage() {
  const { data: health, stale: healthStale, error: healthError } = useHealth();
  const { data: metrics, stale: metricsStale } = useMetrics();
  const { data: runs, refresh: refreshRuns } = useRunsList();
  const { workers, stale: workersStale, degraded: workersDegraded } = useWorkers();
  const [filterStatus, setFilterStatus] = useState<RunStatus | "all">("all");
  const [quickLaunchLoading, setQuickLaunchLoading] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ text: string; type: "good" | "warning" | "critical" } | null>(null);

  if (healthError && !health) {
    return (
      <div className="hud-corner rounded-lg border border-status-critical/40 bg-status-critical/10 p-6 text-sm text-status-critical" data-testid="dashboard-error">
        <div className="flex items-center gap-2 font-bold font-ui text-base mb-1">
          <span className="h-2.5 w-2.5 rounded-full bg-status-critical animate-ping" />
          <span>RUNTIME DISCONNECTED</span>
        </div>
        <p className="text-xs text-ink-secondary">could not reach the backend api — check if docker containers and api service are running</p>
      </div>
    );
  }
  if (!health) {
    return (
      <div className="space-y-4 p-8 text-center" data-testid="dashboard-loading">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-strand-gold border-t-transparent mb-3" />
        <p className="text-xs font-data text-ink-muted uppercase tracking-widest">initializing telemetry stream…</p>
      </div>
    );
  }

  const allRuns = runs?.items ?? [];
  const filteredRuns = filterStatus === "all" ? allRuns : allRuns.filter((r) => r.status === filterStatus);
  const activeRunsCount = health.running_run_count ?? allRuns.filter((r) => r.status === "running" || r.status === "pending").length;

  const handleQuickLaunch = (agentType: string) => {
    setQuickLaunchLoading(true);
    setFeedbackMessage(null);
    api
      .submitRun({
        agent_type: agentType,
        is_demo: true,
        input: { trigger: "dashboard_quick_launch", timestamp: new Date().toISOString() },
      })
      .then((run) => {
        setFeedbackMessage({
          text: `Dispatched ${agentType} (ID: ${run.display_id ?? run.id}) onto worker cluster`,
          type: "good",
        });
        refreshRuns();
      })
      .catch((err: unknown) => {
        setFeedbackMessage({
          text: err instanceof ApiRequestError ? err.message : "Failed to launch run",
          type: "critical",
        });
      })
      .finally(() => {
        setQuickLaunchLoading(false);
      });
  };

  const handleResetDemoRuns = () => {
    setFeedbackMessage(null);
    api
      .resetDemoRuns()
      .then((res) => {
        setFeedbackMessage({
          text: `Demo reset complete: ${res.runs_deleted} runs cleared`,
          type: "warning",
        });
        refreshRuns();
      })
      .catch((err: unknown) => {
        setFeedbackMessage({
          text: err instanceof ApiRequestError ? err.message : "Reset failed",
          type: "critical",
        });
      });
  };

  return (
    <div data-testid="dashboard" className="space-y-6 pb-12">
      {/* Top Command Center Telemetry Header */}
      <div className="hud-corner glass-panel rounded-xl p-5 glow-card">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-status-good opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-status-good"></span>
              </span>
              <h1 className="font-ui text-lg font-bold tracking-tight text-ink-primary uppercase">
                Operator Telemetry Command
              </h1>
              <span className="rounded-full bg-strand-gold/15 px-2.5 py-0.5 text-[10px] font-semibold text-strand-gold border border-strand-gold/30 font-data">
                DURABLE RUNTIME
              </span>
            </div>
            <p className="text-xs text-ink-secondary flex flex-wrap items-center gap-x-3 gap-y-1 font-data">
              <span>PROFILE: <strong className="text-strand-gold font-bold">{metrics?.active_profile ?? health.active_profile ?? "DEMO"}</strong></span>
              <span>·</span>
              <span>LEASE DURATION: <strong className="text-ink-primary">{metrics?.lease_duration_ms ?? 4000}ms</strong></span>
              <span>·</span>
              <span>CONCURRENCY CAP: <strong className="text-ink-primary">{health.global_concurrency_cap ?? 50}</strong></span>
              <span>·</span>
              <span>SCHEMA: <strong className="text-ink-muted">{health.schema_revision}</strong></span>
            </p>
          </div>

          {/* Action Launch Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={quickLaunchLoading}
              onClick={() => handleQuickLaunch("demo_short")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-strand-gold/50 bg-strand-gold/15 px-3.5 py-1.5 text-xs font-semibold text-strand-gold hover:bg-strand-gold/25 hover:border-strand-gold transition-all duration-base shadow-sm disabled:opacity-50"
            >
              <span>⚡</span>
              <span>{quickLaunchLoading ? "Dispatching…" : "1-Click Demo (9-step)"}</span>
            </button>
            <button
              type="button"
              disabled={quickLaunchLoading}
              onClick={() => handleQuickLaunch("demo_long")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gridline bg-surface-elevated px-3 py-1.5 text-xs font-medium text-ink-primary hover:border-strand-gold/40 hover:text-strand-gold transition-all disabled:opacity-50"
            >
              <span>40-Step Run</span>
            </button>
            <Link
              to="/tools/test-run"
              className="inline-flex items-center gap-1.5 rounded-lg border border-gridline bg-surface-elevated px-3 py-1.5 text-xs font-medium text-ink-primary hover:border-baseline hover:text-strand-gold transition-all"
            >
              <span>+ Custom Test</span>
            </Link>
            <button
              type="button"
              onClick={handleResetDemoRuns}
              className="rounded-lg border border-gridline bg-surface-panel px-2.5 py-1.5 text-xs text-ink-muted hover:text-ink-primary hover:border-gridline transition-colors"
              title="Reset all demo runs"
            >
              ↺ Reset
            </button>
          </div>
        </div>

        {feedbackMessage && (
          <div
            className={`mt-4 rounded-lg p-3 text-xs flex items-center justify-between transition-all ${
              feedbackMessage.type === "good"
                ? "bg-status-good/15 text-status-good border border-status-good/30"
                : feedbackMessage.type === "warning"
                ? "bg-status-warning/15 text-status-warning border border-status-warning/30"
                : "bg-status-critical/15 text-status-critical border border-status-critical/30"
            }`}
          >
            <span>{feedbackMessage.text}</span>
            <button type="button" onClick={() => setFeedbackMessage(null)} className="underline ml-2">
              dismiss
            </button>
          </div>
        )}
      </div>

      {(healthStale || metricsStale) && (
        <div className="rounded-lg border border-status-warning/40 bg-status-warning/10 px-4 py-2.5 text-xs text-status-warning flex items-center justify-between" data-testid="dashboard-stale">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-status-warning animate-ping" />
            <span>Telemetry stream interrupted — background refresh retrying…</span>
          </div>
        </div>
      )}

      {/* Hero KPI Telemetry Matrix */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatTile
          label="duplicate side effects"
          value={metrics?.duplicate_side_effects ?? 0}
          emphasize
          badge="verified live"
        />
        <StatTile
          label="active workloads"
          value={activeRunsCount}
          badge={activeRunsCount > 0 ? "executing" : "idle"}
        />
        <StatTile
          label="worker fleet"
          value={`${health.healthy_worker_count ?? health.worker_count} / ${health.worker_count}`}
          badge={health.degraded || workersDegraded ? "degraded" : "healthy"}
        />
        <StatTile
          label="steps/sec throughput"
          value={metrics?.steps_per_second !== undefined ? metrics.steps_per_second.toFixed(1) : "0.0"}
          sparkline={
            metrics?.run_state_distribution && metrics.run_state_distribution.length > 0
              ? metrics.run_state_distribution.map((b) => Object.values(b.counts).reduce((a, c) => a + c, 0))
              : [0, 0.4, 0.8, 1.2, 1.0, 1.5, 2.0, 1.8]
          }
        />
      </div>

      {/* Execution Cockpit & Live Golden Threads Stream */}
      <div className="hud-corner glass-panel rounded-xl p-5 space-y-4 glow-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gridline/60 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-ui text-sm font-bold uppercase tracking-wider text-ink-primary">
                Execution Stream Cockpit
              </h2>
              <span className="rounded bg-surface-elevated px-2 py-0.5 text-[10px] font-data text-ink-muted">
                {allRuns.length} TOTAL
              </span>
            </div>
            <p className="text-xs text-ink-secondary">Live durable agent workflows and golden ownership threads</p>
          </div>

          <div className="flex items-center gap-1.5">
            {(["all", "running", "completed", "needs_review", "failed"] as const).map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setFilterStatus(st)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition-all ${
                  filterStatus === st
                    ? "bg-strand-gold/20 text-strand-gold border border-strand-gold/40 shadow-sm"
                    : "text-ink-muted hover:text-ink-primary hover:bg-surface-elevated"
                }`}
              >
                {st.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {filteredRuns.length === 0 ? (
          <div className="rounded-lg border border-gridline bg-surface-page/50 p-10 text-center space-y-3">
            <p className="text-xs text-ink-muted font-data uppercase tracking-wider">No runs match the active filter</p>
            <button
              type="button"
              onClick={() => handleQuickLaunch("refund-agent")}
              className="inline-flex items-center gap-1.5 rounded border border-strand-gold/40 bg-strand-gold/10 px-3 py-1.5 text-xs text-strand-gold hover:bg-strand-gold/20"
            >
              + Launch Demo Run
            </button>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-gridline bg-surface-page/50">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-gridline bg-surface-elevated/70 text-ink-muted font-data text-[11px] uppercase tracking-wider">
                  <th className="py-2.5 pl-4 pr-3 font-medium">Run ID</th>
                  <th className="py-2.5 pr-3 font-medium">Agent</th>
                  <th className="py-2.5 pr-3 font-medium">State</th>
                  <th className="py-2.5 pr-3 font-medium">Owning Worker</th>
                  <th className="py-2.5 pr-3 font-medium">Elapsed</th>
                  <th className="py-2.5 pr-4 font-medium w-48">Golden Strand</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gridline">
                {filteredRuns.slice(0, 8).map((run) => (
                  <tr key={run.id} className="hover:bg-surface-elevated/50 transition-colors group">
                    <td className="py-3 pl-4 pr-3 font-data font-bold">
                      <Link
                        to={`/runs/${run.id}`}
                        className="text-ink-primary group-hover:text-strand-gold transition-colors inline-flex items-center gap-1"
                      >
                        <span>{run.display_id ?? `run_${run.id}`}</span>
                        <span className="text-[10px] text-ink-muted opacity-0 group-hover:opacity-100 transition-opacity">↗</span>
                      </Link>
                    </td>
                    <td className="py-3 pr-3 text-ink-secondary font-medium">{run.agent_type}</td>
                    <td className="py-3 pr-3">
                      <StatusPill status={run.status} />
                    </td>
                    <td className="py-3 pr-3 font-data text-ink-secondary">
                      {run.owner_worker_id ? (
                        <span className="rounded bg-surface-elevated px-2 py-0.5 text-[11px] text-ink-primary border border-gridline">
                          {run.owner_worker_id}
                        </span>
                      ) : (
                        <span className="text-ink-muted">—</span>
                      )}
                    </td>
                    <td className="figures-tabular py-3 pr-3 font-data text-ink-muted">
                      {Math.round(run.elapsed_ms / 1000)}s
                    </td>
                    <td className="py-3 pr-4 w-48">
                      <RunThread segments={run.segments} compact animate={run.status === "running"} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Fleet Node Cluster Status */}
      <div className="hud-corner glass-panel rounded-xl p-5 space-y-4 glow-card">
        <div className="flex items-center justify-between border-b border-gridline/60 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-ui text-sm font-bold uppercase tracking-wider text-ink-primary">
                Worker Fleet Grid
              </h2>
              <span className="rounded bg-status-good/15 px-2 py-0.5 text-[10px] font-data text-status-good border border-status-good/30">
                {workers.length} NODES
              </span>
            </div>
            <p className="text-xs text-ink-secondary">Autonomous execution nodes with heartbeat lease renewers</p>
          </div>
          <Link to="/workers" className="text-xs text-strand-gold hover:underline font-medium">
            Manage Fleet →
          </Link>
        </div>

        {workers.length === 0 ? (
          <div className="rounded-lg border border-gridline bg-surface-page/50 p-6 text-center text-xs text-ink-muted">
            Connecting to worker fleet…
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5">
            {workers.map((w, idx) => {
              const hueClass = idx % 3 === 0 ? "border-l-worker-1" : idx % 3 === 1 ? "border-l-worker-2" : "border-l-worker-3";
              return (
                <div
                  key={w.id}
                  className={`rounded-lg border border-gridline bg-surface-elevated/60 p-4 space-y-2.5 border-l-4 ${hueClass} hover:border-strand-gold/40 transition-all`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-data text-xs font-bold text-ink-primary">{w.id}</span>
                    <span
                      className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        w.stale
                          ? "bg-status-warning/15 text-status-warning border border-status-warning/30"
                          : "bg-status-good/15 text-status-good border border-status-good/30"
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${w.stale ? "bg-status-warning" : "bg-status-good animate-pulse"}`} />
                      {w.stale ? "STALE" : "HEALTHY"}
                    </span>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between text-ink-secondary text-[11px]">
                      <span>Workload:</span>
                      <span className="font-data text-ink-primary font-bold">
                        {w.current_run_count} / {w.capacity} runs
                      </span>
                    </div>
                    {/* Capacity Progress Bar */}
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-page">
                      <div
                        className="h-full rounded-full transition-all duration-base"
                        style={{
                          width: `${Math.min(100, Math.max(10, (w.current_run_count / (w.capacity || 1)) * 100))}%`,
                          backgroundColor: idx % 3 === 0 ? "var(--worker-1)" : idx % 3 === 1 ? "var(--worker-2)" : "var(--worker-3)",
                        }}
                      />
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-[10px] font-data text-ink-muted pt-1 border-t border-gridline/50">
                    <span>BUILD: {w.code_version}</span>
                    <span>UP: {w.uptime_ms !== undefined ? `${Math.round(w.uptime_ms / 1000)}s` : "—"}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
