"""`register_tool` and the declared-safety registry (plan.md P5.5, T267-T273;
contracts/tool-contract.md).

Two registries exist and are deliberately not the same thing. The in-process
dict here (`_REGISTRY`) holds the actual callables — `fn`, `reconcile_fn` —
that `core.journal.two_phase` invokes; nothing about a Python function can
live in a database row. The `tool_registry` **table** (migration 003) holds
the declared *safety category* and is what a rolling deploy can disagree
with itself about, which is why conflict detection reads and writes the
table, never this dict.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

import asyncpg

from anchor.core.journal.reconcile import ReconcileFn

Safety = Literal["retry_safe", "reconcilable", "unsafe"]
_SAFETY_VALUES = ("retry_safe", "reconcilable", "unsafe")

ToolFn = Callable[..., Awaitable[Any]]


class ToolRegistrationError(ValueError):
    """Raised by the three refusal conditions FR-045/FR-046 name. Distinct
    from a bare `ValueError` so a caller can catch registration mistakes
    specifically, without also catching an unrelated `ValueError` from
    somewhere else in a tool's own construction.
    """


@dataclass(frozen=True, slots=True)
class ToolDeclaration:
    """A tool's full declaration: the callable, plus the five
    safety-relevant fields data-model.md §4 content-hashes for conflict
    detection.
    """

    name: str
    fn: ToolFn
    safety: Safety
    naturally_idempotent: bool = False
    provider_accepts_key: bool = False
    reconcile_fn: ReconcileFn | None = None
    description: str | None = None
    timeout_ms: int | None = None

    @property
    def has_reconcile_fn(self) -> bool:
        return self.reconcile_fn is not None

    @property
    def default_policy(self) -> Safety:
        return self.safety

    def declaration_hash(self) -> str:
        """SHA-256 over the five safety-relevant fields, in a fixed key
        order — the identity of the *declaration*, as distinct from the
        tool (D-46). Deliberately independent of `core.journal.canonical`:
        this is a fixed five-field record, not caller-supplied arguments,
        so a dedicated fixed-order encoding is clearer than routing a
        five-key dict through the general canonicalizer.
        """
        payload = json.dumps(
            {
                "safety": self.safety,
                "naturally_idempotent": self.naturally_idempotent,
                "provider_accepts_key": self.provider_accepts_key,
                "has_reconcile_fn": self.has_reconcile_fn,
                "default_policy": self.default_policy,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate(decl: ToolDeclaration) -> None:
    """The three refusal conditions (FR-045, FR-046), enforced here so a
    mistake is caught at registration rather than at the first crash that
    tries to consult a category that cannot support it. The same three
    rules are also table `CHECK` constraints (migration 003), so a row
    inserted by any other path still satisfies them.
    """
    if decl.safety not in _SAFETY_VALUES:
        raise ToolRegistrationError(
            f"tool {decl.name!r}: safety must be one of {_SAFETY_VALUES}, "
            f"got {decl.safety!r} — there is no default to fall back to"
        )
    if decl.safety == "reconcilable" and decl.reconcile_fn is None:
        raise ToolRegistrationError(
            f"tool {decl.name!r}: safety='reconcilable' requires reconcile_fn"
        )
    if decl.safety == "retry_safe" and not (decl.naturally_idempotent or decl.provider_accepts_key):
        raise ToolRegistrationError(
            f"tool {decl.name!r}: safety='retry_safe' requires naturally_idempotent "
            "or provider_accepts_key — a tool cannot be declared safe to re-execute "
            "without naming why"
        )


_REGISTRY: dict[str, ToolDeclaration] = {}


def register(decl: ToolDeclaration) -> None:
    """In-process registration: makes `decl.fn` and `decl.reconcile_fn`
    resolvable by name for this worker. Does not touch the database — see
    `register_tool` for the declaration upsert and conflict detection.
    """
    _validate(decl)
    _REGISTRY[decl.name] = decl


def resolve(name: str) -> ToolDeclaration | None:
    return _REGISTRY.get(name)


def as_tool_registry() -> dict[str, ToolDeclaration]:
    """A snapshot suitable for `StepContext.tool_registry` — every
    currently in-process-registered tool, by name.
    """
    return dict(_REGISTRY)


_UPSERT_SQL = """
INSERT INTO tool_registry
    (name, safety, naturally_idempotent, provider_accepts_key, has_reconcile_fn,
     default_policy, declaration_hash, declared_by_version, description)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
ON CONFLICT (name) DO UPDATE SET
    -- A matching declaration_hash is a no-op re-registration (the common
    -- case: this worker restarting with the same code). A *different*
    -- hash records the conflict and refuses the tool fleet-wide, without
    -- touching the columns that describe the *original* declaration —
    -- an operator resolving the conflict needs to see both.
    conflict_at = CASE
        WHEN tool_registry.declaration_hash <> EXCLUDED.declaration_hash
        THEN now()
        ELSE tool_registry.conflict_at
    END,
    conflict_version = CASE
        WHEN tool_registry.declaration_hash <> EXCLUDED.declaration_hash
        THEN EXCLUDED.declared_by_version
        ELSE tool_registry.conflict_version
    END
RETURNING conflict_at IS NOT NULL AS conflicted
"""


async def register_tool(
    conn: asyncpg.Connection[Any], decl: ToolDeclaration, *, code_version: str
) -> bool:
    """Validate, register in-process, and upsert the declaration into
    `tool_registry` — called once per tool at worker startup (P5.5).

    Returns `True` if this upsert left (or found) the tool in a conflicted
    state. A conflicting registration does **not** raise: the tool itself
    is refused for execution fleet-wide from this point on
    (`core.journal.two_phase`'s conflict check), which is the fail-loud
    response — refusing to start the whole worker over one tool's
    declaration would take every *other*, unrelated tool down with it.
    """
    _validate(decl)
    register(decl)
    row = await conn.fetchrow(
        _UPSERT_SQL,
        decl.name,
        decl.safety,
        decl.naturally_idempotent,
        decl.provider_accepts_key,
        decl.has_reconcile_fn,
        decl.default_policy,
        decl.declaration_hash(),
        code_version,
        decl.description,
    )
    assert row is not None
    return bool(row["conflicted"])
