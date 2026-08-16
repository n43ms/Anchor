"""T372 — every mutating route that accepts a `run_id` in its path is one
of an explicit allowlist. A new mutating route on `/api/runs/{run_id}/...`
added without deliberately extending this allowlist fails here rather
than silently becoming a write path nobody reviewed for whether it could
race a worker, another visitor's run, or the epoch/lease machinery
(FR-135). This is the one assertion whose subject is code that does not
exist: it exists specifically to catch *future* additions, not to verify
anything about the four routes it allows today.

Pure: constructs the app, no database connection.
"""

from __future__ import annotations

from anchor.api.app import create_app
from tests.boundary.test_openapi_surface_matches import _iter_leaf_routes

_ALLOWED_RUN_ID_MUTATIONS = frozenset(
    {
        ("POST", "/api/runs/{run_id}/cancel"),
        ("POST", "/api/runs/{run_id}/resolve"),
    }
)

_MUTATING_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


def test_every_run_id_mutating_route_is_explicitly_allowed() -> None:
    app = create_app()
    offenders: set[tuple[str, str]] = set()
    for route in _iter_leaf_routes(app.routes):
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if path is None or methods is None:
            continue
        if "{run_id}" not in path:
            continue
        for method in methods:
            if method in _MUTATING_METHODS and (method, path) not in _ALLOWED_RUN_ID_MUTATIONS:
                offenders.add((method, path))

    assert not offenders, (
        f"mutating run_id route(s) not on the explicit allowlist: {sorted(offenders)} "
        "(FR-135) — add it to _ALLOWED_RUN_ID_MUTATIONS deliberately, after reviewing "
        "whether it can race a worker's ownership of the run"
    )
