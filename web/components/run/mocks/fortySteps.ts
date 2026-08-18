import type { RunTimeline, TimelineStep } from "@/lib/types";

/** anchor-spec.md §24.5 — label collision and the rail fallback at scale. */
function step(i: number): TimelineStep {
  return {
    step_index: i,
    name: `step ${i + 1} of the long chain`,
    status: i < 38 ? "done" : i === 38 ? "active" : "pending",
    action_kind: i % 5 === 0 ? "model" : "tool",
    started_at: new Date(2026, 7, 18, 8, 0, i).toISOString(),
    completed_at: i < 38 ? new Date(2026, 7, 18, 8, 0, i + 1).toISOString() : null,
    duration_ms: 800,
    executed: true,
  };
}

const allSteps = Array.from({ length: 40 }, (_, i) => step(i));

export const fortyStepsMock: RunTimeline = {
  id: 501,
  display_id: "run_501",
  agent_type: "long-chain-agent",
  status: "running",
  started_at: "2026-08-18T08:00:00.000Z",
  step_count: 40,
  segments: [
    { worker_id: "worker-a#1", epoch: 1, claim_reason: "initial", started_at: "2026-08-18T08:00:00.000Z", ended_at: "2026-08-18T08:00:25.000Z", steps: allSteps.slice(0, 25), log: [] },
    { worker_id: "worker-b#1", epoch: 2, claim_reason: "reclaimed_after_lease_expiry", started_at: "2026-08-18T08:00:27.000Z", ended_at: null, steps: allSteps.slice(25).map((s) => ({ ...s, status: s.step_index === 38 ? "active" : s.step_index < 38 ? "skipped_on_replay" : "pending", executed: s.step_index < 38 })), log: [{ timestamp: "08:00:27", text: "replayed 13 steps from log", level: "info" }] },
  ],
  fencing_events: [{ at: "2026-08-18T08:00:26.000Z", fenced_worker_id: "worker-a#1", stale_epoch: 1, current_epoch: 2 }],
  summary: { duplicate_side_effects: 0, handoff_count: 1, recovery_seconds: 3.4 },
};
