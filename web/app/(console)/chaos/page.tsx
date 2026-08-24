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

export default function ChaosConsolePage() {
  const [params, setParams] = useState<ChaosParams>({
    worker_count: 3,
    run_count: 10,
    duration_seconds: 45,
    kill_rate_per_minute: 12,
    latency_injection_ms: 150,
    stall_injection_rate: 0.1,
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
      {/* Hero Banner (T525: "This page is the project — it is what you show first") */}
      <div className="relative overflow-hidden rounded-3xl border border-strand-gold/30 bg-gradient-to-br from-strand-gold/10 via-black to-black p-8 backdrop-blur-2xl shadow-2xl">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <Flame className="h-64 w-64 text-strand-gold" />
        </div>

        <div className="relative z-10 space-y-4 max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-strand-gold/40 bg-strand-gold/10 px-3.5 py-1 text-xs font-mono font-bold text-strand-gold uppercase tracking-wider">
            <Flame className="h-3.5 w-3.5 animate-pulse" />
            <span>FAANG-Grade Fault Injection Suite</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight font-mono">
            Deterministic Chaos Control Center
          </h1>

          <p className="text-sm text-zinc-300 leading-relaxed font-mono">
            <strong className="text-white">This page is the project — it is what you show first.</strong>{" "}
            Anchor proves non-negotiable execution correctness under simulated hardware failure, brutal SIGKILL worker termination, network partition, and lease expiration.
          </p>

          <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-zinc-400 pt-2">
            <span className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle2 className="h-4 w-4" /> 0 Duplicate Side Effects
            </span>
            <span className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle2 className="h-4 w-4" /> Single-Writer Zombie Fencing
            </span>
            <span className="flex items-center gap-1.5 text-emerald-400">
              <CheckCircle2 className="h-4 w-4" /> Verbatim Event Log Replay
            </span>
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
                <label className="text-zinc-400 text-[11px]">Worker Fleet Count</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={params.worker_count}
                  onChange={(e) => setParams({ ...params, worker_count: parseInt(e.target.value) || 1 })}
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

        {/* Live Invariant Panel & Report Summary (T522, T524) */}
        <div className="lg:col-span-2 space-y-6">
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
