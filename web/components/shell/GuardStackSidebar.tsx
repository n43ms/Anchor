/**
 * Anchor Operator Console — Guard Stack Sidebar
 * Positioned on the left (w-80).
 * Frosted specular glass panel with subtle bottom gradient mask.
 * Guard Cards: OOM Prevention, Infinite Loop Breaker, Auto Healer, Deadlock & Fence.
 * Status Signal Dots & Accents matching spec tokens.
 * Status Legend pinned at bottom.
 * Canonical Navigation Groups preserved with data-testid="sidebar".
 */
"use client";

import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY } from "@/lib/navigation";
import { useHealth } from "@/hooks/useHealth";
import { ShieldCheck, ShieldAlert, Cpu, Zap, RotateCcw, Lock, ChevronRight, Layers } from "lucide-react";

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

export function GuardStackSidebar() {
  const location = useLocation();
  const pathname = location.pathname;
  const { data: health } = useHealth();
  const [navCollapsed, setNavCollapsed] = useState(false);

  const groups =
    health?.deployment_mode === "local"
      ? [...NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY]
      : NAV_GROUPS;

  const repoUrl =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_REPO_URL) ||
    "https://github.com/n43ms/Anchor";

  return (
    <aside
      data-testid="sidebar"
      className="flex w-80 shrink-0 flex-col justify-between overflow-hidden border-r border-white/[0.08] bg-black/40 backdrop-blur-2xl select-none"
    >
      {/* Top Header */}
      <div className="border-b border-white/[0.08] p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded border border-white/10 bg-white/[0.04]">
              <ShieldCheck className="h-3.5 w-3.5 text-strand-gold" />
            </div>
            <h2 className="font-ui text-xs font-bold uppercase tracking-wider text-white">
              Guard Stack
            </h2>
          </div>
          <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 font-mono text-[10px] font-semibold text-emerald-400">
            4 / 4 ACTIVE
          </span>
        </div>
        <p className="mt-1 font-mono text-[10px] text-zinc-500">
          Continuous runtime invariant enforcement
        </p>
      </div>

      {/* Main Content Area: Guard Cards + Nav Routes */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Guard Cards Stack */}
        <div className="space-y-2.5">
          {GUARDS.map((guard) => {
            const config = STATUS_CONFIG[guard.status];
            const Icon = guard.icon;
            return (
              <div
                key={guard.id}
                className={`group relative flex flex-col justify-between rounded-xl border ${config.borderColor} bg-white/[0.02] p-3 backdrop-blur-xl transition-all duration-base hover:bg-white/[0.05] hover:border-white/[0.2]`}
              >
                {/* Card Header: Icon + Title + Status Dot */}
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

                  {/* Pulsing Status Dot */}
                  <div className="relative flex h-2 w-2">
                    <span
                      className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${config.dotColor}`}
                    />
                    <span
                      className={`relative inline-flex h-2 w-2 rounded-full ${config.dotColor} ${config.dotShadow}`}
                    />
                  </div>
                </div>

                {/* Card Metrics Row */}
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
        </div>

        {/* Canonical Navigation Section (Fully accessible per Spec §13.3 / Tests) */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.01] p-2.5">
          <button
            type="button"
            onClick={() => setNavCollapsed(!navCollapsed)}
            className="flex w-full items-center justify-between text-[10px] font-mono uppercase tracking-wider text-zinc-400 hover:text-white pb-1.5"
          >
            <span className="flex items-center gap-1.5 font-bold">
              <Layers className="h-3 w-3 text-strand-gold" />
              Console Navigation
            </span>
            <ChevronRight
              className={`h-3 w-3 text-zinc-500 transition-transform ${
                navCollapsed ? "" : "rotate-90"
              }`}
            />
          </button>

          {!navCollapsed && (
            <div className="mt-1 space-y-3 pt-1 border-t border-white/[0.04]">
              {groups.map((group) => (
                <div key={group.label} className="space-y-0.5">
                  <div className="px-2 py-0.5 text-[9px] font-mono uppercase tracking-widest text-zinc-500 font-semibold">
                    {group.label}
                  </div>
                  {group.pages.map((page) => {
                    const active =
                      pathname === page.href ||
                      (page.href !== "/" && pathname.startsWith(page.href));
                    return (
                      <Link
                        key={page.href}
                        to={page.href}
                        className={`flex items-center justify-between rounded-lg px-2.5 py-1 text-xs font-mono transition-all ${
                          active
                            ? "bg-white/[0.1] text-white font-medium border border-white/[0.1] text-strand-gold"
                            : "text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200"
                        }`}
                        aria-current={active ? "page" : undefined}
                      >
                        <span>{page.label}</span>
                        {active && (
                          <span className="h-1.5 w-1.5 rounded-full bg-strand-gold" />
                        )}
                      </Link>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Pinned Bottom Status Legend (Spec 4 core signals) */}
      <div className="border-t border-white/[0.08] bg-black/50 p-3 backdrop-blur-xl">
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

        <div className="mt-3 pt-2 border-t border-white/[0.06] flex items-center justify-between text-[10px] font-mono text-zinc-500">
          <a
            href={repoUrl}
            target="_blank"
            rel="noreferrer"
            className="hover:text-white transition-colors"
          >
            docs & specs ↗
          </a>
          <span>constitution v1.0</span>
        </div>
      </div>
    </aside>
  );
}
