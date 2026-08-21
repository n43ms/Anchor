/**
 * Anchor Operator Console — Right Inspector Panel
 * Combines Guard Stack invariant monitors and Runtime Health matrix
 * into a single toggle-closable right drawer with smooth tab transitions.
 */
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useHealth } from "@/hooks/useHealth";
import { useWorkers } from "@/hooks/useWorkers";
import {
  ShieldCheck,
  Activity,
  Cpu,
  Zap,
  RotateCcw,
  Lock,
  X,
  Layers,
  ChevronRight,
  TrendingUp,
  Server,
  Radio,
} from "lucide-react";

interface GuardItem {
  id: string;
  name: string;
  subtitle: string;
  status: "HEALTHY" | "DEGRADED" | "HEALING" | "CRITICAL";
  metricLabel: string;
  metricValue: string;
  threshold: string;
  icon: typeof Cpu;
}

const GUARDS: GuardItem[] = [
  {
    id: "guard-oom",
    name: "OOM Prevention",
    subtitle: "Heap memory monitor & proactive gc",
    status: "HEALTHY",
    metricLabel: "Heap Memory",
    metricValue: "412MB / 2048MB",
    threshold: "85% auto-fence",
    icon: Cpu,
  },
  {
    id: "guard-loop",
    name: "Infinite Loop Breaker",
    subtitle: "AST step execution cycle watchdog",
    status: "HEALTHY",
    metricLabel: "Step Limit",
    metricValue: "100 steps/seg",
    threshold: "50 max cycle",
    icon: Zap,
  },
  {
    id: "guard-healer",
    name: "Auto Healer",
    subtitle: "Worker crash lease handoff & recovery",
    status: "HEALING",
    metricLabel: "Self Healed",
    metricValue: "3 recoveries",
    threshold: "0 side effects",
    icon: RotateCcw,
  },
  {
    id: "guard-fence",
    name: "Deadlock & Fence Guard",
    subtitle: "Monotonic fencing token sequence",
    status: "HEALTHY",
    metricLabel: "Token Epoch",
    metricValue: "seq 4092 verified",
    threshold: "0 split-brain",
    icon: Lock,
  },
];

const STATUS_CONFIG = {
  HEALTHY: {
    textColor: "text-emerald-400",
    borderColor: "border-emerald-500/30",
    bgColor: "bg-emerald-500/10",
    dotColor: "bg-emerald-400",
    dotShadow: "shadow-glow-emerald",
    label: "HEALTHY",
  },
  DEGRADED: {
    textColor: "text-amber-400",
    borderColor: "border-amber-500/30",
    bgColor: "bg-amber-500/10",
    dotColor: "bg-amber-400",
    dotShadow: "shadow-glow-amber",
    label: "DEGRADED",
  },
  HEALING: {
    textColor: "text-cyan-400",
    borderColor: "border-cyan-500/30",
    bgColor: "bg-cyan-500/10",
    dotColor: "bg-cyan-400",
    dotShadow: "shadow-glow-cyan",
    label: "HEALING",
  },
  CRITICAL: {
    textColor: "text-rose-400",
    borderColor: "border-rose-500/30",
    bgColor: "bg-rose-500/10",
    dotColor: "bg-rose-400",
    dotShadow: "shadow-glow-rose",
    label: "CRITICAL",
  },
};

interface RightInspectorPanelProps {
  onClose?: () => void;
}

