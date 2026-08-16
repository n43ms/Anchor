"""T378 — the backend surface matches `contracts/openapi.yaml` exactly.

The contract declares 23 paths and 25 operations. Eight of those
operations are deliberately not yet mounted, each for a reason already
decided and documented elsewhere in this codebase, not a phase-6 gap:

- `POST /api/workers/{worker_id}/kill` — deferred to phase 8: its response
  requires `chaos_event_id`, and `chaos_events` does not exist until phase
  8's migration (`anchor/api/routers/workers.py`'s own module docstring).
- `POST /api/chaos/start`, `GET /api/chaos`, `GET /api/chaos/latest`,
  `GET /api/chaos/{chaos_run_id}/report` — phase 8, the chaos harness.
- `POST /api/authoring/validate`, `POST /api/authoring/generate`,
  `POST /api/authoring/register` — phase 9, stretch.

Every one of the remaining 17 operations must be mounted after phase 6.
Pure: constructs the app (no lifespan, no database connection) and reads
its route table.
"""

from __future__ import annotations

import pytest

from anchor.api.app import create_app

_DEFERRED_OPERATIONS = frozenset(
    {
        ("POST", "/api/workers/{worker_id}/kill"),
        ("POST", "/api/chaos/start"),
        ("GET", "/api/chaos"),
        ("GET", "/api/chaos/latest"),
        ("GET", "/api/chaos/{chaos_run_id}/report"),
        ("POST", "/api/authoring/validate"),
        ("POST", "/api/authoring/generate"),
        ("POST", "/api/authoring/register"),
    }
)

# Every (method, path) contracts/openapi.yaml declares — 25 operations
# across 23 paths, transcribed directly from the document rather than
# parsed out of it with a YAML dependency this project doesn't otherwise
# need (constitution D-04: no dependency outside the frozen set).
_CONTRACT_OPERATIONS = frozenset(
    {
        ("POST", "/api/runs"),
        ("GET", "/api/runs"),
        ("GET", "/api/runs/{run_id}"),
        ("GET", "/api/runs/{run_id}/timeline"),
        ("GET", "/api/runs/{run_id}/events"),
        ("GET", "/api/runs/{run_id}/effects"),
        ("POST", "/api/runs/{run_id}/cancel"),
        ("POST", "/api/runs/{run_id}/resolve"),
        ("POST", "/api/runs/demo/reset"),
        ("GET", "/api/workers"),
        ("POST", "/api/workers/{worker_id}/kill"),
        ("POST", "/api/chaos/start"),
        ("GET", "/api/chaos"),
        ("GET", "/api/chaos/latest"),
        ("GET", "/api/chaos/{chaos_run_id}/report"),
        ("GET", "/api/agents"),
        ("GET", "/api/tools"),
        ("GET", "/api/events"),
        ("GET", "/api/metrics"),
        ("GET", "/api/health"),
        ("GET", "/api/config"),
        ("PATCH", "/api/config"),
        ("POST", "/api/authoring/validate"),
        ("POST", "/api/authoring/generate"),
        ("POST", "/api/authoring/register"),
    }
)


def test_contract_operation_count_is_23_paths_25_operations() -> None:
    paths = {path for _, path in _CONTRACT_OPERATIONS}
    assert len(paths) == 23
    assert len(_CONTRACT_OPERATIONS) == 25


def _fastapi_path_to_openapi_path(path: str) -> str:
    """FastAPI/Starlette route paths already use `{name}` placeholders —
    identical to OpenAPI's own syntax — so this is the identity function;
    kept named and called explicitly so a future path-templating change in
    either system has one place to adapt.
    """
    return path


def _iter_leaf_routes(routes: object) -> list[object]:
    """Flatten FastAPI's route tree. `app.include_router` wraps each
    included router in a lazy `_IncludedRouter` (this FastAPI version's own
    routing internals, not anything this codebase controls) whose real
    `APIRoute` list lives under `.original_router.routes` — this walks
    through that one level of indirection rather than assuming `app.routes`
    is already flat.
    """
    leaves: list[object] = []
    for route in routes:  # type: ignore[attr-defined]
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            leaves.extend(_iter_leaf_routes(original_router.routes))
        else:
            leaves.append(route)
    return leaves


def _mounted_operations() -> set[tuple[str, str]]:
    app = create_app()
    mounted: set[tuple[str, str]] = set()
    for route in _iter_leaf_routes(app.routes):
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None:
            continue
        if not path.startswith("/api/"):
            continue
        openapi_path = _fastapi_path_to_openapi_path(path)
        for method in methods or ():
            if method == "HEAD":
                continue
            mounted.add((method, openapi_path))
    return mounted


def test_every_non_deferred_contract_operation_is_mounted() -> None:
    # PATCH /api/config is conditionally mounted (T334, checked separately
    # below) — this process runs with ANCHOR_AUTHORING_EXECUTE unset, so
    # its legitimate absence here is not a missing-operation failure.
    expected = _CONTRACT_OPERATIONS - _DEFERRED_OPERATIONS - {("PATCH", "/api/config")}
    mounted = _mounted_operations()
    missing = expected - mounted
    assert not missing, f"contract operations not yet mounted: {sorted(missing)}"


def test_patch_config_mounted_only_when_authoring_execute_is_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T304/T334: `PATCH /api/config` is a 404 in demonstration mode — not
    mounted at all — and present only when `ANCHOR_AUTHORING_EXECUTE=true`.
    """
    from anchor.api.app import create_app as build_app

    def _mounted_methods_and_paths(app: object) -> set[tuple[str, str | None]]:
        return {
            (method, getattr(route, "path", None))
            for route in _iter_leaf_routes(app.routes)  # type: ignore[attr-defined]
            for method in getattr(route, "methods", None) or ()
        }

    monkeypatch.setenv("ANCHOR_AUTHORING_EXECUTE", "false")
    assert ("PATCH", "/api/config") not in _mounted_methods_and_paths(build_app())

    monkeypatch.setenv("ANCHOR_AUTHORING_EXECUTE", "true")
    assert ("PATCH", "/api/config") in _mounted_methods_and_paths(build_app())


def test_no_mounted_operation_is_undeclared_by_the_contract() -> None:
    """The inverse direction: every `/api/...` route this app actually
    serves must be one the contract names — a new mutating (or any) route
    added without updating `contracts/openapi.yaml` fails here rather than
    silently becoming an undocumented surface.
    """
    mounted = _mounted_operations()
    # PATCH /api/config is conditionally mounted (local mode only,
    # T334) — this test runs with ANCHOR_AUTHORING_EXECUTE unset in this
    # process, so it is legitimately absent here rather than merely
    # deferred; excluded from the "undeclared" check in either state since
    # it IS declared by the contract regardless of whether this particular
    # process mounted it.
    undeclared = mounted - _CONTRACT_OPERATIONS
    assert not undeclared, f"mounted routes the contract does not declare: {sorted(undeclared)}"
