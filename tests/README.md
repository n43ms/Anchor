# 🧪 Anchor Test Suite & Execution Guide

This document defines the execution environment, database isolation rules, and step-by-step instructions for running Anchor's test suite cleanly.

---

## ⚡ Quickstart: Clean Rebuild & Test Execution

Follow these steps to wipe persistent Docker volumes, rebuild container images with zero cache, set environment variables, and run `pytest`.

### Step 1: Wipe Volumes & Rebuild Stack from Scratch

```powershell
# 1. Stop containers and delete all persistent PostgreSQL & Redis volumes (-v flag)
docker compose -f ops/compose/docker-compose.yml down -v

# 2. Rebuild image layers with zero cache
docker compose -f ops/compose/docker-compose.yml build --no-cache

# 3. Start background services (PostgreSQL & Redis)
docker compose -f ops/compose/docker-compose.yml up -d
```

---

### Step 2: Set Environment Variables

Set these environment variables in your terminal session to ensure `pytest` runs against the isolated `anchor_test` database rather than the live application database (`anchor`):

#### PowerShell:
```powershell
# Live application database (Docker container listens on host port 5433)
$env:ANCHOR_DATABASE_URL="postgresql://anchor:anchor@localhost:5433/anchor"

# Isolated test database (Pytest connects, truncates, & tests against anchor_test)
$env:ANCHOR_TEST_DATABASE_URL="postgresql://anchor:anchor@localhost:5433/anchor_test"

# Isolated test Redis database (Index 1 for test suite; Index 0 for live)
$env:ANCHOR_TEST_REDIS_URL="redis://localhost:6379/1"
```

#### Bash / Zsh:
```bash
export ANCHOR_DATABASE_URL="postgresql://anchor:anchor@localhost:5433/anchor"
export ANCHOR_TEST_DATABASE_URL="postgresql://anchor:anchor@localhost:5433/anchor_test"
export ANCHOR_TEST_REDIS_URL="redis://localhost:6379/1"
```

---

### Step 3: Create & Migrate Database Schemas (`006_chaos`)

Since `docker compose down -v` creates a fresh PostgreSQL instance, create the `anchor_test` database and upgrade both schemas:

```powershell
# 1. Create anchor_test database in PostgreSQL (if not already existing)
uv run python -c "import asyncpg, asyncio; asyncio.run(asyncpg.connect('postgresql://anchor:anchor@localhost:5433/anchor').then(lambda c: c.execute('CREATE DATABASE anchor_test')))" 2>$null

# 2. Upgrade the live application database (anchor)
uv run alembic -c ops/migrations/alembic.ini upgrade head

# 3. Upgrade the isolated test database (anchor_test)
$env:ANCHOR_DATABASE_URL="postgresql://anchor:anchor@localhost:5433/anchor_test"
uv run alembic -c ops/migrations/alembic.ini upgrade head

# 4. Reset ANCHOR_DATABASE_URL back to live database
$env:ANCHOR_DATABASE_URL="postgresql://anchor:anchor@localhost:5433/anchor"
```

---

### Step 4: Run Pytest

```powershell
# Run the complete test suite
uv run pytest

# Or run unit tests specifically
uv run pytest tests/unit -v

# Or run failure & chaos smoke tests
uv run pytest tests/failure -v
```

---

## 📁 Test Suite Structure

- **`tests/unit/`**: Pure functions, event payload models, lease math, retry backoff jitter, SQL state error mappings.
- **`tests/boundary/`**: Schema version gate, CORS, module boundaries, openapi contract compliance.
- **`tests/concurrency/`**: Multi-worker claim races, lock contention, zombie fencing (`AN001`).
- **`tests/failure/`**: Fault-injection matrix testing worker crashes, tool failures, and chaos smoke tests.
- **`tests/replay/`**: Log folding, virtual time projection, and replay determinism ($I_8$).
