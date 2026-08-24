/**
 * Anchor Operator Console — Chaos Engineering Control Center
 * Spec T521, T522, T525.
 * "This page is the project — it is what you show first."
 */

import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  Flame,
  Play,
  RefreshCw,
  ShieldCheck,
  Zap,
  Activity,
  CheckCircle2,
  Clock,
  AlertTriangle,
  History,
  Sliders,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ChaosParams, ChaosReport, ChaosRun } from "@/lib/types";
import { InvariantPanel } from "@/components/chaos/InvariantPanel";
import { ReportCard } from "@/components/chaos/ReportCard";
import { ChaosVisualizer } from "@/components/chaos/ChaosVisualizer";

export default function ChaosConsolePage() {
  const [params, setParams] = useState<ChaosParams>({
    worker_count: 3,
    run_count: 5,
    duration_seconds: 60,
    kill_rate_per_minute: 6,
    latency_injection_ms: 100,
    stall_injection_rate: 0.05,
    tool_failure_rate: 0.05,
    uncertainty_crash_rate: 0.02,
  });

  const [starting, setStarting] = useState(false);
  const [activeRun, setActiveRun] = useState<ChaosRun | null>(null);
  const [latestReport, setLatestReport] = useState<ChaosReport | null>(null);
  const [recentRuns, setRecentRuns] = useState<Array<ChaosRun & { report: ChaosReport | null }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setError(null);
      const [listRes, reportRes] = await Promise.allSettled([
        api.listChaosRuns(),
        api.getLatestChaosReport(),
      ]);

      if (listRes.status === "fulfilled") {
        setRecentRuns(listRes.value.items);
        const currentRunning = listRes.value.items.find((r) => r.status === "running");
        if (currentRunning) {
          setActiveRun(currentRunning);
        } else if (activeRun?.status === "running") {
          setActiveRun(null);
        }
      }

      if (reportRes.status === "fulfilled") {
        setLatestReport(reportRes.value);
      }
    } catch (err) {
      console.error("Failed to fetch chaos data", err);
      setError(err instanceof Error ? err.message : "Failed to load chaos status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleStartChaos = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setStarting(true);
      setError(null);
      const newRun = await api.startChaos(params);
      setActiveRun(newRun);
      fetchData();
    } catch (err) {
      console.error("Failed to start chaos run", err);
      setError(err instanceof Error ? err.message : "Failed to trigger chaos run");
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Clean Chaos Console Header */}
      <div className="rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-2xl p-6 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-strand-gold/40 bg-strand-gold/10 text-strand-gold">
              <Flame className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight font-mono">
                Chaos Console
              </h1>
              <p className="text-xs text-zinc-400 font-mono mt-0.5">
                Simulate hardware failures, worker SIGKILL process terminations, network latency, and lease expirations to verify zero duplicate side-effects and database-level invariants.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-xs font-mono text-rose-300 flex items-center gap-3">
          <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Grid: Control Panel + Active / Recent Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Launch Control Form (T521) */}
        <div className="lg:col-span-1 space-y-6">
          <div className="rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-xl p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
              <div className="flex items-center gap-2 text-white font-mono font-bold text-sm">
                <Sliders className="h-4 w-4 text-strand-gold" />
                <span>Chaos Parameter Config</span>
              </div>
              <span className="text-[10px] font-mono text-zinc-500 uppercase">Interactive Harness</span>
            </div>

            <form onSubmit={handleStartChaos} className="space-y-4 font-mono text-xs">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-zinc-400 text-[11px]">Number of Workers</label>

                  <span className="text-[10px] font-mono text-zinc-500">Range: 1 – 26</span>
                </div>
                <input
                  type="number"
                  min="1"
                  max="26"
                  value={params.worker_count}
                  onChange={(e) => setParams({ ...params, worker_count: Math.min(26, Math.max(1, parseInt(e.target.value) || 1)) })}
                  className="w-full rounded-xl border border-white/[0.1] bg-black/60 px-3.5 py-2 text-white focus:border-strand-gold focus:outline-none"
                />
              </div>


              <div className="space-y-1.5">
                <label className="text-zinc-400 text-[11px]">Target Agent Runs</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={params.run_count}
                  onChange={(e) => setParams({ ...params, run_count: parseInt(e.target.value) || 1 })}
                  className="w-full rounded-xl border border-white/[0.1] bg-black/60 px-3.5 py-2 text-white focus:border-strand-gold focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-zinc-400 text-[11px]">Duration (Seconds)</label>
                <input
                  type="number"
                  min="10"
                  max="300"
                  value={params.duration_seconds}
                  onChange={(e) => setParams({ ...params, duration_seconds: parseInt(e.target.value) || 10 })}
                  className="w-full rounded-xl border border-white/[0.1] bg-black/60 px-3.5 py-2 text-white focus:border-strand-gold focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-zinc-400 text-[11px]">Kill Rate (Kills / Min)</label>
                <input
                  type="number"
                  min="0"
                  max="60"
                  value={params.kill_rate_per_minute}
                  onChange={(e) => setParams({ ...params, kill_rate_per_minute: parseInt(e.target.value) || 0 })}
                  className="w-full rounded-xl border border-white/[0.1] bg-black/60 px-3.5 py-2 text-white focus:border-strand-gold focus:outline-none"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-zinc-400 text-[11px]">Latency Injection (ms)</label>
                <input
                  type="number"
                  min="0"
                  max="2000"
                  value={params.latency_injection_ms}
                  onChange={(e) => setParams({ ...params, latency_injection_ms: parseInt(e.target.value) || 0 })}
                  className="w-full rounded-xl border border-white/[0.1] bg-black/60 px-3.5 py-2 text-white focus:border-strand-gold focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={starting || activeRun?.status === "running"}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-strand-gold px-4 py-3 font-mono font-bold text-black hover:bg-amber-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-glow-gold text-xs uppercase tracking-wider"
              >
                {starting ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Initiating Harness...</span>
                  </>
                ) : activeRun?.status === "running" ? (
                  <>
                    <Activity className="h-4 w-4 animate-pulse text-black" />
                    <span>Chaos Run Active</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 fill-current" />
                    <span>Launch Chaos Harness</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Live Chaos Strand Visualizer + Live Invariant Panel & Report Summary */}
        <div className="lg:col-span-2 space-y-6">
          <ChaosVisualizer activeRun={activeRun} report={latestReport} />
          <InvariantPanel report={latestReport} loading={loading} />

          {latestReport && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs font-mono text-zinc-400">
                <span className="font-bold uppercase tracking-wider text-white">Latest Verified Report</span>
                <Link to="/chaos/history" className="text-strand-gold hover:underline flex items-center gap-1">
                  <History className="h-3.5 w-3.5" /> View All Past Runs
                </Link>
              </div>
              <ReportCard report={latestReport} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
