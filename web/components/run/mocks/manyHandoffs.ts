import type { RunTimeline, TimelineSegment } from "@/lib/types";

/** anchor-spec.md §22.3, §24.7 — beyond three distinct labels, color by
 * emphasis (current owner in slot 1, all prior owners muted) rather than
 * by extending the validated three-hue set. */
const labels = ["worker-a", "worker-b", "worker-c", "worker-d", "worker-e"];

function segment(index: number, workerLabel: string, isLast: boolean): TimelineSegment {
  const startMinute = index * 2;
  return {
    worker_id: `${workerLabel}#${index + 1}`,
    epoch: index + 1,
    claim_reason: index === 0 ? "initial" : "reclaimed_after_lease_expiry",
    started_at: `2026-08-18T09:0${startMinute}:00.000Z`,
    ended_at: isLast ? null : `2026-08-18T09:0${startMinute + 2}:00.000Z`,
    steps: [
      {
        step_index: index,
        name: `step ${index + 1}`,
        status: isLast ? "active" : "done",
        action_kind: "tool",
        started_at: `2026-08-18T09:0${startMinute}:00.000Z`,
        completed_at: isLast ? null : `2026-08-18T09:0${startMinute + 1}:00.000Z`,
        executed: true,
      },
    ],
    log: [{ timestamp: `09:0${startMinute}`, text: `run_claimed ${workerLabel}#${index + 1} epoch=${index + 1}`, level: "info" }],
  };
}

export const manyHandoffsMock: RunTimeline = {
  id: 88,
  display_id: "run_88",
  agent_type: "long-poll-agent",
  status: "running",
  started_at: "2026-08-18T09:00:00.000Z",
  step_count: labels.length,
  segments: labels.map((label, i) => segment(i, label, i === labels.length - 1)),
  fencing_events: labels.slice(0, -1).map((label, i) => ({
    at: `2026-08-18T09:0${i * 2 + 2}:00.000Z`,
    fenced_worker_id: `${label}#${i + 1}`,
    stale_epoch: i + 1,
    current_epoch: i + 2,
  })),
  summary: { duplicate_side_effects: 0, handoff_count: labels.length - 1, recovery_seconds: 4.6 },
};
