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
import { motion, AnimatePresence } from "framer-motion";
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

  const repoUrl =
    (typeof import.meta !== "undefined" && import.meta.env?.VITE_REPO_URL) ||
    "https://github.com/n43ms/Anchor";

  return (
    <header className="sticky top-0 z-40 flex h-14 w-full items-center justify-between border-b border-white/[0.08] bg-black/40 px-5 backdrop-blur-2xl transition-all">
      {/* Left: Logo & Dashboard Title */}
      <div className="flex items-center gap-4">
        <Link
          to="/"
          className="group flex items-center gap-2.5 text-sm font-bold tracking-tight text-white transition-colors"
        >
          {/* Geometric Anchor SVG Logo */}
          <div className="relative flex h-8 w-8 items-center justify-center rounded-xl border border-strand-gold/40 bg-strand-gold/10 p-1.5 transition-all group-hover:border-strand-gold/60 group-hover:bg-strand-gold/20">
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
              <span className="rounded-full border border-strand-gold/30 bg-strand-gold/10 px-1.5 py-0.2 text-[9px] font-mono font-semibold text-strand-gold">
                v1.5.0-prod
              </span>
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

      {/* Right Controls: License Badge + Inspector Toggle + Settings */}
      <div className="flex items-center gap-3">
        {/* Apache 2.0 License Badge */}
        <a
          href="https://github.com/n43ms/Anchor/blob/main/LICENSE"
          target="_blank"
          rel="noreferrer"
          className="hidden sm:flex items-center gap-1 rounded-xl border border-strand-gold/30 bg-strand-gold/10 px-2.5 py-1 text-[11px] font-mono font-bold text-strand-gold hover:bg-strand-gold/20 transition-all"
        >
          <ShieldCheck className="h-3 w-3 text-amber-400" />
          <span>Apache 2.0</span>
        </a>
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
