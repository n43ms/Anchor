# Test suite

## Structure

- **`tests/unit/`** — Pure functions: event payload models, lease math, retry backoff jitter, SQL
  state error mappings.
- **`tests/property/`** — Canonical serialization stability: structurally identical arguments in any
  key order hash identically. This protects the entire idempotency mechanism.
- **`tests/replay/`** — Log folding, virtual time projection, and replay determinism (`I6`).
- **`tests/concurrency/`** — Multi-worker claim races, lock contention, zombie fencing.
- **`tests/failure/`** — Fault-injection tests, one per row of `anchor-spec.md`'s failure matrix
  (`§9`) — each induces the failure and asserts the documented handling.
- **`tests/boundary/`** — Schema version gate, CORS, deployment-mode routing, module import
  boundaries, OpenAPI contract compliance.
- **`tests/contract/`** — Request/response shape against `contracts/openapi.yaml`.

## Running against a real database

Most of this suite exercises real PostgreSQL and Redis instances rather than mocks — a mocked
database is exactly the kind of divergence-from-production risk this project's own correctness
guarantees exist to eliminate. `tests/conftest.py` reads its DSNs from the environment and skips any
test requiring a fixture it cannot reach, so the suite degrades gracefully without Docker; the
concurrency, failure, and replay suites need it to exercise anything meaningful.

```bash
docker compose -f ops/compose/docker-compose.yml up -d postgres redis
```

Point the suite at an isolated database, separate from any application instance you may also be
running against the same containers:

```bash
export ANCHOR_TEST_DATABASE_URL="postgresql://anchor:anchor@localhost:5432/anchor_test"
export ANCHOR_TEST_REDIS_URL="redis://localhost:6379/1"

createdb -h localhost -U anchor anchor_test   # first run only
uv run alembic -c ops/migrations/alembic.ini -x db-url="$ANCHOR_TEST_DATABASE_URL" upgrade head
```

(PowerShell: replace `export` with `$env:NAME = "..."` and `createdb` with the equivalent `psql -c
"CREATE DATABASE anchor_test"` invocation.)

## Running

```bash
uv run pytest                    # full suite
uv run pytest tests/unit -v      # one suite
uv run pytest -q                 # quiet; DB-dependent tests skip cleanly if no database is reachable
```