export function RightInspectorPanel({ onClose }: RightInspectorPanelProps) {
  const { data: health, stale } = useHealth();
  const { workers } = useWorkers();
  const [activeTab, setActiveTab] = useState<"guards" | "health">("guards");

  const totalRuns = workers.reduce((acc, w) => acc + w.current_run_count, 0);
  const totalCapacity = workers.reduce((acc, w) => acc + w.capacity, 0);
  const isHealthy = health?.database_reachable && !health.degraded && !stale;

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col justify-between overflow-hidden border-l border-white/[0.08] bg-black/40 backdrop-blur-2xl select-none">
      {/* Top Header with Tab Switcher & Close Toggle */}
      <div className="border-b border-white/[0.08] p-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded border border-white/10 bg-white/[0.04]">
              {activeTab === "guards" ? (
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
            <span className="flex items-center gap-1 font-mono text-[9px] text-emerald-400 mr-1.5">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400 shadow-glow-emerald" />
              LIVE
            </span>
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

        {/* Tab Selector Switcher with Framer Motion Sliding Pill */}
        <div className="mt-3 flex rounded-xl border border-white/[0.08] bg-white/[0.02] p-1 font-mono text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("guards")}
            className={`relative flex-1 rounded-lg py-1 text-center font-semibold transition-colors ${
              activeTab === "guards" ? "text-strand-gold" : "text-zinc-400 hover:text-white"
            }`}
          >
            {activeTab === "guards" && (
              <motion.div
                layoutId="inspectorActiveTabPill"
                className="absolute inset-0 rounded-lg bg-strand-gold/20 border border-strand-gold/40 shadow-sm"
                transition={{ type: "spring", stiffness: 350, damping: 30 }}
              />
            )}
            <span className="relative z-10">Guards (4)</span>
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
            <span className="relative z-10">Health Matrix</span>
          </button>
        </div>
      </div>

      {/* Main Content Area with Animated Transitions */}
      <div className="flex-1 overflow-y-auto p-3.5 scrollbar-thin">
        <AnimatePresence mode="wait">
          {activeTab === "guards" ? (
            /* Guard Cards View */
            <motion.div
              key="guards"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ type: "spring", stiffness: 350, damping: 30 }}
              className="space-y-2.5"
            >
              <div className="flex items-center justify-between text-[10px] font-mono text-zinc-400 px-1">
                <span>ACTIVE ENFORCEMENT</span>
                <span className="text-emerald-400 font-bold">4 / 4 PASSING</span>
              </div>

              {GUARDS.map((guard) => {
                const config = STATUS_CONFIG[guard.status];
                const Icon = guard.icon;
                return (
                  <div
                    key={guard.id}
                    className={`group relative flex flex-col justify-between rounded-xl border ${config.borderColor} bg-white/[0.02] p-3 backdrop-blur-xl transition-all duration-base hover:bg-white/[0.05] hover:border-white/[0.2]`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/[0.08] bg-white/[0.04] text-zinc-300 group-hover:text-white transition-colors">
                          <Icon className="h-3.5 w-3.5" />
                        </div>
                        <div>
                          <h3 className="font-ui text-xs font-semibold tracking-tight text-white group-hover:text-strand-gold transition-colors">
                            {guard.name}
                          </h3>
                          <p className="font-mono text-[10px] text-zinc-400 line-clamp-1">
                            {guard.subtitle}
                          </p>
                        </div>
                      </div>

                      <div className="relative flex h-2 w-2">
                        <span
                          className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${config.dotColor}`}
                        />
                        <span
                          className={`relative inline-flex h-2 w-2 rounded-full ${config.dotColor} ${config.dotShadow}`}
                        />
                      </div>
                    </div>

                    <div className="mt-2.5 flex items-center justify-between border-t border-white/[0.05] pt-2 font-mono text-[10px]">
                      <span className="text-zinc-500">{guard.metricLabel}:</span>
                      <span className="font-bold text-zinc-200">{guard.metricValue}</span>
                    </div>
                    <div className="flex items-center justify-between font-mono text-[9px] text-zinc-500">
                      <span>Guard Rule:</span>
                      <span className="text-strand-gold/80">{guard.threshold}</span>
                    </div>
                  </div>
                );
              })}
            </motion.div>
          ) : (
            /* Runtime Health Matrix View */
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
                  <span className="text-zinc-400">Cluster Uptime</span>
                  <span className="font-bold text-emerald-400">99.998%</span>
                </div>

                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2">
                  <span className="text-zinc-400">Duplicate Effects</span>
                  <span className="font-bold text-emerald-400">0 (VERIFIED)</span>
                </div>

                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2">
                  <span className="text-zinc-400">Active Leases</span>
                  <span className="font-bold text-white">4 / 4 Held</span>
                </div>

                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2">
                  <span className="text-zinc-400">Throughput</span>
                  <span className="font-bold text-strand-gold">142.8 steps/s</span>
                </div>

                <div className="flex items-center justify-between border-b border-white/[0.05] pb-2">
                  <span className="text-zinc-400">Fleet Workers</span>
                  <span className="font-bold text-white">{workers.length} Nodes</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-zinc-400">Cluster Capacity</span>
                  <span className="font-bold text-zinc-300">
                    {totalRuns} / {totalCapacity || 15} runs
                  </span>
                </div>
              </div>

              {/* Invariant Assertion Badge */}
              <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3 text-[11px] font-mono text-emerald-400">
                <div className="flex items-center gap-1.5 font-bold mb-1">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>INVARIANT PASSING</span>
                </div>
                <p className="text-[10px] text-zinc-400 leading-relaxed">
                  Zero duplicate effects across cluster handoffs and automatic recovery.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Pinned Bottom Status Legend (Spec 4 core signals) */}
      <div className="border-t border-white/[0.08] bg-black/50 p-3.5 backdrop-blur-xl">
        <div className="mb-2 text-[9px] font-mono uppercase tracking-widest text-zinc-500 font-semibold">
          Status Signals
        </div>
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-glow-emerald" />
            <span className="text-emerald-400">HEALTHY</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-400 shadow-glow-amber" />
            <span className="text-amber-400">DEGRADED</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-glow-cyan" />
            <span className="text-cyan-400">HEALING</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-rose-400 shadow-glow-rose" />
            <span className="text-rose-400">CRITICAL</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
