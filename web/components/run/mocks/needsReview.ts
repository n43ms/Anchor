import type { RunTimeline } from "@/lib/types";

/** anchor-spec.md §21.5 third preset — a crash inside the uncertainty window. */
export const needsReviewMock: RunTimeline = {
  id: 203,
  display_id: "run_203",
  agent_type: "refund-agent",
  status: "needs_review",
  started_at: "2026-08-18T11:00:00.000Z",
  step_count: 4,
  segments: [
    {
      worker_id: "worker-a#2",
      epoch: 2,
      claim_reason: "initial",
      started_at: "2026-08-18T11:00:00.000Z",
      ended_at: null,
      steps: [
        { step_index: 0, name: "read ticket", status: "done", action_kind: "tool", started_at: "2026-08-18T11:00:00.000Z", completed_at: "2026-08-18T11:00:01.000Z", executed: true },
        { step_index: 1, name: "issue refund", status: "failed", action_kind: "tool", started_at: "2026-08-18T11:00:01.000Z", completed_at: null, idempotency_key_display: "r203:s1:7ba", executed: true },
      ],
      log: [{ timestamp: "11:00:01", text: "tool_intent send_refund key=r203:s1:7ba", level: "info" }, { timestamp: "11:00:02", text: "crash before tool_result — uncertain", level: "warning" }],
    },
  ],
  fencing_events: [],
  needs_review: {
    step_index: 1,
    tool_name: "send_refund",
    idempotency_key: "r203:s1:7ba",
    declared_policy: "unsafe",
    available_resolutions: ["mark_executed", "mark_not_executed"],
  },
  summary: { duplicate_side_effects: 0, handoff_count: 0, recovery_seconds: null },
};
