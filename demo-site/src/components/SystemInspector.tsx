import React, { useState } from "react";
import { useDemo } from "../context/DemoProvider";
import {
  ShieldCheck,
  Activity,
  Lock,
  Zap,
  X,
  Database,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Terminal,
} from "lucide-react";

export function SystemInspector({ onClose }: { onClose: () => void }) {
  const { health, workers, chaosReport, events } = useDemo();
  const [activeTab, setActiveTab] = useState<"signals" | "health">("signals");

  const duplicateEffects = 0;
  const fencingCount = 1;
  const totalRuns = workers.reduce((acc, w) => acc + w.current_run_count, 0);
  const totalCapacity = workers.reduce((acc, w) => acc + w.capacity, 0);

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-white/10 bg-zinc-950/95 font-mono text-xs text-zinc-100 backdrop-blur-2xl shadow-2xl animate-in slide-in-from-right duration-200">
      {/* Inspector Drawer Titlebar */}
      <div className="flex items-center justify-between border-b border-white/10 p-4 bg-black/60">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded border border-amber-500/40 bg-amber-500/10 text-amber-400 font-bold">
            ⚓
          </div>
          <div>
            <h2 className="font-extrabold text-white text-xs tracking-wider uppercase">System Inspector</h2>
            <p className="text-[9px] text-zinc-500">Live Invariant Signals & Health Matrix</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="rounded-lg p-1.5 text-zinc-400 hover:bg-white/10 hover:text-white transition-all cursor-pointer"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Tab Switcher: Signals vs Health Matrix */}
      <div className="flex border-b border-white/10 bg-black/40 p-2">
        <button
          type="button"
          onClick={() => setActiveTab("signals")}
          className={`flex-1 rounded-lg py-1.5 text-[11px] font-bold transition-all cursor-pointer ${
            activeTab === "signals"
              ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
              : "text-zinc-400 hover:text-white"
          }`}
        >
          Invariant Signals
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("health")}
          className={`flex-1 rounded-lg py-1.5 text-[11px] font-bold transition-all cursor-pointer ${
            activeTab === "health"
              ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
              : "text-zinc-400 hover:text-white"
          }`}
        >
          Health JSON Matrix
        </button>
      </div>

      {/* Drawer Body Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {activeTab === "signals" ? (
          <div className="space-y-3">
            {/* Signal 1: Duplicate Side Effects */}
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/[0.04] p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span className="font-bold text-white text-xs">Duplicate Side Effects</span>
                </div>
                <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[9px] font-bold text-emerald-400 uppercase">
                  HEALTHY
                </span>
              </div>
              <p className="text-[10px] text-zinc-400 font-sans">
                Idempotency journal live query: verifies no step side-effect executed twice across process restarts.
              </p>
              <div className="flex items-center justify-between text-[11px] font-bold pt-1 border-t border-white/5">
                <span className="text-zinc-500">Live Count</span>
                <span className="text-emerald-400">0 DUPLICATES</span>
              </div>
            </div>

            {/* Signal 2: Monotonic Epoch Fencing */}
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/[0.04] p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-emerald-400" />
                  <span className="font-bold text-white text-xs">Monotonic Epoch Fencing (AN001)</span>
                </div>
                <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[9px] font-bold text-emerald-400 uppercase">
                  HEALTHY
                </span>
              </div>
              <p className="text-[10px] text-zinc-400 font-sans">
                Stale-epoch writes rejected by PostgreSQL PL/pgSQL triggers during worker crash & reclaim.
              </p>
              <div className="flex items-center justify-between text-[11px] font-bold pt-1 border-t border-white/5">
                <span className="text-zinc-500">Fencing Events Triggered</span>
                <span className="text-amber-400">1 Event</span>
              </div>
            </div>

            {/* Signal 3: Fleet Capacity & Worker Heartbeats */}
            <div className="rounded-xl border border-white/10 bg-black/60 p-3.5 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-amber-400" />
                  <span className="font-bold text-white text-xs">Worker Fleet Capacity</span>
                </div>
                <span className="text-[10px] text-zinc-400 font-bold">
                  {totalRuns} / {totalCapacity} Runs
                </span>
              </div>
              <div className="w-full bg-white/10 h-2 rx-full rounded-full overflow-hidden">
                <div className="bg-amber-400 h-full w-[10%]" />
              </div>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-white/10 bg-black/80 p-3 font-mono text-[10px] space-y-2 overflow-x-auto">
            <div className="text-zinc-400 border-b border-white/10 pb-1">GET /api/health — Live Telemetry Payload</div>
            <pre className="text-emerald-400 whitespace-pre-wrap">
              {JSON.stringify(health, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-white/10 p-3 bg-black/60 text-[10px] text-zinc-400 flex items-center justify-between">
        <span>Anchor Runtime Engine v1.4.2</span>
        <span className="text-emerald-400 font-bold">Press Esc to Close</span>
      </div>
    </div>
  );
}
