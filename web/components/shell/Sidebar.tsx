/**
 * Anchor Operator Console — Navigation Sidebar
 * Clean, modern left-hand navigation console.
 * Displays cluster indicator, deployment mode, and canonical navigation routes.
 * Preserves data-testid="sidebar" and spec §13.3 route requirements.
 */
"use client";

import { Link, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import { NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY } from "@/lib/navigation";
import { useHealth } from "@/hooks/useHealth";
import {
  Layers,
  Settings,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  Server,
  Terminal,
  Play,
  FileText,
  BarChart2,
  Wrench,
  AlertTriangle,
} from "lucide-react";

export function Sidebar() {
  const location = useLocation();
  const pathname = location.pathname;
  const { data: health, stale } = useHealth();

  const groups =
    health?.deployment_mode === "local"
      ? [...NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY]
      : NAV_GROUPS;

  const allPages = groups.flatMap((g) => g.pages);

  const isHealthy = health?.database_reachable && !health.degraded && !stale;

  const modeLabel =
    health?.deployment_mode === "demonstration"
      ? "DEMONSTRATION MODE"
      : "LOCAL DEV MODE";

  const repoUrl =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_REPO_URL) ||
    "https://github.com/n43ms/Anchor";

  return (
    <aside
      data-testid="sidebar"
      className="flex w-64 shrink-0 flex-col justify-between overflow-hidden border-r border-white/[0.08] bg-black/40 backdrop-blur-2xl select-none"
    >
      {/* Top Cluster & Mode Status Header */}
      <div className="border-b border-white/[0.08] p-4 space-y-3">
        {/* Cluster Status Pill */}
        <div
          className={`flex items-center justify-between rounded-xl border px-3 py-2 text-xs font-mono backdrop-blur-md transition-all ${
            isHealthy
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
              : "border-amber-500/30 bg-amber-500/10 text-amber-400"
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span
                className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${
                  isHealthy ? "bg-emerald-400" : "bg-amber-400"
                }`}
              />
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  isHealthy ? "bg-emerald-400 shadow-glow-emerald" : "bg-amber-400 shadow-glow-amber"
                }`}
              />
            </span>
            <span className="font-bold uppercase tracking-wider text-[11px]">
              {isHealthy ? "CLUSTER 04: HEALTHY" : "CLUSTER 04: DEGRADED"}
            </span>
          </div>
          <span className="text-[10px] text-zinc-500 font-bold">
            {health?.worker_count ?? 0}w
          </span>
        </div>

        {/* Deployment Mode Badge */}
        <div className="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-1.5 text-[10px] font-mono text-zinc-400">
          <span className="uppercase tracking-widest text-zinc-500">Deployment</span>
          <span className="font-semibold text-strand-gold">{modeLabel}</span>
        </div>
      </div>

      {/* Navigation Groups List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4 scrollbar-thin">
        {groups.map((group) => (
          <div key={group.label} className="space-y-1">
            <div className="px-2.5 py-1 text-[9px] font-mono uppercase tracking-widest text-zinc-500 font-bold">
              {group.label}
            </div>
            <div className="space-y-0.5">
              {group.pages.map((page) => {
                const isExact = pathname === page.href;
                const isNestedChild =
                  page.href !== "/" &&
                  pathname.startsWith(page.href + "/") &&
                  !allPages.some((p) => p.href !== page.href && pathname === p.href);
                const active = isExact || isNestedChild;

                return (
                  <Link
                    key={page.href}
                    to={page.href}
                    className={`relative flex items-center justify-between rounded-xl px-3 py-2 text-xs font-mono transition-colors ${
                      active
                        ? "text-strand-gold font-bold"
                        : "text-zinc-400 hover:bg-white/[0.04] hover:text-white"
                    }`}
                    aria-current={active ? "page" : undefined}
                  >
                    {active && (
                      <motion.div
                        layoutId="sidebarActiveBackground"
                        className="absolute inset-0 rounded-xl bg-strand-gold/15 border border-strand-gold/30 shadow-sm"
                        transition={{ type: "spring", stiffness: 350, damping: 30 }}
                      />
                    )}
                    <span className="relative z-10">{page.label}</span>
                    {active && (
                      <motion.span
                        layoutId="sidebarActiveDot"
                        className="relative z-10 h-1.5 w-1.5 rounded-full bg-strand-gold shadow-glow-gold"
                        transition={{ type: "spring", stiffness: 350, damping: 30 }}
                      />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Pinned Bottom Settings & Specs Footer */}
      <div className="border-t border-white/[0.08] bg-black/50 p-3.5 backdrop-blur-xl space-y-2">
        <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
          <Link
            to="/settings/environment"
            className="flex items-center gap-1.5 hover:text-white transition-colors"
          >
            <Settings className="h-3.5 w-3.5" />
            <span>Settings</span>
          </Link>
          <a
            href={repoUrl}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 hover:text-white transition-colors text-zinc-500 hover:text-zinc-300"
          >
            <span>Specs</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
        <div className="text-[9px] font-mono text-zinc-600 flex justify-between">
          <span>Anchor Runtime v0.1</span>
          <span>Durable AST</span>
        </div>
      </div>
    </aside>
  );
}
