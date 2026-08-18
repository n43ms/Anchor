import type { RunTimeline } from "@/lib/types";

/** anchor-spec.md §24.2 — footer suppression: recovery_seconds must not render as "0.0s". */
export const zeroHandoffsMock: RunTimeline = {
  id: 12,
  display_id: "run_12",
  agent_type: "search-summarize-notify",
  status: "completed",
  started_at: "2026-08-18T10:00:00.000Z",
  step_count: 3,
  segments: [
    {
      worker_id: "worker-b#1",
      epoch: 1,
      claim_reason: "initial",
      started_at: "2026-08-18T10:00:00.000Z",
      ended_at: "2026-08-18T10:00:09.000Z",
      steps: [
        { step_index: 0, name: "search", status: "done", action_kind: "tool", started_at: "2026-08-18T10:00:00.000Z", completed_at: "2026-08-18T10:00:03.000Z", duration_ms: 3000, executed: true },
        { step_index: 1, name: "summarize", status: "done", action_kind: "model", started_at: "2026-08-18T10:00:03.000Z", completed_at: "2026-08-18T10:00:06.000Z", duration_ms: 3000, executed: true },
        { step_index: 2, name: "notify", status: "done", action_kind: "tool", started_at: "2026-08-18T10:00:06.000Z", completed_at: "2026-08-18T10:00:09.000Z", duration_ms: 3000, executed: true },
      ],
      log: [{ timestamp: "10:00:00", text: "run_claimed worker-b#1 epoch=1", level: "info" }],
    },
  ],
  fencing_events: [],
  summary: { duplicate_side_effects: 0, handoff_count: 0, recovery_seconds: null },
};
