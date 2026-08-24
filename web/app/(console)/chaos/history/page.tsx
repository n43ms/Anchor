/**
 * Anchor Operator Console — Chaos History Page
 * Spec T523: Lists every past chaos harness run and its final invariant report, retained permanently.
 */

import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { History, ShieldCheck, CheckCircle2, AlertOctagon, Flame, ArrowLeft, RefreshCw, FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { ChaosReport, ChaosRun } from "@/lib/types";
import { ReportCard } from "@/components/chaos/ReportCard";

export default function ChaosHistoryPage() {
  const [runs, setRuns] = useState<Array<ChaosRun & { report: ChaosReport | null }>>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReport, setSelectedReport] = useState<ChaosReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.listChaosRuns();
      setRuns(res.items);
    } catch (err) {
      console.error("Failed to load chaos history", err);
      setError(err instanceof Error ? err.message : "Failed to load chaos history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link to="/chaos" className="text-xs font-mono text-zinc-400 hover:text-white flex items-center gap-1">
              <ArrowLeft className="h-3.5 w-3.5" /> Back to Chaos Launchpad
            </Link>
          </div>
          <h1 className="text-2xl font-bold text-white font-mono flex items-center gap-2">
            <History className="h-6 w-6 text-strand-gold" />
            <span>Chaos Harness Run History</span>
          </h1>
          <p className="text-xs text-zinc-400 font-mono">
            Permanent ledger of fault injection experiments and invariant proof reports
          </p>
        </div>

        <button
          onClick={fetchHistory}
          disabled={loading}
          className="flex items-center gap-2 rounded-xl border border-white/[0.1] bg-white/[0.04] px-4 py-2 text-xs font-mono text-zinc-300 hover:bg-white/[0.08] transition-all"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh History</span>
        </button>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/40 bg-rose-500/10 p-4 text-xs font-mono text-rose-300">
          {error}
        </div>
      )}

      {/* Main Grid: Run List Table + Selected Report Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Table List */}
        <div className="lg:col-span-1 space-y-4">
          <div className="rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-xl p-4 space-y-3">
            <div className="text-xs font-bold font-mono text-white uppercase tracking-wider px-2">
              Historical Experiments ({runs.length})
            </div>

            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1 scrollbar-thin">
              {runs.length === 0 && !loading && (
                <div className="p-8 text-center text-xs font-mono text-zinc-500">
                  No chaos harness runs recorded yet.
                </div>
              )}

              {runs.map((item) => {
                const isSelected = selectedReport?.chaos_run_id === item.id;
                const allPassing = item.report ? Object.values(item.report.invariants).every(Boolean) : false;

                return (
                  <button
                    key={item.id}
                    onClick={() => item.report && setSelectedReport(item.report)}
                    className={`w-full text-left rounded-xl border p-3.5 font-mono text-xs transition-all space-y-2 ${
                      isSelected
                        ? "border-strand-gold bg-strand-gold/10"
                        : "border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white">Run #{item.id}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                          item.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : item.status === "running"
                            ? "bg-sky-500/10 text-sky-400"
                            : "bg-rose-500/10 text-rose-400"
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>

                    <div className="text-[11px] text-zinc-400 flex items-center justify-between">
                      <span>{new Date(item.started_at).toLocaleString()}</span>
                      <span>{item.params.duration_seconds}s</span>
                    </div>

                    {item.report && (
                      <div className="flex items-center justify-between text-[10px] border-t border-white/[0.06] pt-2">
                        <span className="text-zinc-500">
                          {item.report.kills_injected} Kills • {item.report.runs_total} Runs
                        </span>
                        {allPassing ? (
                          <span className="text-emerald-400 font-bold flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3" /> PASSED
                          </span>
                        ) : (
                          <span className="text-rose-400 font-bold flex items-center gap-1">
                            <AlertOctagon className="h-3 w-3" /> FAILED
                          </span>
                        )}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Report Inspection Panel */}
        <div className="lg:col-span-2 space-y-4">
          {selectedReport ? (
            <ReportCard report={selectedReport} />
          ) : (
            <div className="rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-xl p-12 text-center font-mono text-xs text-zinc-500 space-y-2">
              <FileText className="h-8 w-8 mx-auto text-zinc-600" />
              <div>Select a chaos run from the left panel to inspect its invariant report.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
