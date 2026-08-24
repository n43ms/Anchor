/**
 * Anchor Chaos Console — ReportCard
 * Displays the full proof of correctness for a chaos harness run:
 * Config profile, lease duration, worker count, total faults, and invariant assertion status.
 */

import React from "react";
import { CheckCircle2, AlertOctagon, Flame, Zap, Shield, Clock, Layers } from "lucide-react";
import type { ChaosReport, ChaosRun } from "@/lib/types";

interface ReportCardProps {
  run?: ChaosRun;
  report: ChaosReport;
}

export function ReportCard({ run, report }: ReportCardProps) {
  const allPassing = Object.values(report.invariants).every(Boolean);

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 font-mono text-xs text-zinc-400">
            <span>Chaos Harness Report #{report.chaos_run_id}</span>
            <span>•</span>
            <span className="text-zinc-500">{new Date(report.created_at).toLocaleString()}</span>
          </div>
          <h3 className="text-lg font-bold text-white font-mono flex items-center gap-2">
            <span>Fault Injection Verification Result</span>
          </h3>
        </div>

        <div
          className={`flex items-center gap-2 rounded-xl border px-4 py-2 text-xs font-mono font-bold ${
            allPassing
              ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400 shadow-glow-emerald"
              : "border-rose-500/40 bg-rose-500/10 text-rose-400"
          }`}
        >
          {allPassing ? (
            <>
              <CheckCircle2 className="h-4 w-4" />
              <span>0 INVARIANT VIOLATIONS (PASSED)</span>
            </>
          ) : (
            <>
              <AlertOctagon className="h-4 w-4" />
              <span>INVARIANT VIOLATION DETECTED</span>
            </>
          )}
        </div>
      </div>

      {/* Profile & Lease Configuration Strip (FR-082) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono text-xs">
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 space-y-1">
          <div className="text-[10px] text-zinc-500 uppercase tracking-wider flex items-center gap-1">
            <Shield className="h-3 w-3 text-strand-gold" /> Config Profile
          </div>
          <div className="text-sm font-bold text-white uppercase">{report.config_profile}</div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 space-y-1">
          <div className="text-[10px] text-zinc-500 uppercase tracking-wider flex items-center gap-1">
            <Clock className="h-3 w-3 text-sky-400" /> Lease Duration
          </div>
          <div className="text-sm font-bold text-white">{report.lease_duration_ms}ms</div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 space-y-1">
          <div className="text-[10px] text-zinc-500 uppercase tracking-wider flex items-center gap-1">
            <Layers className="h-3 w-3 text-indigo-400" /> Target Runs / Steps
          </div>
          <div className="text-sm font-bold text-white">
            {report.runs_total} / {report.steps_total}
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-3 space-y-1">
          <div className="text-[10px] text-zinc-500 uppercase tracking-wider flex items-center gap-1">
            <Flame className="h-3 w-3 text-rose-400" /> Injected Faults
          </div>
          <div className="text-sm font-bold text-rose-400">{report.kills_injected} Kills</div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03] p-4 space-y-1 text-center">
          <div className="text-[10px] text-emerald-400 uppercase tracking-wider">Duplicate Side Effects</div>
          <div className="text-2xl font-bold text-emerald-400">{report.duplicate_effect_count}</div>
          <div className="text-[10px] text-zinc-500">Guaranteed 0 by Two-Phase Journal (I5)</div>
        </div>

        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/[0.03] p-4 space-y-1 text-center">
          <div className="text-[10px] text-emerald-400 uppercase tracking-wider">Stranded Runs</div>
          <div className="text-2xl font-bold text-emerald-400">{report.stranded_run_count}</div>
          <div className="text-[10px] text-zinc-500">Guaranteed 0 by Terminal Check (I4)</div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-1 text-center">
          <div className="text-[10px] text-zinc-400 uppercase tracking-wider">Zombie Fencing Events</div>
          <div className="text-2xl font-bold text-amber-400">{report.fencing_events}</div>
          <div className="text-[10px] text-zinc-500">SQLSTATE AN001 Epoch Rejections (I3)</div>
        </div>
      </div>

      {/* Invariants Status Checklist */}
      <div className="rounded-xl border border-white/[0.06] bg-black/50 p-4 space-y-3 font-mono text-xs">
        <div className="text-xs font-bold uppercase tracking-wider text-zinc-400">Verified Invariants Summary</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
          {Object.entries(report.invariants).map(([key, val]) => (
            <div key={key} className="flex items-center justify-between border-b border-white/[0.04] py-1.5 px-2">
              <span className="text-zinc-300 capitalize">{key.replace(/_/g, " ")}</span>
              {val ? (
                <span className="text-emerald-400 font-bold flex items-center gap-1">
                  <CheckCircle2 className="h-3 w-3" /> VERIFIED
                </span>
              ) : (
                <span className="text-rose-400 font-bold flex items-center gap-1">
                  <AlertOctagon className="h-3 w-3" /> VIOLATED
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
