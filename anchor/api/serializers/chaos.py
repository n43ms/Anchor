"""`contracts/openapi.yaml` `ChaosRun` / `ChaosReport` (plan.md P8.6)."""

from __future__ import annotations

import json
from typing import Any

import asyncpg
from pydantic import BaseModel

CHAOS_RUN_COLUMNS = (
    "id, status, params, deployment_mode, config_profile, "
    "lease_duration_ms, renewal_interval_ms, started_at, ended_at"
)


class ChaosRunResponse(BaseModel):
    id: int
    status: str
    params: dict[str, Any]
    deployment_mode: str
    config_profile: str
    lease_duration_ms: int
    renewal_interval_ms: int
    started_at: str
    ended_at: str | None


def serialize_chaos_run(row: asyncpg.Record) -> ChaosRunResponse:
    return ChaosRunResponse(
        id=row["id"],
        status=row["status"],
        params=json.loads(row["params"]),
        deployment_mode=row["deployment_mode"],
        config_profile=row["config_profile"],
        lease_duration_ms=row["lease_duration_ms"],
        renewal_interval_ms=row["renewal_interval_ms"],
        started_at=row["started_at"].isoformat(),
        ended_at=row["ended_at"].isoformat() if row["ended_at"] is not None else None,
    )


class InvariantResults(BaseModel):
    no_duplicate_effects: bool
    log_monotonic: bool
    single_writer_per_epoch: bool
    terminal_reachability: bool
    replay_determinism: bool


class RecoveryMs(BaseModel):
    p50: int
    p95: int
    p99: int
    max: int


class ChaosReportResponse(BaseModel):
    chaos_run_id: int
    invariants: InvariantResults
    violations: list[dict[str, Any]]
    duplicate_effect_count: int
    stranded_run_count: int
    kills_injected: int
    runs_total: int
    steps_total: int
    config_profile: str
    lease_duration_ms: int
    recovery_ms: RecoveryMs | None
    replay_steps_mean: float | None
    replay_ms_mean: float | None
    steps_per_second: float | None
    fencing_events: int
    uncertainty_entries: dict[str, int]
    dead_letter_count: int
    duration_seconds: int
    created_at: str


CHAOS_REPORT_COLUMNS = (
    "cr.chaos_run_id, cr.inv_no_duplicate_effects, cr.inv_log_monotonic, "
    "cr.inv_single_writer_per_epoch, cr.inv_terminal_reachability, cr.inv_replay_determinism, "
    "cr.violations, cr.duplicate_effect_count, cr.stranded_run_count, cr.kills_injected, "
    "cr.runs_total, cr.steps_total, cr.recovery_ms_p50, cr.recovery_ms_p95, cr.recovery_ms_p99, "
    "cr.recovery_ms_max, cr.replay_steps_mean, cr.replay_ms_mean, cr.steps_per_second, "
    "cr.fencing_events, cr.uncertainty_entries, cr.dead_letter_count, cr.duration_seconds, "
    "cr.created_at, run.config_profile, run.lease_duration_ms"
)


def serialize_chaos_report(row: asyncpg.Record) -> ChaosReportResponse:
    recovery = (
        RecoveryMs(
            p50=row["recovery_ms_p50"],
            p95=row["recovery_ms_p95"],
            p99=row["recovery_ms_p99"],
            max=row["recovery_ms_max"],
        )
        if row["recovery_ms_p50"] is not None
        else None
    )
    return ChaosReportResponse(
        chaos_run_id=row["chaos_run_id"],
        invariants=InvariantResults(
            no_duplicate_effects=row["inv_no_duplicate_effects"],
            log_monotonic=row["inv_log_monotonic"],
            single_writer_per_epoch=row["inv_single_writer_per_epoch"],
            terminal_reachability=row["inv_terminal_reachability"],
            replay_determinism=row["inv_replay_determinism"],
        ),
        violations=json.loads(row["violations"]),
        duplicate_effect_count=row["duplicate_effect_count"],
        stranded_run_count=row["stranded_run_count"],
        kills_injected=row["kills_injected"],
        runs_total=row["runs_total"],
        steps_total=row["steps_total"],
        config_profile=row["config_profile"],
        lease_duration_ms=row["lease_duration_ms"],
        recovery_ms=recovery,
        replay_steps_mean=(
            float(row["replay_steps_mean"]) if row["replay_steps_mean"] is not None else None
        ),
        replay_ms_mean=float(row["replay_ms_mean"]) if row["replay_ms_mean"] is not None else None,
        steps_per_second=(
            float(row["steps_per_second"]) if row["steps_per_second"] is not None else None
        ),
        fencing_events=row["fencing_events"],
        uncertainty_entries=json.loads(row["uncertainty_entries"]),
        dead_letter_count=row["dead_letter_count"],
        duration_seconds=row["duration_seconds"],
        created_at=row["created_at"].isoformat(),
    )
