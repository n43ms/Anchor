import type { RunTimeline } from "@/lib/types";

/**
 * anchor-spec.md §24.5 — the refund-agent example: 5 steps, 2 workers,
 * 1 handoff, 0 duplicate side effects, 3.1s recovery. Must render
 * meaningfully with no live backend.
 */
export const referenceMock: RunTimeline = {
  id: 47,
  display_id: "run_47",
  agent_type: "refund-agent",
  status: "running",
  started_at: "2026-08-18T14:02:11.000Z",
  step_count: 5,
  segments: [
    {
      worker_id: "worker-a#3",
      epoch: 5,
      claim_reason: "initial",
      started_at: "2026-08-18T14:02:11.000Z",
      ended_at: "2026-08-18T14:02:15.000Z",
      steps: [
        {
          step_index: 0,
          name: "read ticket",
          status: "done",
          action_kind: "tool",
          started_at: "2026-08-18T14:02:11.000Z",
          completed_at: "2026-08-18T14:02:12.000Z",
          duration_ms: 900,
          executed: true,
        },
        {
          step_index: 1,
          name: "check order",
          status: "done",
          action_kind: "tool",
          started_at: "2026-08-18T14:02:12.000Z",
          completed_at: "2026-08-18T14:02:14.000Z",
          duration_ms: 1800,
          idempotency_key_display: "r47:s2:c1e",
          executed: true,
        },
        {
          step_index: 2,
          name: "decide",
          status: "done",
          action_kind: "model",
          started_at: "2026-08-18T14:02:14.000Z",
          completed_at: "2026-08-18T14:02:15.000Z",
          duration_ms: 700,
          executed: true,
        },
      ],
      log: [
        { timestamp: "14:02:11", text: "run_claimed worker-a#3 epoch=5", level: "info" },
        { timestamp: "14:02:13", text: "tool_intent fetch_order key=r47:s2:c1e", level: "info" },
        { timestamp: "14:02:14", text: "tool_result fetch_order ok", level: "success" },
      ],
    },
    {
      worker_id: "worker-c#1",
      epoch: 6,
      claim_reason: "reclaimed_after_lease_expiry",
      started_at: "2026-08-18T14:02:17.000Z",
      ended_at: null,
      steps: [
        {
          step_index: 3,
          name: "issue refund",
          status: "active",
          action_kind: "tool",
          started_at: "2026-08-18T14:02:17.000Z",
          completed_at: null,
          idempotency_key_display: "r47:s4:9a1",
          executed: true,
        },
        {
          step_index: 4,
          name: "notify customer",
          status: "pending",
          action_kind: "tool",
          started_at: "2026-08-18T14:02:18.000Z",
          completed_at: null,
        },
      ],
      log: [
        { timestamp: "14:02:17", text: "run_claimed worker-c#1 epoch=6 reclaimed", level: "info" },
        { timestamp: "14:02:17", text: "replayed 3 steps from log", level: "info" },
        { timestamp: "14:02:18", text: "tool_intent send_refund key=r47:s4:9a1", level: "info" },
      ],
    },
  ],
  fencing_events: [],
  summary: {
    duplicate_side_effects: 0,
    handoff_count: 1,
    recovery_seconds: 3.1,
  },
};
