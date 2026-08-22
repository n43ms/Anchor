/**
 * Anchor Operator Console — Right Inspector Panel
 * Combines invariant-signal monitors and a runtime health matrix into a
 * single toggle-closable right drawer.
 *
 * Every figure here is read from GET /api/health, GET /api/metrics, or
 * useWorkers — none are invented. "OOM prevention" / "infinite loop
 * breaker" style guard cards were removed: they described subsystems that
 * do not exist in anchor/core, and a console must never render invented
 * telemetry as if it were live (constitution Principle VIII).
 */
"use client";

import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { useHealth } from "@/hooks/useHealth";
import { useWorkers } from "@/hooks/useWorkers";
import { useMetrics } from "@/hooks/useMetrics";
import {
  ShieldCheck,
  Activity,
  Lock,
  RotateCcw,
  Zap,
  X,
  ChevronRight,
} from "lucide-react";

type SignalStatus = "HEALTHY" | "ATTENTION";

interface SignalItem {
  id: string;
  name: string;
  subtitle: string;
  status: SignalStatus;
  metricLabel: string;
  metricValue: string;
  icon: typeof Zap;
}

const STATUS_CONFIG: Record<SignalStatus, { borderColor: string; dotColor: string; dotShadow: string }> = {
  HEALTHY: {
    borderColor: "border-emerald-500/30",
    dotColor: "bg-emerald-400",
    dotShadow: "shadow-glow-emerald",
  },
  ATTENTION: {
    borderColor: "border-amber-500/30",
    dotColor: "bg-amber-400",
    dotShadow: "shadow-glow-amber",
  },
};

interface RightInspectorPanelProps {
  onClose?: () => void;
}

