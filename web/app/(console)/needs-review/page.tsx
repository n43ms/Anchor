/**
 * anchor-spec.md §13.3 — its own page, never only a filter. A failure
 * reachable only by narrowing a list is a failure that goes unnoticed.
 */
"use client";

import { Link } from "react-router-dom";
import { useNeedsReview } from "@/hooks/useNeedsReview";
import { AlertTriangle, ArrowUpRight } from "lucide-react";

export default function NeedsReviewPage() {
  const { data, error } = useNeedsReview();
  const reviewRuns = (data?.items ?? []).filter((run) => run.status === "needs_review");

  return (
    <div data-testid="needs-review-page" className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-white/[0.08] bg-black/40 p-5 backdrop-blur-2xl">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-ui text-base font-bold uppercase tracking-wider text-white">Needs Review Queue</h1>
            <span className="ml-3.5 rounded-full bg-amber-500/10 px-2.5 py-0.5 font-mono text-[10px] text-amber-400 border border-amber-500/30 font-semibold">
              {reviewRuns.length} PENDING
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono">
            Runs halted at the uncertainty window following a worker crash during non-idempotent tool execution
          </p>
        </div>
      </div>

      {error && !data && <p className="text-sm font-mono text-rose-400">could not load review queue</p>}
      {!error && !data && <p className="text-sm font-mono text-zinc-500">loading review queue…</p>}
      {data && reviewRuns.length === 0 && (
        <div className="rounded-2xl border border-white/[0.08] bg-black/40 p-12 text-center text-sm font-mono text-zinc-500 backdrop-blur-2xl">
          no runs currently require operator review
        </div>
      )}

      {reviewRuns.length > 0 && (
        <div className="space-y-3">
          {reviewRuns.map((run) => (
            <Link
              key={run.id}
              to={`/needs-review/${run.id}`}
              className="group block rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 backdrop-blur-2xl transition-all duration-base hover:border-amber-500/60 hover:bg-amber-500/15"
            >
              <div className="flex items-center justify-between">
                <div className="font-mono text-sm font-bold text-white group-hover:text-strand-gold transition-colors flex items-center gap-1.5">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                  <span>{run.display_id ?? `run_${run.id}`}</span>
                  <ArrowUpRight className="h-3.5 w-3.5 text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
                <span className="rounded-full border border-amber-500/40 bg-amber-500/20 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-amber-300">
                  ACTION REQUIRED
                </span>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-4 text-xs font-mono text-zinc-400">
                <span>agent: <strong className="text-white">{run.agent_type}</strong></span>
                <span className="text-zinc-600">·</span>
                <span>step: <strong className="text-white font-mono">{run.current_step_index ?? "—"}</strong></span>
                <span className="text-zinc-600">·</span>
                <span>last owner: <strong className="text-white font-mono">{run.owner_worker_id ?? "—"}</strong></span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
