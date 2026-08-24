/**
 * anchor-spec.md §13.3 — one card per worker: id, uptime, current runs,
 * steps executed, last heartbeat age, code version, and a kill control.
 * Killing a worker from the interface is a first-class feature.
 */
"use client";

import { useState } from "react";
import { useWorkers } from "@/hooks/useWorkers";
import { api, ApiRequestError } from "@/lib/api";
import { Server, AlertTriangle, Skull, Shield } from "lucide-react";

export default function FleetPage() {
  const { workers, stale, degraded } = useWorkers();
  const [errors, setErrors] = useState<Record<string, string>>({});

  const kill = (id: string) => {
    setErrors((prev) => ({ ...prev, [id]: "" }));
    api.killWorker(id, false).catch((err: unknown) => {
      setErrors((prev) => ({ ...prev, [id]: err instanceof ApiRequestError ? err.message : "kill failed" }));
    });
  };

  return (
    <div data-testid="fleet-page" className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Worker Fleet Cluster</h1>
            <span className="ml-3.5 rounded-full bg-emerald-500/10 px-2.5 py-0.5 font-mono text-[10px] text-emerald-400 border border-emerald-500/30 font-semibold">
              {workers.length} NODES
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono">Durable worker nodes with lease renewers and crash recovery</p>
        </div>
      </div>

      {stale && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3.5 text-xs font-mono text-amber-400 flex items-center gap-2 backdrop-blur-xl">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>stale — showing last known fleet state</span>
        </div>
      )}

      {degraded && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs font-mono text-rose-400 flex items-center gap-2 backdrop-blur-xl">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>fleet is below its expected complement</span>
        </div>
      )}

      {workers.length === 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-12 text-center text-sm font-mono text-zinc-500 backdrop-blur-2xl">
          no workers registered
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {workers.map((w, idx) => {
          const hueClass = idx % 3 === 0 ? "border-l-worker-1" : idx % 3 === 1 ? "border-l-worker-2" : "border-l-worker-3";
          return (
            <div
              key={w.id}
              className={`rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl border-l-4 ${hueClass} space-y-4 hover:border-white/[0.2] transition-all`}
              data-testid="worker-card"
            >
              <div className="flex items-center justify-between border-b border-white/[0.06] pb-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.04]">
                    <Server className="h-3.5 w-3.5 text-zinc-300" />
                  </div>
                  <span className="font-mono text-xs font-bold text-white">{w.id}</span>
                </div>
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

              <dl className="space-y-2 text-xs font-mono">
                <Row label="uptime" value={w.uptime_ms !== undefined ? `${Math.round(w.uptime_ms / 1000)}s` : "—"} />
                <Row label="current runs" value={`${w.current_run_count}/${w.capacity}`} />
                <Row label="steps executed" value={w.steps_executed ?? "—"} />
                <Row label="heartbeat age" value={w.heartbeat_age_ms !== undefined ? `${w.heartbeat_age_ms}ms` : "—"} />
                <Row label="code version" value={w.code_version} />
              </dl>

              {errors[w.id] && (
                <p className="rounded-lg bg-rose-500/10 border border-rose-500/30 p-2 text-xs font-mono text-rose-400">
                  {errors[w.id]}
                </p>
              )}

              <div className="pt-2 border-t border-white/[0.04]">
                <button
                  type="button"
                  onClick={() => kill(w.id)}
                  className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-rose-500/15 border border-rose-500/30 px-3.5 py-2 text-xs font-mono font-bold text-rose-400 hover:bg-rose-500/25 transition-all shadow-sm uppercase tracking-wider"
                  title="Sends SIGKILL process termination signal to worker node"
                >
                  <Skull className="h-3.5 w-3.5" />
                  <span>Hard Kill (SIGKILL)</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between items-center text-zinc-400 border-b border-white/[0.02] pb-1">
      <dt className="uppercase text-[10px] tracking-wider">{label}</dt>
      <dd className="figures-tabular text-white font-bold">{value}</dd>
    </div>
  );
}