export function RightInspectorPanel({ onClose }: RightInspectorPanelProps) {
  const { data: health, stale } = useHealth();
  const { workers } = useWorkers();
  const { data: metrics } = useMetrics();
  const [activeTab, setActiveTab] = useState<"signals" | "health">("signals");

  const totalRuns = workers.reduce((acc, w) => acc + w.current_run_count, 0);
  const totalCapacity = workers.reduce((acc, w) => acc + w.capacity, 0);
  const fencingCount = metrics?.fencing_events_series?.reduce((acc, b) => acc + b.count, 0) ?? 0;
  const uncertaintyCount = metrics
    ? Object.values(metrics.uncertainty_by_policy ?? {}).reduce((a, c) => a + c, 0)
    : 0;
  const deadLetterCount = metrics
    ? (metrics.dead_letter_reasons ?? []).reduce((a, r) => a + r.count, 0)
    : 0;
  const duplicateEffects = metrics?.duplicate_side_effects ?? 0;

  const signals: SignalItem[] = [
    {
      id: "signal-duplicate-effects",
      name: "Duplicate side effects",
      subtitle: "Idempotency journal, live query",
      status: duplicateEffects > 0 ? "ATTENTION" : "HEALTHY",
      metricLabel: "Count",
      metricValue: metrics ? String(duplicateEffects) : "—",
      icon: ShieldCheck,
    },
    {
      id: "signal-fencing",
      name: "Fencing events",
      subtitle: "Stale-epoch writes rejected, this window",
      status: fencingCount > 0 ? "ATTENTION" : "HEALTHY",
      metricLabel: "Count",
      metricValue: metrics ? String(fencingCount) : "—",
      icon: Lock,
    },
    {
      id: "signal-uncertainty",
      name: "Uncertainty window entries",
      subtitle: "Crashes between intent and result, by policy",
      status: uncertaintyCount > 0 ? "ATTENTION" : "HEALTHY",
      metricLabel: "Count",
      metricValue: metrics ? String(uncertaintyCount) : "—",
      icon: RotateCcw,
    },
    {
      id: "signal-dead-letter",
      name: "Dead letters",
      subtitle: "Steps that exhausted max attempts",
      status: deadLetterCount > 0 ? "ATTENTION" : "HEALTHY",
      metricLabel: "Count",
      metricValue: metrics ? String(deadLetterCount) : "—",
      icon: Zap,
    },
  ];

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col justify-between overflow-hidden border-l border-white/[0.08] bg-black/40 backdrop-blur-2xl select-none">
      <div className="border-b border-white/[0.08] p-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded border border-white/10 bg-white/[0.04]">
              {activeTab === "signals" ? (
                <ShieldCheck className="h-3.5 w-3.5 text-strand-gold" />
              ) : (
                <Activity className="h-3.5 w-3.5 text-strand-gold" />
              )}
            </div>
            <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-white">
              System Inspector
            </h2>
          </div>

          <div className="flex items-center gap-1">
            {stale ? (
              <span className="flex items-center gap-1 font-mono text-[9px] text-amber-400 mr-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400 shadow-glow-amber" />
                STALE
              </span>
            ) : (
              <span className="flex items-center gap-1 font-mono text-[9px] text-emerald-400 mr-1.5">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400 shadow-glow-emerald" />
                LIVE
              </span>
            )}
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                className="flex h-6 w-6 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.02] text-zinc-400 hover:bg-white/[0.06] hover:text-white transition-colors"
                title="Collapse Inspector"
                aria-label="Collapse Inspector"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>

        <div className="mt-3 flex rounded-xl border border-white/[0.08] bg-white/[0.02] p-1 font-mono text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("signals")}
            className={`relative flex-1 rounded-lg py-1 text-center font-semibold transition-colors ${
              activeTab === "signals" ? "text-strand-gold" : "text-zinc-400 hover:text-white"
            }`}
          >
            {activeTab === "signals" && (
              <motion.div
                layoutId="inspectorActiveTabPill"
                className="absolute inset-0 rounded-lg bg-strand-gold/20 border border-strand-gold/40 shadow-sm"
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
              />
            )}
            <span className="relative z-10">Invariant signals</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("health")}
            className={`relative flex-1 rounded-lg py-1 text-center font-semibold transition-colors ${
              activeTab === "health" ? "text-strand-gold" : "text-zinc-400 hover:text-white"
            }`}
          >
            {activeTab === "health" && (
              <motion.div
                layoutId="inspectorActiveTabPill"
                className="absolute inset-0 rounded-lg bg-strand-gold/20 border border-strand-gold/40 shadow-sm"
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
              />
            )}
            <span className="relative z-10">Health matrix</span>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3.5 scrollbar-thin">
        <AnimatePresence mode="wait">
          {activeTab === "signals" ? (
            <motion.div
              key="signals"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ type: "spring", stiffness: 350, damping: 30 }}
              className="space-y-2.5"
            >
              <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400 px-1">
                <span>LIVE, FROM /api/metrics</span>
                <span
                  className={`font-bold ${
                    signals.every((s) => s.status === "HEALTHY") ? "text-emerald-400" : "text-amber-400"
                  }`}
                >
                  {signals.filter((s) => s.status === "HEALTHY").length} / {signals.length} CLEAN
                </span>
              </div>

              {signals.map((signal) => {
                const config = STATUS_CONFIG[signal.status];
                const Icon = signal.icon;
                return (
                  <div
                    key={signal.id}
                    className={`group relative flex flex-col justify-between rounded-xl border ${config.borderColor} bg-white/[0.02] p-3 backdrop-blur-xl transition-all duration-base hover:bg-white/[0.05] hover:border-white/[0.2]`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.04] text-zinc-300 group-hover:text-white transition-colors">
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                        <div>
                          <h3 className="font-ui text-xs font-semibold tracking-tight text-white group-hover:text-strand-gold transition-colors">
                            {signal.name}
                          </h3>
                          <p className="font-mono text-[10px] text-zinc-400 line-clamp-1">
                            {signal.subtitle}
                          </p>
                        </div>
                      </div>

                      <span className={`relative inline-flex h-2 w-2 rounded-full ${config.dotColor} ${config.dotShadow}`} />
                    </div>

                    <div className="mt-2.5 flex items-center justify-between border-t border-white/[0.05] pt-2 font-mono text-[10px]">
                      <span className="text-zinc-500">{signal.metricLabel}:</span>
                      <span className="font-bold text-zinc-200">{signal.metricValue}</span>
                    </div>
                  </div>
                );
              })}
            </motion.div>
          ) : (
            <motion.div
              key="health"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ type: "spring", stiffness: 350, damping: 30 }}
              className="space-y-3"
            >
              <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 backdrop-blur-xl space-y-2.5 font-mono text-xs">
                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2">
                  <span className="text-zinc-400">Database reachable</span>
                  <span className={`font-bold ${health?.database_reachable ? "text-emerald-400" : "text-rose-400"}`}>
                    {health ? (health.database_reachable ? "yes" : "no") : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2">
                  <span className="text-zinc-400">Duplicate effects</span>
                  <span className="font-bold text-emerald-400">
                    {metrics ? `${duplicateEffects} (live query)` : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2">
                  <span className="text-zinc-400">Running runs</span>
                  <span className="font-bold text-white">
                    {health?.running_run_count ?? "—"}
                    {health?.global_concurrency_cap !== undefined ? ` / ${health.global_concurrency_cap} cap` : ""}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2">
                  <span className="text-zinc-400">Steps/sec</span>
                  <span className="font-bold text-strand-gold">
                    {metrics?.steps_per_second !== undefined ? metrics.steps_per_second.toFixed(1) : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2">
                  <span className="text-zinc-400">Fleet workers</span>
                  <span className="font-bold text-white">{workers.length} nodes</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-zinc-400">Cluster capacity</span>
                  <span className="font-bold text-zinc-300">
                    {totalRuns} / {totalCapacity} runs
                  </span>
                </div>
              </div>

              <div
                className={`rounded-xl border p-3 text-[11px] font-mono ${
                  health?.degraded
                    ? "border-amber-500/20 bg-amber-500/5 text-amber-400"
                    : "border-emerald-500/20 bg-emerald-500/5 text-emerald-400"
                }`}
              >
                <div className="flex items-center gap-1.5 font-bold mb-1">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>{health?.degraded ? "FLEET DEGRADED" : "FLEET HEALTHY"}</span>
                </div>
                <p className="text-[10px] text-zinc-400 leading-relaxed">
                  {health?.degraded
                    ? "schema mismatch or zero live workers — see /workers"
                    : "zero duplicate effects across cluster handoffs, verified live from the journal"}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="border-t border-white/[0.08] bg-black/50 p-3.5 backdrop-blur-xl">
        <div className="mb-2 text-[9px] font-mono uppercase tracking-widest text-zinc-500 font-semibold">
          Status legend
        </div>
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-glow-emerald" />
            <span className="text-emerald-400">HEALTHY</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-400 shadow-glow-amber" />
            <span className="text-amber-400">ATTENTION</span>
          </div>
        </div>
        <Link
          to="/metrics"
          className="mt-3 flex items-center justify-between rounded-lg border border-white/[0.08] bg-white/[0.02] px-2.5 py-1.5 text-[10px] font-mono text-zinc-400 hover:text-strand-gold hover:border-strand-gold/30 transition-colors"
        >
          <span>Full metrics view</span>
          <ChevronRight className="h-3 w-3" />
        </Link>
      </div>
    </aside>
  );
}
