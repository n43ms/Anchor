/**
 * Anchor Operator Console — Top Navigation
 * Fixed h-14 frosted glass navigation bar.
 * Left: Anchor SVG logo + Console title.
 * Center: Clean navigation breadcrumb / quick access.
 * Right: System Inspector toggle (Guards & Health), Agent Cluster Selector, Settings.
 */
"use client";

import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useHealth } from "@/hooks/useHealth";
import { NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY } from "@/lib/navigation";
import { Settings, ExternalLink, ChevronDown, Activity, ShieldCheck, PanelRightClose, PanelRightOpen } from "lucide-react";

interface TopNavigationProps {
  inspectorOpen?: boolean;
  onToggleInspector?: () => void;
}

export function TopNavigation({ inspectorOpen = true, onToggleInspector }: TopNavigationProps) {
  const location = useLocation();
  const pathname = location.pathname;
  const { data: health, stale } = useHealth();
  const [selectedGroup, setSelectedGroup] = useState("Cluster 04 (Production)");
  const [groupDropdownOpen, setGroupDropdownOpen] = useState(false);

  const groups =
    health?.deployment_mode === "local"
      ? [...NAV_GROUPS, SETTINGS_GROUP_LOCAL_ONLY]
      : NAV_GROUPS;

  const modeLabel =
    health?.deployment_mode === "demonstration"
      ? "demonstration mode"
      : "local mode";

  const repoUrl =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_REPO_URL) ||
    "https://github.com/n43ms/Anchor";

  const isHealthy = health?.database_reachable && !health.degraded && !stale;

  return (
    <header className="sticky top-0 z-40 flex h-14 w-full items-center justify-between border-b border-white/[0.08] bg-black/40 px-5 backdrop-blur-2xl transition-all">
      {/* Left: Logo & Dashboard Title */}
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="group flex items-center gap-2.5 text-sm font-bold tracking-tight text-white transition-colors"
        >
          {/* Geometric Anchor SVG Logo */}
          <div className="relative flex h-8 w-8 items-center justify-center rounded-xl border border-white/[0.1] bg-white/[0.04] p-1.5 transition-all group-hover:border-strand-gold/50 group-hover:bg-strand-gold/10">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="h-full w-full text-strand-gold"
            >
              <circle cx="12" cy="5" r="3" />
              <line x1="12" y1="22" x2="12" y2="8" />
              <path d="M5 12H2a10 10 0 0 0 20 0h-3" />
            </svg>
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5 leading-none">
              <span className="font-ui font-extrabold uppercase tracking-wider text-white">
                Anchor
              </span>
              <span className="text-[10px] font-mono text-zinc-500">v0.1</span>
            </div>
            <span className="text-[9px] font-mono uppercase tracking-widest text-zinc-500">
              OPERATOR CONSOLE
            </span>
          </div>
        </Link>

        <div className="h-4 w-px bg-white/[0.08]" />

        {/* Current View Breadcrumb */}
        <div className="hidden md:flex items-center gap-2 text-xs font-mono text-zinc-400">
          <span>/</span>
          <span className="text-white font-medium capitalize">
            {pathname === "/" ? "Dashboard" : pathname.replace(/^\//, "").replace(/-/g, " ")}
          </span>
        </div>
      </div>

      {/* Right Controls: Inspector Toggle + Group Selector + Settings */}
      <div className="flex items-center gap-3">
        {/* Toggle Right Inspector Drawer */}
        {onToggleInspector && (
          <button
            type="button"
            onClick={onToggleInspector}
            className={`flex items-center gap-2 rounded-xl border px-3 py-1.5 text-xs font-mono transition-all ${
              inspectorOpen
                ? "border-strand-gold/40 bg-strand-gold/15 text-strand-gold font-semibold shadow-sm"
                : "border-white/[0.08] bg-white/[0.02] text-zinc-400 hover:border-white/[0.2] hover:text-white"
            }`}
            title={inspectorOpen ? "Collapse System Inspector" : "Expand System Inspector"}
          >
            <ShieldCheck className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">System Inspector</span>
            {inspectorOpen ? (
              <PanelRightClose className="h-3.5 w-3.5 text-strand-gold" />
            ) : (
              <PanelRightOpen className="h-3.5 w-3.5 text-zinc-400" />
            )}
          </button>
        )}

        {/* Minimalist Select Agent Group Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setGroupDropdownOpen(!groupDropdownOpen)}
            className="flex items-center gap-2 rounded-xl border border-white/[0.08] bg-white/[0.02] px-3 py-1.5 text-xs font-mono text-zinc-300 hover:border-white/[0.2] hover:text-white transition-all"
          >
            <Activity className="h-3.5 w-3.5 text-strand-gold" />
            <span className="hidden sm:inline">{selectedGroup}</span>
            <ChevronDown className="h-3 w-3 text-zinc-500" />
          </button>

          {groupDropdownOpen && (
            <div className="absolute right-0 mt-1.5 w-60 rounded-2xl border border-white/[0.12] bg-zinc-950/95 p-1.5 shadow-2xl backdrop-blur-2xl z-50">
              <div className="px-2.5 py-1 text-[10px] font-mono uppercase tracking-widest text-zinc-500">
                Switch Agent Cluster
              </div>
              {[
                "Cluster 04 (Production)",
                "Demo Worker Fleet",
                "Refund & Billing Agents",
                "Chaos Experiment Pool",
              ].map((grp) => (
                <button
                  key={grp}
                  type="button"
                  onClick={() => {
                    setSelectedGroup(grp);
                    setGroupDropdownOpen(false);
                  }}
                  className={`flex w-full items-center justify-between rounded-xl px-2.5 py-1.5 text-left text-xs font-mono transition-colors ${
                    selectedGroup === grp
                      ? "bg-white/[0.1] text-strand-gold font-semibold"
                      : "text-zinc-400 hover:bg-white/[0.04] hover:text-white"
                  }`}
                >
                  <span>{grp}</span>
                  {selectedGroup === grp && (
                    <span className="h-1.5 w-1.5 rounded-full bg-strand-gold" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Documentation Link */}
        <a
          href={repoUrl}
          target="_blank"
          rel="noreferrer"
          title="Operator Documentation"
          className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.02] text-zinc-400 hover:border-white/[0.2] hover:text-white transition-all"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </a>

        {/* Settings Gear */}
        <Link
          to="/settings/environment"
          title="Console Settings"
          className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/[0.08] bg-white/[0.02] text-zinc-400 hover:border-white/[0.2] hover:text-white transition-all"
        >
          <Settings className="h-3.5 w-3.5" />
        </Link>
      </div>
    </header>
  );
}
