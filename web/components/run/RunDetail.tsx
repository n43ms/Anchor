/**
 * anchor-spec.md Addendum B (§24), contracts/component-contract.md.
 * No data fetching, no WebSocket, no API call — kill is raised to the
 * parent, which owns POST /api/workers/{id}/kill and its error handling.
 */
"use client";

import { useMemo } from "react";
import type { RunTimeline } from "@/lib/types";
import { workerHueSlot } from "@/lib/hues";
import { StatusPill } from "@/components/primitives/StatusPill";
import { WorkerBar } from "./WorkerBar";
import { HandoffDivider } from "./HandoffDivider";
import { SegmentLog } from "./SegmentLog";
import { OrphanedGap } from "./OrphanedGap";
import { RunThread } from "./RunThread";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

export function RunDetail({
  run,
  onKill,
  now = new Date(),
}: {
  run: RunTimeline;
  onKill: (workerId: string) => void;
  now?: Date;
}) {
  const claimOrder = useMemo(() => run.segments.map((s) => s.worker_id), [run.segments]);
  const currentSegment = run.segments.find((s) => s.ended_at === null) ?? null;
  const isTerminal = TERMINAL_STATUSES.has(run.status);
  const startedAgoSeconds = Math.max(0, Math.round((now.getTime() - new Date(run.started_at).getTime()) / 1000));

  const killDisabledReason = isTerminal
    ? `run is ${run.status}`
    : !currentSegment
      ? "no current owner — run is orphaned"
      : null;
  const killTargetWorkerId = currentSegment?.worker_id ?? null;

  return (
    <div
      className="rounded-2xl border border-white/[0.08] bg-black/40 p-6 backdrop-blur-2xl"
      data-testid="run-detail"
      data-run-status={run.status}
    >
      <header className="flex items-start justify-between">
        <div>
          <h2 className="font-ui text-base font-bold text-white">
            {run.display_id ?? `run_${run.id}`} · {run.agent_type}
          </h2>
          <p className="mt-1 text-xs text-zinc-400 font-mono">
            started {startedAgoSeconds}s ago · {run.step_count} steps
          </p>
        </div>
        <StatusPill status={run.status} />
      </header>

      <div className="mt-5 space-y-2">
        {run.segments.map((segment, i) => {
          const hueSlot = workerHueSlot(segment.worker_id, claimOrder, segment.ended_at === null);
          return (
            <div key={`${segment.worker_id}-${segment.started_at}`}>
              {i > 0 && <HandoffDivider workerId={run.segments[i - 1]!.worker_id} />}
              <div className="flex items-start gap-3">
                <span
                  className="w-24 shrink-0 pt-0.5 font-mono text-xs font-bold text-indigo-300 drop-shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                >
                  {segment.worker_id}
                </span>
                <div className="min-w-0 flex-1">
                  <WorkerBar segment={segment} hueSlot={hueSlot} />
                  <StepLabels steps={segment.steps} />
                  <SegmentLog lines={segment.log ?? []} />
                </div>
              </div>
            </div>
          );
        })}

        {!currentSegment && !isTerminal && <OrphanedGap leaseExpiresAt={run.lease_expires_at ?? null} now={now} />}
      </div>

      {/* Runtime Execution Thread Centerpiece */}
      <div className="mt-5 rounded-2xl border border-white/[0.06] bg-black/50 p-4 backdrop-blur-xl">
        <div className="mb-2.5 flex items-center justify-between font-mono text-[10px] uppercase tracking-widest text-zinc-400">
          <span className="flex items-center gap-1.5 font-bold text-strand-gold">
            <span className="h-1.5 w-1.5 rounded-full bg-strand-gold shadow-glow-gold" />
            Runtime Thread
          </span>
          <span className="text-zinc-500">{run.step_count} steps</span>
        </div>
        <RunThread segments={run.segments} terminal={isTerminal} />
      </div>

      <footer className="mt-4 flex items-center justify-between border-t border-white/[0.06] pt-3.5">
        <p className="text-xs text-zinc-400 font-mono" data-testid="run-detail-footer">
          {run.summary.duplicate_side_effects} duplicate side effects · {run.summary.handoff_count} handoff
          {run.summary.handoff_count === 1 ? "" : "s"}
          {run.summary.handoff_count > 0 && run.summary.recovery_seconds !== null
            ? ` · ${run.summary.recovery_seconds.toFixed(1)}s recovery`
            : ""}
        </p>
        <button
          type="button"
          disabled={killDisabledReason !== null}
          title={killDisabledReason ?? undefined}
          onClick={() => killTargetWorkerId && onKill(killTargetWorkerId)}
          className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3.5 py-1.5 text-xs font-mono font-medium text-rose-400 transition-all hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-40"
        >
          kill {killTargetWorkerId ?? "—"}
        </button>
      </footer>
    </div>
  );
}

function StepLabels({ steps }: { steps: RunTimeline["segments"][number]["steps"] }) {
  return (
    <div className="mt-2.5 flex flex-wrap gap-x-2 gap-y-1.5 text-xs">
      {steps.map((step) => {
        const isModel = step.action_kind === "model";
        const isTool = step.action_kind === "tool";
        const isReplay = step.status === "skipped_on_replay";
        const stepNum = step.step_index + 1;

        return (
          <span
            key={step.step_index}
            className={`inline-flex items-center gap-1.5 rounded-lg px-2 py-0.5 font-mono text-[10px] transition-colors ${
              step.status === "active"
                ? isTool
                  ? "border border-amber-500/50 bg-amber-500/20 text-amber-200 font-bold shadow-sm"
                  : "border border-indigo-500/50 bg-indigo-500/20 text-indigo-200 font-bold shadow-sm"
                : isTool
                  ? "border border-amber-500/30 bg-amber-500/10 text-amber-300/90"
                  : isReplay
                    ? "border border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                    : "border border-indigo-500/30 bg-indigo-500/10 text-indigo-300/90"
            }`}
            data-step-status={step.status}
          >
            {/* Numbered Legend Key Index linking directly to thread marker */}
            <span
              className={`flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold ${
                isTool
                  ? "bg-amber-500/25 text-amber-200 border border-amber-500/40"
                  : isReplay
                    ? "bg-emerald-500/25 text-emerald-200 border border-emerald-500/40"
                    : "bg-indigo-500/25 text-indigo-200 border border-indigo-500/40"
              }`}
            >
              {stepNum}
            </span>
            <span className="font-medium">{step.name}</span>
            {step.status === "active" ? "…" : ""}
          </span>
        );
      })}
    </div>
  );
}
