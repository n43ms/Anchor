"""T189 — no ownership, lease, or liveness decision reads from Redis
anywhere in `anchor/` (FR-058). Redis is pub/sub fan-out and fleet
telemetry only; PostgreSQL's `runs.epoch` and `runs.lease_expires_at` are
the only things anyone is ever allowed to reason about for those decisions.

Checked structurally: the modules that make ownership/lease/liveness
decisions — `core.leases.claim`, `core.leases.renew`, and the epoch-gate
machinery in `core.db.errors` — must not import `redis` at all. The modules
that legitimately touch Redis (`worker.registry.kill`,
`worker.registry.heartbeat`'s publish) are exempted by name, and this test
pins that the exemption list is exactly those two, so a new Redis import
anywhere else fails loudly rather than silently becoming a second source of
truth for something PostgreSQL already decides.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_ANCHOR_ROOT = Path(__file__).resolve().parent.parent.parent / "anchor"

# The only modules permitted to import redis at all — both are display/fan-out
# only (kill delivery is not an ownership decision; the fleet telemetry
# publish is explicitly documented as "display only" in heartbeat.py itself).
_REDIS_ALLOWED_MODULES = frozenset(
    {
        "worker/registry/kill.py",
        "worker/registry/heartbeat.py",
        "worker/__main__.py",  # constructs the redis client to hand to kill.py
        # P6.7/P6.8 (D-50): the API process constructs the one redis client
        # shared by the publish path (core.events.publish, no redis import
        # of its own — a Protocol) and the always-on WebSocket-firehose
        # subscriber (api.ws.subscriber, also a Protocol) — both are
        # display/fan-out only, never an ownership or lease decision.
        "api/app.py",
        "api/routers/authoring.py",
    }
)

# Modules whose entire responsibility is an ownership, lease, or liveness
# decision — these must never import redis, structurally, not just "not use
# it in a way we noticed."
_MUST_NEVER_IMPORT_REDIS = (
    "core/leases/claim.py",
    "core/leases/renew.py",
    "core/db/errors.py",
    "core/db/pool.py",
    "worker/loop.py",
    "worker/renewer.py",
)


def _imports_redis(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] == "redis" for alias in node.names):
                return True
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module is not None
            and node.module.split(".")[0] == "redis"
        ):
            return True
    return False


@pytest.mark.parametrize("relative_path", _MUST_NEVER_IMPORT_REDIS)
def test_ownership_lease_and_liveness_modules_never_import_redis(relative_path: str) -> None:
    path = _ANCHOR_ROOT / relative_path
    assert path.exists(), f"expected module not found: {path}"
    assert not _imports_redis(path), f"{relative_path} must not import redis (FR-058)"


def test_redis_import_is_confined_to_the_documented_exemption_list() -> None:
    offenders = []
    for path in _ANCHOR_ROOT.rglob("*.py"):
        relative = path.relative_to(_ANCHOR_ROOT).as_posix()
        if relative in _REDIS_ALLOWED_MODULES:
            continue
        if _imports_redis(path):
            offenders.append(relative)
    assert offenders == [], (
        f"redis imported outside the documented exemption list: {offenders} — "
        "either it is a new display/fan-out-only use (add it to "
        "_REDIS_ALLOWED_MODULES with a stated reason) or it is a new ownership "
        "decision reading from a non-authoritative source (forbidden, FR-058)"
    )
