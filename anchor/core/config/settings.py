"""The fifteen runtime settings (data-model.md §9), typed and unit-suffixed.

No timing, retry, or concurrency constant is legal anywhere else in the
codebase (FR-059). Every field name carries its unit so a reviewer never has
to guess whether a value is milliseconds or seconds.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class LeaseRenewedEmitPolicy(StrEnum):
    """When LEASE_RENEWED is written to the log (research.md D-48)."""

    BOUNDARIES_AND_SLOW = "boundaries_and_slow"
    ALWAYS = "always"


class RuntimeSettings(BaseModel):
    """The fifteen configuration keys seeded into `runtime_config` at migration
    time and re-read (with a bounded poll) at runtime. This model is the
    single place these values may be declared; every consumer reads an
    instance of it rather than a module-level constant.
    """

    # --- Lease and renewal ---
    lease_duration_ms: int = Field(gt=0)
    renewal_interval_ms: int = Field(gt=0)
    margin_ms: int = Field(
        gt=0,
        description="lease_duration_ms - renewal_interval_ms, asserted rather than derived "
        "so a hand-edited runtime_config row cannot silently violate the relationship.",
    )
    reclaim_poll_interval_ms: int = Field(gt=0)
    renewal_latency_warn_pct: float = Field(
        gt=0,
        le=1,
        description="Fraction of the lease above which a renewal is emitted and flagged (D-48).",
    )
    lease_renewed_emit_policy: LeaseRenewedEmitPolicy = LeaseRenewedEmitPolicy.BOUNDARIES_AND_SLOW

    # --- Step execution ---
    step_timeout_ms: int = Field(gt=0)
    max_attempts_per_step: int = Field(gt=0)
    backoff_base_ms: int = Field(gt=0)
    backoff_factor: float = Field(gt=1)
    backoff_jitter_pct: float = Field(ge=0, le=1)
    backoff_cap_ms: int = Field(gt=0)

    # --- Concurrency ---
    per_worker_concurrency: int = Field(gt=0)
    global_concurrency_cap: int = Field(gt=0)

    # --- Payload ---
    max_event_payload_bytes: int = Field(
        gt=0,
        description="Payload ceiling (D-51). Exceeding this dead-letters the step; it is "
        "never truncated, because truncation would replay to different messages than the "
        "original execution.",
    )

    def assert_relationships(self) -> None:
        """The three-part startup assertion (FR-060).

        Raises `anchor.core.db.errors.ConfigAssertionError` naming the
        violated relationship and the offending values — never a bare
        "invalid configuration", which costs an hour at the worst possible
        time.
        """
        from anchor.core.config.assertion import assert_relationships

        assert_relationships(self)
