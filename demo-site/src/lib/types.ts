export type RunStatus = "pending" | "running" | "completed" | "failed" | "cancelled" | "needs_review";

export type EventType =
  | "RUN_SUBMITTED"
  | "RUN_CLAIMED"
  | "REPLAY_COMPLETED"
  | "STEP_STARTED"
  | "LLM_CALLED"
  | "TOOL_INTENT"
  | "TOOL_RESULT"
  | "NONDET_RECORDED"
  | "STEP_COMPLETED"
  | "STEP_SKIPPED_ON_REPLAY"
  | "STEP_FAILED"
  | "LEASE_RENEWED"
  | "WORKER_FENCED"
  | "RUN_COMPLETED"
  | "RUN_FAILED"
  | "RUN_CANCELLED"
  | "RUN_NEEDS_REVIEW";

export type ToolSafety = "retry_safe" | "reconcilable" | "unsafe";

export interface TimelineStep {
  step_index: number;
  name: string;
  status: "done" | "active" | "pending" | "failed" | "skipped_on_replay";
  action_kind: "tool" | "model" | "nondet" | "done";
  started_at: string;
  completed_at: string | null;
  duration_ms?: number | null;
  attempt?: number;
  idempotency_key?: string | null;
  idempotency_key_display?: string | null;
  executed?: boolean;
  skipped_on_replay?: boolean;
}


export interface SegmentLogLine {
  timestamp: string;
  text: string;
  level: "info" | "success" | "warning";
}

export interface TimelineSegment {
  worker_id: string;
  epoch?: number;
  claim_reason?: "initial" | "reclaimed_after_lease_expiry";
  started_at: string;
  ended_at: string | null;
  steps: TimelineStep[];
  log?: SegmentLogLine[];
}

export interface FencingEvent {
  at: string;
  fenced_worker_id: string;
  stale_epoch: number;
  current_epoch: number;
}

export interface RunSummary {
  duplicate_side_effects: number;
  handoff_count: number;
  recovery_seconds: number | null;
  effects_executed?: number;
  replayed_step_count?: number;
}

export interface RunTimeline {
  id: number;
  display_id?: string;
  agent_type: string;
  status: RunStatus;
  started_at: string;
  step_count: number;
  orphaned?: boolean;
  lease_expires_at?: string | null;
  segments: TimelineSegment[];
  fencing_events?: FencingEvent[];
  summary: RunSummary;
}

export interface RunListItem {
  id: number;
  display_id?: string;
  agent_type: string;
  status: RunStatus;
  epoch: number;
  owner_worker_id: string | null;
  lease_expires_at: string | null;
  orphaned?: boolean;
  current_step_index: number | null;
  step_count: number;
  attempts: number;
  priority: number;
  is_demo: boolean;
  cancel_requested_at: string | null;
  created_at: string;
  claimed_at: string | null;
  finished_at: string | null;
  elapsed_ms: number;
  segments: TimelineSegment[];
  summary: RunSummary;
}

export interface RunEvent {
  run_id: number;
  seq: number;
  type: EventType;
  payload: Record<string, unknown>;
  epoch: number;
  worker_id: string;
  step_index: number | null;
  created_at: string;
}

export interface Worker {
  id: string;
  label: string;
  incarnation: number;
  hostname: string;
  pid: number;
  started_at: string;
  last_seen_at: string;
  heartbeat_age_ms?: number;
  stale?: boolean;
  uptime_ms?: number;
  current_run_count: number;
  capacity: number;
  steps_executed?: number;
  code_version: string;
  role: "runner" | "chaos";
}

export interface Health {
  database_reachable: boolean;
  redis_reachable: boolean;
  worker_count: number;
  healthy_worker_count?: number;
  stale_worker_count?: number;
  pending_run_count?: number;
  running_run_count?: number;
  global_concurrency_cap?: number;
  oldest_pending_age_ms?: number | null;
  deployment_mode: "demonstration" | "local";
  active_profile?: string;
  code_version?: string;
  schema_revision?: string;
  degraded?: boolean;
}

export interface ChaosReport {
  id: number;
  chaos_run_id: number;
  started_at: string;
  finished_at: string;
  duration_seconds: number;
  worker_count: number;
  runs_submitted: number;
  runs_completed: number;
  kills_injected: number;
  duplicate_effect_count: number;
  stranded_run_count: number;
  recovery_ms_p50: number;
  recovery_ms_p95: number;
  recovery_ms_p99: number;
  recovery_ms_max: number;
  mean_steps_replayed: number;
  mean_replay_ms: number;
  throughput_steps_per_sec: number;
  fencing_events_count: number;
  uncertainty_resolutions: Record<string, number>;
  dead_letter_count: number;
  config_profile: string;
  lease_duration_ms: number;
  renewal_interval_ms: number;
  violations: unknown[];
}

export interface ToolDescriptor {
  name: string;
  safety: ToolSafety;
  naturally_idempotent?: boolean;
  provider_accepts_key?: boolean;
  has_reconcile_fn: boolean;
  default_policy: ToolSafety;
  declaration_hash: string;
  executable: boolean;
  description?: string;
}
