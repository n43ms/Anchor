import type { RunTimeline } from "@/lib/types";

/**
 * anchor-spec.md §24.5 — currently orphaned: no segment has ended_at ===
 * null. The state the component is in during the most important two
 * seconds of the demo, and the easiest to forget.
 */
export const orphanedMock: RunTimeline = {
  id: 92,
  display_id: "run_92",
  agent_type: "refund-agent",
  status: "running",
  started_at: "2026-08-18T15:00:00.000Z",
  step_count: 5,
  lease_expires_at: "2026-08-18T15:00:34.000Z",
  segments: [
    {
      worker_id: "worker-a#4",
      epoch: 5,
      claim_reason: "initial",
      started_at: "2026-08-18T15:00:00.000Z",
      ended_at: "2026-08-18T15:00:30.000Z",
      steps: [
        { step_index: 0, name: "read ticket", status: "done", action_kind: "tool", started_at: "2026-08-18T15:00:00.000Z", completed_at: "2026-08-18T15:00:05.000Z", executed: true },
        { step_index: 1, name: "check order", status: "done", action_kind: "tool", started_at: "2026-08-18T15:00:05.000Z", completed_at: "2026-08-18T15:00:20.000Z", executed: true },
        { step_index: 2, name: "decide", status: "done", action_kind: "model", started_at: "2026-08-18T15:00:20.000Z", completed_at: "2026-08-18T15:00:30.000Z", executed: true },
      ],
      log: [{ timestamp: "15:00:30", text: "lease expired — no renewal received", level: "warning" }],
    },
  ],
  fencing_events: [],
  summary: { duplicate_side_effects: 0, handoff_count: 0, recovery_seconds: null },
};
