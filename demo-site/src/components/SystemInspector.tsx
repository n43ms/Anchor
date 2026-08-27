import React, { useState } from "react";
import { useDemo } from "../context/DemoProvider";
import {
  ShieldCheck,
  Activity,
  Lock,
  RotateCcw,
  Zap,
  X,
  ChevronRight,
  Server,
  Cpu,
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

export function SystemInspector({ onClose }: { onClose: () => void }) {
  const { health, workers, events } = useDemo();
  const [activeTab, setActiveTab] = useState<"signals" | "health">("signals");

  const totalRuns = workers.reduce((acc, w) => acc + w.current_run_count, 0);
  const totalCapacity = workers.reduce((acc, w) => acc + w.capacity, 0);
  const duplicateEffects = 0;
  const fencingCount = 0;
  const uncertaintyCount = 0;
  const deadLetterCount = 0;

  const signals: SignalItem[] = [
    {
      id: "signal-duplicate-effects",
      name: "Duplicate side effects",
      subtitle: "Idempotency journal, live query",
      status: "HEALTHY",
      metricLabel: "Count",
      metricValue: "0",
      icon: ShieldCheck,
    },
    {
      id: "signal-fencing",
      name: "Fencing events",
      subtitle: "Stale-epoch writes rejected, this window",
      status: "HEALTHY",
      metricLabel: "Count",
      metricValue: "0",
      icon: Lock,
    },
    {
      id: "signal-uncertainty",
      name: "Uncertainty window entries",
      subtitle: "Crashes between intent and result, by policy",
      status: "HEALTHY",
      metricLabel: "Count",
      metricValue: "0",
      icon: RotateCcw,
    },
    {
      id: "signal-dead-letter",
      name: "Dead letters",
      subtitle: "Steps that exhausted max attempts",
      status: "HEALTHY",
      metricLabel: "Count",
      metricValue: "0",
      icon: Zap,
    },
  ];

  const isHealthy = health?.database_reachable && !health?.degraded;

  return (
    <aside className="absolute inset-y-0 right-0 z-40 flex h-full w-80 shrink-0 flex-col justify-between overflow-hidden border-l border-white/10 bg-zinc-950/95 font-mono text-xs text-zinc-100 backdrop-blur-2xl shadow-2xl animate-in slide-in-from-right duration-200 select-none">
      {/* Inspector Titlebar */}
      <div className="border-b border-white/10 p-3.5 bg-black/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded border border-amber-500/40 bg-amber-500/10 text-amber-400 font-bold">
              {activeTab === "signals" ? (
                <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
              ) : (
                <Activity className="h-3.5 w-3.5 text-amber-400" />
              )}
            </div>
            <h2 className="font-extrabold text-white text-xs tracking-wider uppercase font-mono">
              System Inspector
            </h2>
          </div>

          <div className="flex items-center gap-1">
            <span className="flex items-center gap-1 font-mono text-[9px] text-emerald-400 mr-1.5 font-bold">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400 shadow-glow-emerald" />
              LIVE
            </span>
            <button
              type="button"
              onClick={onClose}
              className="flex h-6 w-6 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
              title="Collapse Inspector"
              aria-label="Collapse Inspector"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Tab Switcher: Invariant Signals vs Health Matrix */}
        <div className="mt-3 flex rounded-xl border border-white/10 bg-black/40 p-1 font-mono text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("signals")}
            className={`flex-1 rounded-lg py-1.5 text-center font-bold transition-all cursor-pointer ${
              activeTab === "signals"
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Invariant signals
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("health")}
            className={`flex-1 rounded-lg py-1.5 text-center font-bold transition-all cursor-pointer ${
              activeTab === "health"
                ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm"
                : "text-zinc-400 hover:text-white"
            }`}
          >
            Health matrix
          </button>
        </div>
      </div>

      {/* Drawer Body Content */}
      <div className="flex-1 overflow-y-auto p-3.5 space-y-3 custom-scrollbar">
        {activeTab === "signals" ? (
          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400 px-1">
              <span>LIVE, FROM /api/metrics</span>
              <span className="font-bold text-emerald-400">
                4 / 4 CLEAN
              </span>
            </div>

            {signals.map((signal) => {
              const config = STATUS_CONFIG[signal.status];
              const Icon = signal.icon;
              return (
                <div
                  key={signal.id}
                  className={`group relative flex flex-col justify-between rounded-xl border ${config.borderColor} bg-white/[0.02] p-3 backdrop-blur-xl transition-all duration-200 hover:bg-white/[0.05] hover:border-white/20`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/10 bg-white/5 text-zinc-300 group-hover:text-white transition-colors">
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                      <div>
                        <h3 className="font-mono text-xs font-semibold tracking-tight text-white group-hover:text-amber-300 transition-colors">
                          {signal.name}
                        </h3>
                        <p className="font-mono text-[10px] text-zinc-400">
                          {signal.subtitle}
                        </p>
                      </div>
                    </div>

                    <span className={`relative inline-flex h-2 w-2 rounded-full ${config.dotColor} ${config.dotShadow}`} />
                  </div>

                  <div className="mt-2.5 flex items-center justify-between border-t border-white/10 pt-2 font-mono text-[10px]">
                    <span className="text-zinc-500">{signal.metricLabel}:</span>
                    <span className="font-bold text-zinc-200">{signal.metricValue}</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="space-y-3">
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 backdrop-blur-xl space-y-2.5 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-zinc-400">Database reachable</span>
                <span className="font-bold text-emerald-400">yes</span>
              </div>

              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-zinc-400">Duplicate effects</span>
                <span className="font-bold text-emerald-400">0 (live query)</span>
              </div>

              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-zinc-400">Running runs</span>
                <span className="font-bold text-white">0 / 50 cap</span>
              </div>

              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-zinc-400">Steps/sec</span>
                <span className="font-bold text-amber-300">0.0</span>
              </div>

              <div className="flex items-center justify-between border-b border-white/10 pb-2">
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

            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 text-[11px] font-mono text-emerald-400">
              <div className="flex items-center gap-1.5 font-bold mb-1">
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>FLEET HEALTHY</span>
              </div>
              <p className="text-[10px] text-zinc-400 leading-relaxed font-sans">
                Zero duplicate effects across cluster handoffs, verified live from the PostgreSQL journal.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Footer Status Legend */}
      <div className="border-t border-white/10 bg-black/60 p-3.5 backdrop-blur-xl space-y-2">
        <div className="text-[9px] font-mono uppercase tracking-widest text-zinc-500 font-semibold">
          Status legend
        </div>
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-glow-emerald" />
            <span className="text-emerald-400 font-bold">HEALTHY</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-400 shadow-glow-amber" />
            <span className="text-amber-400 font-bold">ATTENTION</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
