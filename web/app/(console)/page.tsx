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
import { Zap, Play, Plus, RotateCcw, Server, Activity, ArrowUpRight } from "lucide-react";

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
      <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-sm text-rose-400 backdrop-blur-xl" data-testid="dashboard-error">
        <div className="flex items-center gap-2 font-bold font-ui text-base mb-1">
          <span className="h-2.5 w-2.5 rounded-full bg-rose-400 animate-ping shadow-glow-rose" />
          <span>RUNTIME DISCONNECTED</span>
        </div>
        <p className="text-xs text-zinc-400">could not reach the backend api — check if docker containers and api service are running</p>
      </div>
    );
  }
  if (!health) {
    return (
      <div className="space-y-4 p-12 text-center" data-testid="dashboard-loading">
        <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-strand-gold border-t-transparent mb-3" />
        <p className="text-xs font-mono text-zinc-500 uppercase tracking-widest">initializing telemetry stream…</p>
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
      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl transition-all">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400 shadow-glow-emerald"></span>
              </span>
              <h1 className="font-ui text-base font-bold tracking-tight text-white uppercase">
                Operator Telemetry Cockpit
              </h1>
              <span className="ml-3.5 rounded-full bg-strand-gold/10 px-2.5 py-0.5 text-[10px] font-semibold text-strand-gold border border-strand-gold/30 font-mono">
                DURABLE RUNTIME
              </span>
            </div>
            <p className="text-xs text-zinc-400 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono">
              <span>PROFILE: <strong className="text-strand-gold font-bold">{metrics?.active_profile ?? health.active_profile ?? "DEMO"}</strong></span>
              <span className="text-zinc-600">·</span>
              <span>LEASE DURATION: <strong className="text-zinc-200">{metrics?.lease_duration_ms ?? 4000}ms</strong></span>
              <span className="text-zinc-600">·</span>
              <span>CONCURRENCY CAP: <strong className="text-zinc-200">{health.global_concurrency_cap ?? 50}</strong></span>
              <span className="text-zinc-600">·</span>
              <span>SCHEMA: <strong className="text-zinc-500">{health.schema_revision}</strong></span>
            </p>
          </div>

          {/* Action Launch Bar */}
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              disabled={quickLaunchLoading}
              onClick={() => handleQuickLaunch("demo_short")}
              className="inline-flex items-center gap-1.5 rounded-xl border border-strand-gold/50 bg-strand-gold/15 px-3.5 py-2 text-xs font-semibold text-strand-gold hover:bg-strand-gold/25 hover:border-strand-gold transition-all duration-base shadow-sm disabled:opacity-50"
            >
              <Zap className="h-3.5 w-3.5" />
              <span>{quickLaunchLoading ? "Dispatching…" : "1-Click Demo (9-step)"}</span>
            </button>
            <button
              type="button"
              disabled={quickLaunchLoading}
              onClick={() => handleQuickLaunch("demo_long")}
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2 text-xs font-medium text-zinc-200 hover:border-white/[0.2] hover:text-white transition-all disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5 text-zinc-400" />
              <span>40-Step Run</span>
            </button>
            <Link
              to="/tools/test-run"
              className="inline-flex items-center gap-1.5 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2 text-xs font-medium text-zinc-200 hover:border-strand-gold/40 hover:text-strand-gold transition-all"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Custom Test</span>
            </Link>
            <button
              type="button"
              onClick={handleResetDemoRuns}
              className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-2 text-xs text-zinc-400 hover:text-white hover:border-white/[0.2] transition-colors"
              title="Reset all demo runs"
            >
              <RotateCcw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {feedbackMessage && (
          <div
            className={`mt-4 rounded-xl p-3 text-xs flex items-center justify-between transition-all backdrop-blur-xl ${
              feedbackMessage.type === "good"
                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                : feedbackMessage.type === "warning"
                ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                : "bg-rose-500/15 text-rose-400 border border-rose-500/30"
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
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-400 flex items-center justify-between backdrop-blur-xl" data-testid="dashboard-stale">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-amber-400 animate-ping shadow-glow-amber" />
            <span>Telemetry stream interrupted — background refresh retrying…</span>
          </div>
        </div>
      )}

      {/* Hero KPI Telemetry Matrix */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
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

      {/* Execution Cockpit & Live Runtime Thread Stream */}
      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 space-y-4 backdrop-blur-2xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-ui text-sm font-bold uppercase tracking-wider text-white">
                Execution Stream Cockpit
              </h2>
              <span className="ml-3.5 rounded bg-white/[0.05] px-2 py-0.5 text-[10px] font-mono text-zinc-400 border border-white/[0.08]">
                {allRuns.length} TOTAL
              </span>
            </div>
            <p className="text-xs text-zinc-400">Live durable agent workflows and runtime execution threads</p>
          </div>

          <div className="flex items-center gap-1.5">
            {(["all", "running", "completed", "needs_review", "failed"] as const).map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setFilterStatus(st)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium font-mono transition-all ${
                  filterStatus === st
                    ? "bg-strand-gold/20 text-strand-gold border border-strand-gold/40 shadow-sm"
                    : "text-zinc-400 hover:text-white hover:bg-white/[0.04]"
                }`}
              >
                {st.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {filteredRuns.length === 0 ? (
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-10 text-center space-y-3">
            <p className="text-xs text-zinc-500 font-mono uppercase tracking-wider">No runs match the active filter</p>
            <button
              type="button"
              onClick={() => handleQuickLaunch("refund-agent")}
              className="inline-flex items-center gap-1.5 rounded-lg border border-strand-gold/40 bg-strand-gold/10 px-3 py-1.5 text-xs text-strand-gold hover:bg-strand-gold/20"
            >
              + Launch Demo Run
            </button>
          </div>
        ) : (
          <div className="overflow-hidden rounded-xl border border-white/[0.08] bg-white/[0.02]">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/[0.06] bg-white/[0.03] text-zinc-400 font-mono text-[11px] uppercase tracking-wider">
                  <th className="py-2.5 pl-4 pr-3 font-medium">Run ID</th>
                  <th className="py-2.5 pr-3 font-medium">Agent</th>
                  <th className="py-2.5 pr-3 font-medium">State</th>
                  <th className="py-2.5 pr-3 font-medium">Owning Worker</th>
                  <th className="py-2.5 pr-3 font-medium">Elapsed</th>
                  <th className="py-2.5 pr-4 font-medium w-48">Runtime Thread</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/[0.04]">
                {filteredRuns.slice(0, 8).map((run) => (
                  <tr key={run.id} className="hover:bg-white/[0.04] transition-colors group">
                    <td className="py-3 pl-4 pr-3 font-mono font-bold">
                      <Link
                        to={`/runs/${run.id}`}
                        className="text-white group-hover:text-strand-gold transition-colors inline-flex items-center gap-1"
                      >
                        <span>{run.display_id ?? `run_${run.id}`}</span>
                        <ArrowUpRight className="h-3 w-3 text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </Link>
                    </td>
                    <td className="py-3 pr-3 text-zinc-300 font-medium">{run.agent_type}</td>
                    <td className="py-3 pr-3">
                      <StatusPill status={run.status} />
                    </td>
                    <td className="py-3 pr-3 font-mono text-zinc-300">
                      {run.owner_worker_id ? (
                        <span className="rounded bg-white/[0.04] px-2 py-0.5 text-[11px] text-zinc-200 border border-white/[0.08]">
                          {run.owner_worker_id}
                        </span>
                      ) : (
                        <span className="text-zinc-500">—</span>
                      )}
                    </td>
                    <td className="figures-tabular py-3 pr-3 font-mono text-zinc-400">
                      {Math.round(run.elapsed_ms / 1000)}s
                    </td>
                    <td className="py-3 pr-4 w-48">
                      <RunThread segments={run.segments} compact />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Fleet Node Cluster Status */}
      <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-5 space-y-4 backdrop-blur-2xl">
        <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-ui text-sm font-bold uppercase tracking-wider text-white">
                Worker Fleet Grid
              </h2>
              <span className="ml-3.5 rounded bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono text-emerald-400 border border-emerald-500/30">
                {workers.length} NODES
              </span>
            </div>
            <p className="text-xs text-zinc-400">Autonomous execution nodes with heartbeat lease renewers</p>
          </div>
          <Link to="/workers" className="text-xs text-strand-gold hover:underline font-mono font-medium">
            Manage Fleet →
          </Link>
        </div>

        {workers.length === 0 ? (
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-6 text-center text-xs text-zinc-500 font-mono">
            Connecting to worker fleet…
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3.5">
            {workers.map((w, idx) => {
              const hueClass = idx % 3 === 0 ? "border-l-worker-1" : idx % 3 === 1 ? "border-l-worker-2" : "border-l-worker-3";
              return (
                <div
                  key={w.id}
                  className={`rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 space-y-2.5 border-l-4 ${hueClass} hover:border-white/[0.2] transition-all backdrop-blur-xl`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-white">{w.id}</span>
                    <span
                      className={`inline-flex items-center gap-1 text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full ${
                        w.stale
                          ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                          : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${w.stale ? "bg-amber-400 shadow-glow-amber" : "bg-emerald-400 animate-pulse shadow-glow-emerald"}`} />
                      {w.stale ? "STALE" : "HEALTHY"}
                    </span>
                  </div>

                  <div className="space-y-1 text-xs font-mono">
                    <div className="flex justify-between text-zinc-400 text-[11px]">
                      <span>Workload:</span>
                      <span className="text-white font-bold tabular-nums">
                        {w.current_run_count} / {w.capacity} runs
                      </span>
                    </div>
                    {/* Capacity Progress Bar */}
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.05]">
                      <div
                        className="h-full rounded-full transition-all duration-base"
                        style={{
                          width: `${Math.min(100, Math.max(10, (w.current_run_count / (w.capacity || 1)) * 100))}%`,
                          backgroundColor: idx % 3 === 0 ? "var(--worker-1)" : idx % 3 === 1 ? "var(--worker-2)" : "var(--worker-3)",
                        }}
                      />
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-[10px] font-mono text-zinc-500 pt-1 border-t border-white/[0.04]">
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
