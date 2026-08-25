import React from "react";
import { useDemo } from "../../context/DemoProvider";
import { RunDetail } from "../run/RunDetail";
import { InvariantPanel } from "../chaos/InvariantPanel";
import { ChaosVisualizer } from "../chaos/ChaosVisualizer";
import { ReportCard } from "../chaos/ReportCard";
import {
  Activity,
  Flame,
  Terminal,
  ShieldCheck,
  Zap,
  RefreshCw,
  Play,
  RotateCcw,
  CheckCircle2,
} from "lucide-react";

export const MiniOperatorConsoleContent: React.FC = () => {
  const {
    stage,
    activeTab,
    setActiveTab,
    timeline,
    chaosReport,
    events,
    isSimulating,
    killWorker,
    triggerRecovery,
    resetDemoState,
  } = useDemo();

  return (
    <div className="flex flex-col h-full bg-zinc-950 font-mono text-xs text-zinc-100 select-none overflow-hidden rounded-2xl border border-white/10 shadow-2xl">
      {/* Top Embedded Window Titlebar */}
      <div className="flex items-center justify-between border-b border-white/10 bg-black/60 px-4 py-2.5 backdrop-blur-xl">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="h-3 w-3 rounded-full bg-rose-500/80 inline-block" />
            <span className="h-3 w-3 rounded-full bg-amber-500/80 inline-block" />
            <span className="h-3 w-3 rounded-full bg-emerald-500/80 inline-block" />
          </div>
          <span className="ml-3 text-[11px] font-bold text-zinc-400 tracking-wider uppercase">
            Anchor Operator Console — Mini Sandbox Replica
          </span>
        </div>

        {/* Tab Navigation Controls */}
        <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-white/[0.03] p-1">
          <button
            type="button"
            onClick={() => setActiveTab("timeline")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1 text-[11px] font-bold transition-all ${
              activeTab === "timeline"
                ? "bg-strand-gold/20 text-strand-gold border border-strand-gold/40"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            <span>Timeline & Handoff</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("chaos")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1 text-[11px] font-bold transition-all ${
              activeTab === "chaos"
                ? "bg-strand-gold/20 text-strand-gold border border-strand-gold/40"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Flame className="h-3.5 w-3.5" />
            <span>Chaos Proof</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("logs")}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1 text-[11px] font-bold transition-all ${
              activeTab === "logs"
                ? "bg-strand-gold/20 text-strand-gold border border-strand-gold/40"
                : "text-zinc-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Terminal className="h-3.5 w-3.5" />
            <span>Event Audit Logs</span>
          </button>
        </div>
      </div>

      {/* Main Sandbox Interactive Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-black/40 custom-scrollbar">
        {/* Interactive Action Control Toolbar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/[0.02] p-3.5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0" />
            <div>
              <span className="font-bold text-white text-xs">Guided Interactive Simulation</span>
              <p className="text-[10px] text-zinc-400">
                {stage === "normal" && "Run r101 active: worker-a#1 died after TOOL_INTENT (step 2), worker-b#1 recorded TOOL_RESULT & completed run."}
                {stage === "crashed" && "worker-a#1 terminated abruptly! Lease expiring."}
                {stage === "recovered" && "worker-b#1 reclaimed run. Replayed steps, zero duplicate side-effects."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {stage === "normal" && (
              <button
                type="button"
                onClick={() => killWorker("worker-a#1")}
                disabled={isSimulating}
                className="flex items-center gap-1.5 rounded-lg border border-rose-500/50 bg-rose-500/20 px-3 py-1.5 text-xs font-bold text-rose-300 hover:bg-rose-500/30 transition-all"
              >
                <Zap className="h-3.5 w-3.5 text-rose-400" />
                <span>Simulate Worker Kill (os._exit)</span>
              </button>
            )}

            {stage === "crashed" && (
              <button
                type="button"
                onClick={triggerRecovery}
                disabled={isSimulating}
                className="flex items-center gap-1.5 rounded-lg border border-strand-gold/50 bg-strand-gold/20 px-3 py-1.5 text-xs font-bold text-strand-gold hover:bg-strand-gold/30 transition-all animate-pulse"
              >
                <Play className="h-3.5 w-3.5" />
                <span>Auto-Reclaim & Recover</span>
              </button>
            )}

            <button
              type="button"
              onClick={resetDemoState}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-zinc-300 hover:bg-white/10 transition-all"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset Scenario</span>
            </button>
          </div>
        </div>

        {/* Tab 1: Timeline & Handoff View (Reuses exact RunDetail component) */}
        {activeTab === "timeline" && (
          <div className="space-y-4">
            <RunDetail
              run={timeline}
              onKill={(workerId) => killWorker(workerId)}
            />
          </div>
        )}

        {/* Tab 2: Chaos Proof & Invariant Verification */}
        {activeTab === "chaos" && (
          <div className="space-y-5">
            <ChaosVisualizer activeRun={null} report={chaosReport} />
            <InvariantPanel report={chaosReport} loading={false} />
            <ReportCard report={chaosReport} />
          </div>
        )}

        {/* Tab 3: Raw Event Audit Logs */}
        {activeTab === "logs" && (
          <div className="rounded-xl border border-white/10 bg-black/80 p-4 space-y-2">
            <div className="flex items-center justify-between pb-2 border-b border-white/10 text-[11px] text-zinc-400 font-bold">
              <span>SEQUENCE & EVENT TYPE</span>
              <span>EPOCH & WORKER</span>
            </div>
            <div className="space-y-1.5">
              {events.map((ev) => (
                <div
                  key={ev.seq}
                  className="flex items-center justify-between text-[11px] py-1 border-b border-white/[0.04] text-zinc-300"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-500 font-mono">#{ev.seq}</span>
                    <span className="font-bold text-strand-gold">{ev.type}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-400">epoch {ev.epoch}</span>
                    <span className="rounded bg-white/5 px-1.5 py-0.5 text-zinc-300">{ev.worker_id}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer Status Bar */}
      <div className="flex items-center justify-between border-t border-white/10 bg-black/60 px-4 py-2 text-[10px] text-zinc-400">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Standalone Mock Engine Active (300ms simulated latency)</span>
        </div>
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-3 w-3 text-emerald-400" />
          <span>Zero Duplicate Side-Effects Verified</span>
        </div>
      </div>
    </div>
  );
};

export const MiniOperatorConsole: React.FC = () => {
  return (
    <DemoProvider>
      <div className="w-full max-w-4xl h-[620px] mx-auto my-6">
        <MiniOperatorConsoleContent />
      </div>
    </DemoProvider>
  );
};

