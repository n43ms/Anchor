/**
 * Types mirror specs/001-anchor-durable-execution-runtime/contracts/openapi.yaml exactly.
 * This file has no logic — it is the typed shape of the wire contract, so a drift between
 * the API and the console shows up as a compile error rather than a runtime surprise.
 */

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

export interface ApiError {
  error: string;
  message: string;
  detail?: Record<string, unknown>;
}

export interface RunSubmission {
  agent_type: string;
  input?: Record<string, unknown>;
  client_request_key?: string;
  priority?: number;
  is_demo?: boolean;
}

export interface Run {
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
}

export interface RunSummary {
  duplicate_side_effects: number;
  handoff_count: number;
  recovery_seconds: number | null;
  effects_executed?: number;
  replayed_step_count?: number;
}

export type TimelineStepStatus = "done" | "active" | "pending" | "failed" | "skipped_on_replay";
export type ActionKind = "tool" | "model" | "nondet" | "done";

export interface TimelineStep {
  step_index: number;
  name: string;
  status: TimelineStepStatus;
  action_kind: ActionKind;
  started_at: string;
  completed_at: string | null;
  duration_ms?: number | null;
  attempt?: number;
  idempotency_key?: string | null;
  idempotency_key_display?: string | null;
  /** false ⇒ read back from the log, not re-executed. Rendered as fill weight, never hue. */
  executed?: boolean;
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
  /** null identifies the current owner. Trusted, never re-derived. */
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

export interface NeedsReview {
  step_index: number;
  tool_name: string;
  idempotency_key: string;
  declared_policy: ToolSafety;
  available_resolutions: Array<"mark_executed" | "mark_not_executed" | "retry">;
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
  needs_review?: NeedsReview | null;
  summary: RunSummary;
}

export interface RunListItem extends Run {
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

export interface ToolDescriptor {
  name: string;
  safety: ToolSafety;
  naturally_idempotent?: boolean;
  provider_accepts_key?: boolean;
  has_reconcile_fn: boolean;
  default_policy: ToolSafety;
  declaration_hash: string;
  declared_by_version?: string;
  executable: boolean;
  conflict?: { detected_at: string; versions: string[] } | null;
  description?: string;
  last_used_at: string | null;
}

export interface AgentDescriptor {
  agent_type: string;
  description?: string;
  contract_version: string;
  expected_step_count: number | null;
  tools_used: string[];
  stubbed_model?: boolean;
}

export interface HistogramBin {
  lower_ms: number;
  upper_ms: number;
  count: number;
}

export interface Histogram {
  bins: HistogramBin[];
  p50: number | null;
  p95: number | null;
  p99: number | null;
}

export interface Metrics {
  window: string;
  duplicate_side_effects: number;
  stranded_runs?: number;
  runs_total?: number;
  steps_total?: number;
  steps_per_second?: number;
  steps_per_second_by_worker?: Record<string, number>;
  run_state_distribution: Array<{ bucket: string; counts: Record<string, number> }>;
  recovery_ms_histogram?: Histogram;
  lease_renewal_ms_histogram?: Histogram;
  replay_steps_mean?: number;
  replay_ms_mean?: number;
  fencing_events_series?: Array<{ bucket: string; count: number }>;
  uncertainty_by_policy?: Record<string, number>;
  dead_letter_reasons?: Array<{ error_type: string; count: number }>;
  throughput_by_worker_count?: Array<{ worker_count: number; steps_per_second: number }>;
  active_profile?: string;
  lease_duration_ms?: number;
}

export interface RuntimeConfigValues {
  renewal_interval_ms: number;
  lease_duration_ms: number;
  margin_ms: number;
  step_timeout_ms: number;
  max_attempts_per_step: number;
  backoff_base_ms?: number;
  backoff_factor?: number;
  per_worker_concurrency: number;
  global_concurrency_cap: number;
  reclaim_poll_interval_ms: number;
}

export interface RuntimeConfig {
  version: number;
  active_profile: "demo" | "production";
  editable: boolean;
  values: RuntimeConfigValues;
}

export interface ChaosParams {
  worker_count: number;
  run_count?: number;
  duration_seconds: number;
  kill_rate_per_minute?: number;
  latency_injection_ms?: number;
  stall_injection_rate?: number;
  tool_failure_rate?: number;
  uncertainty_crash_rate?: number;
}

export interface ChaosRun {
  id: number;
  status: "pending" | "running" | "completed" | "failed" | "abandoned";
  params: ChaosParams;
  deployment_mode: "demonstration" | "local";
  config_profile: "demo" | "production";
  lease_duration_ms: number;
  renewal_interval_ms: number;
  started_at: string;
  ended_at: string | null;
}

export interface ChaosReport {
  chaos_run_id: number;
  invariants: {
    no_duplicate_effects: boolean;
    log_monotonic: boolean;
    single_writer_per_epoch: boolean;
    terminal_reachability: boolean;
    replay_determinism: boolean;
  };
  violations: Array<Record<string, unknown>>;
  duplicate_effect_count: number;
  stranded_run_count: number;
  kills_injected: number;
  runs_total: number;
  steps_total: number;
  recovery_ms: { p50: number; p95: number; p99: number; max: number } | null;
  replay_steps_mean: number | null;
  replay_ms_mean: number | null;
  steps_per_second: number | null;
  fencing_events: number;
  uncertainty_entries: Record<string, number>;
  dead_letter_count: number;
  duration_seconds: number;
  config_profile: string;
  lease_duration_ms: number;
  created_at: string;
}

/** WS envelope, contracts/websocket.md. */
export interface WsFrame<T = unknown> {
  channel: string;
  kind: "hello" | "event" | "snapshot" | "fleet" | "lag" | "bye";
  seq?: number;
  sent_at: string;
  data: T;
}

/** contracts/openapi.yaml `ValidationReport` — the authoring surface's
 * static-check result (plan.md P9.1, Phase 9). `findings` is empty on a
 * clean draft, but `unchecked` is never empty: it is the four
 * pre-registration judgements no static check can make, carried on every
 * report so a console never renders `valid: true` as "this agent is
 * correct" (FR-134, D-59). */
export type ValidationCheck =
  | "determinism_imports"
  | "return_shape"
  | "module_level_mutable_state"
  | "unregistered_tool"
  | "missing_safety_declaration"
  | "unbounded_self_recursion";

export interface ValidationFinding {
  check: ValidationCheck;
  line: number;
  column: number | null;
  message: string;
  severity?: "error" | "warning";
}

export interface ValidationReport {
  valid: boolean;
  findings: ValidationFinding[];
  unchecked: string[];
}
