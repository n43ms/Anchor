/**
 * Anchor Chaos Console — Live Invariant Panel
 * Displays real-time and reported invariant assertions:
 * 1. no_duplicate_effects (0 duplicate executions)
 * 2. log_monotonic (contiguous sequence numbers)
 * 3. single_writer_per_epoch (epoch gating & zombie fencing)
 * 4. terminal_reachability (terminal state holds no lease)
 * 5. replay_determinism (log fold replay matching original)
 */

import React from "react";
import { ShieldCheck, CheckCircle2, AlertOctagon, Activity, RefreshCw } from "lucide-react";
import type { ChaosReport } from "@/lib/types";

interface InvariantPanelProps {
  report: ChaosReport | null;
  loading?: boolean;
}

const INVARIANTS = [
  {
    key: "no_duplicate_effects",
    name: "I5: Zero Duplicate Effects",
    description: "Two-phase tool journaling ensures side effects occur at most once under failure.",
  },
  {
    key: "log_monotonic",
    name: "I1: Monotonic Log Contiguity",
    description: "Sequence numbers (run_id, seq) increment contiguously with zero gaps.",
  },
  {
    key: "single_writer_per_epoch",
    name: "I3: Single Writer Per Epoch",
    description: "Stale workers are fenced immediately via SQLSTATE AN001 on epoch mismatch.",
  },
  {
    key: "terminal_reachability",
    name: "I4: Terminal Reachability",
    description: "Terminal states require null owner, null lease, and non-null finished_at.",
  },
  {
    key: "replay_determinism",
    name: "I8: Replay Determinism",
    description: "In-memory state folds event log verbatim without re-invoking external tools.",
  },
] as const;

export function InvariantPanel({ report, loading = false }: InvariantPanelProps) {
  const allPassing = report ? Object.values(report.invariants).every(Boolean) : true;

  return (
    <div className="rounded-2xl border border-white/[0.08] bg-black/40 backdrop-blur-xl p-6 space-y-6">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-white font-mono">
              Invariant Verification Suite
            </h3>
            <p className="text-xs text-zinc-400">
              Database-enforced safety guarantees verified during fault injection
            </p>
          </div>
        </div>

        {report && (
          <div
            className={`flex items-center gap-2 rounded-xl border px-3.5 py-1.5 text-xs font-mono font-semibold ${
              allPassing
                ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                : "border-rose-500/40 bg-rose-500/10 text-rose-400"
            }`}
          >
            {allPassing ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                <span>ALL INVARIANTS HELD (0 VIOLATIONS)</span>
              </>
            ) : (
              <>
                <AlertOctagon className="h-4 w-4 text-rose-400" />
                <span>INVARIANT VIOLATION DETECTED</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Grid of 5 Invariants */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {INVARIANTS.map((inv) => {
          const isVerified = report ? Boolean(report.invariants[inv.key as keyof typeof report.invariants]) : true;

          return (
            <div
              key={inv.key}
              className={`rounded-xl border p-4 transition-all ${
                report
                  ? isVerified
                    ? "border-emerald-500/20 bg-emerald-500/[0.03]"
                    : "border-rose-500/30 bg-rose-500/[0.05]"
                  : "border-white/[0.06] bg-white/[0.02]"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold font-mono text-white">{inv.name}</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 leading-relaxed">{inv.description}</p>
                </div>
                <div className="shrink-0 pt-0.5">
                  {loading ? (
                    <RefreshCw className="h-4 w-4 animate-spin text-zinc-500" />
                  ) : isVerified ? (
                    <span className="inline-flex items-center gap-1 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-400">
                      <CheckCircle2 className="h-3 w-3" /> HELD
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded-md border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-[10px] font-mono font-bold text-rose-400">
                      <AlertOctagon className="h-3 w-3" /> FAILED
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Live Recovery Metrics Card */}
        <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 flex flex-col justify-between space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold font-mono text-white flex items-center gap-1.5">
              <Activity className="h-3.5 w-3.5 text-strand-gold" />
              Recovery Latency (P50 / P95 / P99)
            </span>
            <span className="text-[10px] font-mono text-zinc-500">Post-fault reclaim</span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center font-mono">
            <div className="rounded-lg bg-black/40 border border-white/[0.04] p-2">
              <div className="text-[10px] text-zinc-500">P50</div>
              <div className="text-sm font-bold text-emerald-400">
                {report?.recovery_ms?.p50 ? `${report.recovery_ms.p50}ms` : "—"}
              </div>
            </div>
            <div className="rounded-lg bg-black/40 border border-white/[0.04] p-2">
              <div className="text-[10px] text-zinc-500">P95</div>
              <div className="text-sm font-bold text-strand-gold">
                {report?.recovery_ms?.p95 ? `${report.recovery_ms.p95}ms` : "—"}
              </div>
            </div>
            <div className="rounded-lg bg-black/40 border border-white/[0.04] p-2">
              <div className="text-[10px] text-zinc-500">P99</div>
              <div className="text-sm font-bold text-amber-400">
                {report?.recovery_ms?.p99 ? `${report.recovery_ms.p99}ms` : "—"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
