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
    <div className="rounded-lg border border-gridline bg-surface-panel p-5" data-testid="run-detail" data-run-status={run.status}>
      <header className="flex items-start justify-between">
        <div>
          <h2 className="font-ui text-base text-ink-primary">
            {run.display_id ?? `run_${run.id}`} · {run.agent_type}
          </h2>
          <p className="mt-1 text-xs text-ink-secondary">
            started {startedAgoSeconds}s ago · {run.step_count} steps
          </p>
        </div>
        <StatusPill status={run.status} />
      </header>

      <div className="mt-5 space-y-1">
        {run.segments.map((segment, i) => {
          const hueSlot = workerHueSlot(segment.worker_id, claimOrder, segment.ended_at === null);
          return (
            <div key={`${segment.worker_id}-${segment.started_at}`}>
              {i > 0 && <HandoffDivider workerId={run.segments[i - 1]!.worker_id} />}
              <div className="flex items-start gap-3">
                <span
                  className="w-24 shrink-0 pt-0.5 font-data text-xs font-bold"
                  style={{ color: hueSlot === "muted" ? "var(--ink-muted)" : `var(--worker-${hueSlot})` }}
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

      <div className="mt-4 border-t border-gridline pt-3">
        <div className="mb-2 text-xs text-ink-muted">thread view</div>
        <RunThread segments={run.segments} terminal={isTerminal} />
      </div>

      <footer className="mt-4 flex items-center justify-between border-t border-gridline pt-3">
        <p className="text-xs text-ink-muted" data-testid="run-detail-footer">
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
          className="rounded bg-status-critical/15 px-3 py-1.5 text-xs text-status-critical transition-colors duration-fast hover:bg-status-critical/25 disabled:cursor-not-allowed disabled:opacity-40"
        >
          kill {killTargetWorkerId ?? "—"}
        </button>
      </footer>
    </div>
  );
}

function StepLabels({ steps }: { steps: RunTimeline["segments"][number]["steps"] }) {
  return (
    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
      {steps.map((step) => (
        <span
          key={step.step_index}
          className={step.status === "active" ? "font-bold text-ink-primary" : "text-ink-secondary"}
          data-step-status={step.status}
        >
          {step.name}
          {step.status === "active" ? "…" : ""}
        </span>
      ))}
    </div>
  );
}
