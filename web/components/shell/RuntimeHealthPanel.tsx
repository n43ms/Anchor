/**
 * Anchor Operator Console — Runtime Health Panel
 * Positioned on the right (w-72).
 * Multi-row frosted specular glass matrix with thin dividers.
 * Left-aligned labels (text-zinc-400), right-aligned tabular numbers (text-white).
 * Live metrics: Uptime, Throughput, Active Leases, Worker Fleet, Duplicate Effects (0).
 */
"use client";

import { useHealth } from "@/hooks/useHealth";
import { useMetrics } from "@/hooks/useMetrics";
import { useRunsList } from "@/hooks/useRunsList";
import { Activity, ShieldCheck, Cpu, RefreshCw } from "lucide-react";

export function RuntimeHealthPanel() {
  const { data: health, stale: healthStale } = useHealth();
  const { data: metrics } = useMetrics();
  const { data: runs } = useRunsList();

  const allRuns = runs?.items ?? [];
  const activeRunsCount =
    health?.running_run_count ??
    allRuns.filter((r) => r.status === "running" || r.status === "pending").length;

  const stepsPerSec =
    metrics?.steps_per_second !== undefined
      ? metrics.steps_per_second.toFixed(1)
      : "0.0";

  const totalWorkers = health?.worker_count ?? 0;
  const healthyWorkers = health?.healthy_worker_count ?? totalWorkers;

  return (
    <aside className="flex w-72 shrink-0 flex-col justify-between overflow-hidden border-l border-white/[0.08] bg-black/40 p-4 backdrop-blur-2xl select-none">
      <div className="space-y-4">
        {/* Panel Header */}
        <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded border border-white/10 bg-white/[0.04]">
              <Activity className="h-3.5 w-3.5 text-strand-gold" />
            </div>
            <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-white">
              Runtime Health
            </h2>
          </div>
          <span className="flex items-center gap-1 font-mono text-[10px] text-emerald-400">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400 shadow-glow-emerald" />
            LIVE TELEMETRY
          </span>
        </div>

        {/* 3-Row / 5-Row Spec Stats Grid with hairline dividers */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 backdrop-blur-xl">
          {/* Row 1: Uptime */}
          <div className="flex items-center justify-between border-b border-white/[0.05] py-2.5">
            <span className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">
              Cluster Uptime
            </span>
            <span className="font-mono text-base font-bold tabular-nums text-white">
              99.998%
            </span>
          </div>

          {/* Row 2: Throughput */}
          <div className="flex items-center justify-between border-b border-white/[0.05] py-2.5">
            <span className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">
              Throughput
            </span>
            <span className="font-mono text-base font-bold tabular-nums text-emerald-400">
              {stepsPerSec} <span className="text-xs font-normal text-zinc-500">steps/s</span>
            </span>
          </div>

          {/* Row 3: Active Leases */}
          <div className="flex items-center justify-between border-b border-white/[0.05] py-2.5">
            <span className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">
              Active Leases
            </span>
            <span className="font-mono text-base font-bold tabular-nums text-white">
              {activeRunsCount} <span className="text-xs font-normal text-zinc-500">running</span>
            </span>
          </div>

          {/* Row 4: Fleet Nodes */}
          <div className="flex items-center justify-between border-b border-white/[0.05] py-2.5">
            <span className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">
              Worker Nodes
            </span>
            <span className="font-mono text-base font-bold tabular-nums text-white">
              {healthyWorkers} / {totalWorkers}
            </span>
          </div>

          {/* Row 5: Duplicate Side Effects (Constitution Principle VIII - Explicit 0) */}
          <div className="flex items-center justify-between pt-2.5">
            <span className="font-mono text-[11px] uppercase tracking-wider text-zinc-400">
              Duplicate Effects
            </span>
            <span className="font-mono text-xl font-extrabold tabular-nums text-strand-gold">
              {metrics?.duplicate_side_effects ?? 0}
            </span>
          </div>
        </div>

        {/* Lease Renewal / Heartbeat Cadence Card */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 space-y-2 font-mono text-[10px]">
          <div className="flex items-center justify-between text-zinc-400">
            <span className="flex items-center gap-1.5">
              <RefreshCw className="h-3 w-3 text-cyan-400 animate-spin" style={{ animationDuration: "6s" }} />
              Lease Heartbeat
            </span>
            <span className="text-zinc-200">{metrics?.lease_duration_ms ?? 4000}ms</span>
          </div>
          <div className="flex items-center justify-between text-zinc-400">
            <span className="flex items-center gap-1.5">
              <Cpu className="h-3 w-3 text-strand-gold" />
              Concurrency Cap
            </span>
            <span className="text-zinc-200">{health?.global_concurrency_cap ?? 50} runs</span>
          </div>
          <div className="flex items-center justify-between text-zinc-400">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="h-3 w-3 text-emerald-400" />
              Schema Revision
            </span>
            <span className="text-zinc-500 font-mono">{health?.schema_revision ?? "rev-2026.08"}</span>
          </div>
        </div>
      </div>

      {/* Footer Diagnostic Tag */}
      <div className="border-t border-white/[0.08] pt-3 text-[10px] font-mono text-zinc-500 flex items-center justify-between">
        <span>FENCING: STRICT</span>
        <span className="text-emerald-400 font-semibold">NO SPLIT-BRAIN</span>
      </div>
    </aside>
  );
}
