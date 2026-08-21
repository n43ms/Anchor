/**
 * Anchor Operator Console Layout
 * Assembles:
 * - 3D Background Canvas (Silk Gold Threads & Checkpoint Diamonds)
 * - Top Navigation (h-14) with Inspector Toggle
 * - Left Navigation Sidebar (w-64) with Cluster & Mode status
 * - Center Dynamic Workspace Router Outlet (Spacious & Clean)
 * - Right System Inspector Panel (w-80, Toggle-closable Guards & Runtime Health)
 * - Bottom Monospace Terminal Console (Collapsible)
 */
"use client";

import { useState } from "react";
import { Outlet } from "react-router-dom";
import { TopNavigation } from "./TopNavigation";
import { Sidebar } from "./Sidebar";
import { ModeBanner } from "./ModeBanner";
import { RightInspectorPanel } from "./RightInspectorPanel";
import { TerminalConsole } from "./TerminalConsole";
import { GoldenThreadsCanvas } from "@/components/canvas/GoldenThreadsCanvas";
import { ShieldCheck, PanelRightOpen } from "lucide-react";

export function ConsoleLayout() {
  const [inspectorOpen, setInspectorOpen] = useState(true);

  return (
    <div className="relative flex h-screen w-screen flex-col overflow-hidden bg-surface-page font-ui text-ink-primary selection:bg-strand-gold/20 selection:text-strand-gold">
      {/* 3D Background: Silk Threads & Checkpoint Pointers (z-index: -1) */}
      <GoldenThreadsCanvas />

      {/* Top Header Navigation (h-14) */}
      <TopNavigation
        inspectorOpen={inspectorOpen}
        onToggleInspector={() => setInspectorOpen((prev) => !prev)}
      />

      {/* Mode Banner notification ribbon if degraded / offline */}
      <ModeBanner />

      {/* Main Operator Command Grid */}
      <div className="relative flex flex-1 overflow-hidden">
        {/* Left: Navigation Sidebar (w-64) */}
        <Sidebar />

        {/* Center: Active Viewport Stream */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 transition-all duration-base scrollbar-thin">
          <div className="mx-auto max-w-6xl space-y-8 pb-12">
            <Outlet />
          </div>
        </main>

        {/* Right: Toggle-closable System Inspector (Guards & Runtime Health) */}
        {inspectorOpen ? (
          <div className="hidden lg:flex">
            <RightInspectorPanel onClose={() => setInspectorOpen(false)} />
          </div>
        ) : (
          /* Slim Floating Re-open Button on the Right Edge */
          <div className="hidden lg:flex items-center pr-2 py-4">
            <button
              type="button"
              onClick={() => setInspectorOpen(true)}
              className="group flex flex-col items-center gap-2 rounded-2xl border border-white/[0.08] bg-black/50 p-2.5 backdrop-blur-2xl text-zinc-400 hover:border-strand-gold/50 hover:bg-strand-gold/10 hover:text-strand-gold transition-all shadow-xl"
              title="Open System Inspector"
              aria-label="Open System Inspector"
            >
              <ShieldCheck className="h-4 w-4 text-strand-gold" />
              <span className="[writing-mode:vertical-rl] rotate-180 text-[10px] font-mono uppercase tracking-widest font-semibold py-1">
                Inspector
              </span>
              <PanelRightOpen className="h-3.5 w-3.5 text-zinc-500 group-hover:text-strand-gold" />
            </button>
          </div>
        )}
      </div>

      {/* Bottom: Terminal Console */}
      <TerminalConsole />
    </div>
  );
}
