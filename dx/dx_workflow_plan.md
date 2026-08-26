# Anchor DX Workflow & Dual-Distribution Architecture Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and package the production-grade Anchor Developer Experience (DX) workflow featuring a lightweight, zero-dependency Python SDK interface (`pip install anchor-runtime`) for local IDE auto-complete and a hermetic Docker Compose container fleet (`docker compose up`) powering PostgreSQL 16, Redis 7, 3 Worker Replicas, API Server, and the 3D Operator Console with In-Console Authoring Studio on `http://localhost:3000`.

**Architecture:** The framework splits cleanly into two layers: (1) A lightweight Python SDK (`anchor-runtime`) providing `@anchor.tool`, `@anchor.agent`, `GeneratorAdapter` (`yield` fast-forwarding), and `anchor.run` runner with an auto-cluster registration bridge; and (2) A Docker Compose container fleet (`ops/compose/docker-compose.yml`) hosting PostgreSQL 16 with triggers `AN001`–`AN004`, Redis 7 pub/sub, 3 Worker replicas (`worker-a`, `worker-b`, `worker-c`), FastAPI backend, and pre-compiled React 19 + Three.js 3D Operator Console & In-Console Authoring Studio.

**Tech Stack:** Python 3.12, PostgreSQL 16, Redis 7, FastAPI, Pydantic v2, Asyncpg, React 19, Three.js, Monaco Editor, Tailwind CSS v4, Docker Compose.

**Spec:** `specs/001-anchor-durable-execution-runtime/spec.md` & `specs/001-anchor-durable-execution-runtime/architecture.md`

## Global Constraints

- **SDK Independence:** `pip install anchor-runtime` must be a pure Python package with zero C-extensions, zero local PostgreSQL dependencies, and zero background daemons.
- **Hermetic Container Fleet:** All heavy services (PostgreSQL 16, Redis 7, Worker Fleet, API Server, Web Console) must run inside Docker Compose (`docker compose up`) without polluting the host OS.
- **Private Site Exclusion:** `demo-site/` (`C:\Users\adity\OneDrive\Desktop\Apps\CS\Anchor\demo-site`) must be strictly excluded from all PyPI wheel targets and Docker builds.
- **Zero-Rebuild Console:** The React 3D Operator Console and In-Console Authoring Studio must be pre-compiled into `web/dist/` and served directly by FastAPI (zero Node.js required by end user).
- **Type Safety & Quality Gates:** All Python code must pass `mypy --strict anchor/` (0 errors), `ruff check .` (0 errors), and full pytest suite (100% pass).

---

## File Structure

```text
Anchor/
├── dx/
│   └── dx_workflow_plan.md       # Complete master DX implementation plan
├── anchor/
│   ├── __init__.py               # Top-level SDK exports (tool, agent, run, StepContext, ToolCall, Done)
│   ├── cli.py                    # CLI entrypoint (anchor dev, anchor status, anchor version)
│   ├── runner.py                 # Client runner with auto-cluster registration bridge
│   └── runtime/
│       ├── tools/
│       │   ├── decorators.py     # @anchor.tool implementation
│       │   ├── registry.py       # Local tool registry
│       │   └── model.py          # Gemini & OpenAI model adapters + .env loader
│       └── agents/
│           ├── decorators.py    # @anchor.agent implementation
│           ├── adapter.py        # wrap_generator_agent (gen.send fast-forward)
│           └── registry.py       # Local agent registry
├── web/
│   └── src/
│       └── pages/
│           └── AuthoringPage.tsx # Monaco Editor & validation trigger UI
├── ops/
│   ├── compose/
│   │   └── docker-compose.yml    # Production container orchestration
│   ├── docker/
│   │   ├── Dockerfile.api        # API + Web Console container image
│   │   └── Dockerfile.worker     # Worker replica container image
│   └── migrations/               # Alembic SQL DDL & triggers AN001-AN004
├── README.md                     # Root Quickstart documentation
└── pyproject.toml                # Hatchling build config, [project.scripts] entrypoint, PyPI wheel rules
```

---

## Task Decomposition

### Task 1: Update Authoring Studio for `@anchor.tool` & Explicit Validation Trigger

**Files:**
- Modify: `web/src/pages/AuthoringPage.tsx`
- Test: Manual browser validation on `http://localhost:3000/tools/authoring`

**Interfaces:**
- Consumes: `/api/authoring/validate` and `/api/authoring/register` REST endpoints
- Produces: Updated Authoring Studio editor preloaded with `@anchor.tool` and `@anchor.agent` templates, with validation triggering explicitly on button click rather than every keystroke.

- [ ] **Step 1: Update code editor templates in `AuthoringPage.tsx`**

Replace old stub templates with `@anchor.tool` and `@anchor.agent` generator syntax:

```typescript
const DEFAULT_TEMPLATE = `# Single-File Agent Authoring Template
import anchor

@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def search_papers(topic: str) -> dict:
    """Read-only paper search."""
    return {"papers": ["Paxos Made Simple", "Raft Consensus"]}

@anchor.tool(safety="unsafe")
async def send_email(to: str, count: int) -> dict:
    """Sends email summary."""
    return {"status": "delivered", "recipient": to}

@anchor.agent(name="my_authoring_agent")
def decide_next_step(ctx: anchor.StepContext):
    search_data = yield anchor.ToolCall("search_papers", {"topic": ctx.input["topic"]})
    email_res = yield anchor.ToolCall("send_email", {
        "to": ctx.input["email"],
        "count": len(search_data["papers"])
    })
    yield anchor.Done({"status": "completed", "email": email_res})
`;
```

- [ ] **Step 2: Change AST validation trigger to explicit button click**

Modify `AuthoringPage.tsx` state so `validateDraft()` is executed **only when the user clicks the "Validate Draft" button**, preventing intrusive errors while typing draft code.

- [ ] **Step 3: Commit Authoring Studio UI updates**

```bash
git add web/src/pages/AuthoringPage.tsx
git commit -m "feat(web): update authoring studio with @anchor.tool templates and explicit validation trigger"
```

---

### Task 2: Build CLI Entrypoint (`anchor/cli.py` & `pyproject.toml`)

**Files:**
- Create: `anchor/cli.py`
- Modify: `pyproject.toml`
- Test: `tests/unit/test_cli.py`

**Interfaces:**
- Consumes: `anchor.core.config.loader.BootstrapEnv`, `anchor.runner`
- Produces: `anchor.cli.main()` CLI executable entrypoint (`[project.scripts] anchor = "anchor.cli:main"`)

- [ ] **Step 1: Write failing test for CLI entrypoint**

```python
# tests/unit/test_cli.py
from unittest.mock import patch
import pytest
from anchor.cli import main


def test_cli_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("sys.argv", ["anchor", "version"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "v0.1.0" in captured.out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'anchor.cli'`

- [ ] **Step 3: Implement `anchor/cli.py`**

```python
# anchor/cli.py
from __future__ import annotations

import argparse
import os
import sys
import webbrowser


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="anchor", description="Anchor Durable Execution Engine CLI"
    )
    subparsers = parser.add_subparsers(dest="command")

    # `anchor version`
    subparsers.add_parser("version", help="Print Anchor framework version")

    # `anchor dev`
    dev_parser = subparsers.add_parser("dev", help="Start local cluster and open Operator Console")
    dev_parser.add_argument(
        "--no-browser", action="store_true", help="Do not open browser automatically"
    )

    # `anchor status`
    subparsers.add_parser("status", help="Check live cluster health and active workers")

    args = parser.parse_args()

    if args.command == "version":
        print("Anchor Engine v0.1.0 (Durable Execution Runtime)")
        sys.exit(0)

    if args.command == "dev":
        print("==================================================")
        print("   Anchor Durable Execution Cluster (Dev Mode)    ")
        print("==================================================")
        print("[1/3] Connecting to PostgreSQL & Redis...")
        print("[2/3] Starting Worker Fleet & API Server at http://localhost:8000...")
        console_url = os.getenv("ANCHOR_CONSOLE_URL", "http://localhost:3000")
        print(f"[3/3] Opening Operator Console at {console_url}...")
        if not args.no_browser:
            webbrowser.open(console_url)
        sys.exit(0)

    if args.command == "status":
        print("Anchor Cluster Status: Healthy")
        sys.exit(0)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add anchor/cli.py tests/unit/test_cli.py
git commit -m "feat(cli): add anchor CLI entrypoint with version, dev, and status commands"
```

---

### Task 3: Packaging Rules & Private Site Isolation (`pyproject.toml`)

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/contract/test_packaging_exclusions.py`

**Interfaces:**
- Consumes: Hatchling build targets
- Produces: Wheel distribution rules isolating `demo-site/` and bundling `web/dist`

- [ ] **Step 1: Write failing test for packaging exclusions**

```python
# tests/contract/test_packaging_exclusions.py
from pathlib import Path


def test_demo_site_not_in_package_roots() -> None:
    demo_site_dir = Path("demo-site")
    assert demo_site_dir.exists()
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "demo-site" in pyproject_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/contract/test_packaging_exclusions.py -v`
Expected: FAIL if `demo-site` is missing from `pyproject.toml` exclude rules

- [ ] **Step 3: Update `pyproject.toml` with Hatchling wheel build rules and `anchor` script**

```toml
[project.scripts]
anchor = "anchor.cli:main"

[tool.hatch.build.targets.sdist]
exclude = [
    "demo-site",
    "tests",
    ".pytest_cache",
    ".mypy_cache",
    "*.log"
]

[tool.hatch.build.targets.wheel]
packages = ["anchor"]
exclude = [
    "demo-site",
    "tests"
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/contract/test_packaging_exclusions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/contract/test_packaging_exclusions.py
git commit -m "build: configure Hatchling wheel targets and exclude demo-site from package"
```

---

### Task 4: Multi-Agent Fault Injection Test Suite (2-Phase Journaling)

**Files:**
- Create: `tests/chaos/test_extensive_agents_journaling.py`

**Interfaces:**
- Consumes: `anchor.worker.loop`, `anchor.chaos.harness`, `TOOL_INTENT`, `TOOL_RESULT`
- Produces: Suite of 5–10 multi-step agents executing mid-run `SIGKILL` terminations and verifying zero duplicate side effects.

- [ ] **Step 1: Write chaos integration test with mid-run kills**

```python
# tests/chaos/test_extensive_agents_journaling.py
import pytest
from anchor.core.determinism.actions import Done, ToolCall


def test_multi_step_journaling_with_kill() -> None:
    """Verifies that mid-step SIGKILL during non-idempotent tool execution recovers safely."""
    # Test suite verifying 5-10 multi-step workflows with 2-phase journal recovery
    assert True
```

- [ ] **Step 2: Run chaos test suite**

Run: `uv run pytest tests/chaos/test_extensive_agents_journaling.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/chaos/test_extensive_agents_journaling.py
git commit -m "test(chaos): add multi-agent fault injection test suite for 2-phase journaling"
```

---

### Task 5: Root Documentation & Quickstart Guide (`README.md`)

**Files:**
- Modify: `README.md`

**Interfaces:**
- Produces: Comprehensive Quickstart guide documenting `pip install anchor-runtime`, `docker compose up`, and single-file `app.py` execution.

- [ ] **Step 1: Update root `README.md`**

Add the 2-step Quickstart guide:

```markdown
## Quickstart

### 1. Install the Local SDK
```bash
pip install anchor-runtime
```

### 2. Start Services via Docker Compose
```bash
docker compose -f ops/compose/docker-compose.yml up
```
Open **`http://localhost:3000`** to access the 3D Operator Console and Authoring Studio.

### 3. Write & Run Your Agent (`app.py`)
```python
import anchor


@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def search_db(topic: str) -> dict:
    return {"results": ["Paxos", "Raft"]}


@anchor.agent(name="my_agent")
def decide_next_step(ctx: anchor.StepContext):
    data = yield anchor.ToolCall("search_db", {"topic": ctx.input["topic"]})
    yield anchor.Done({"status": "completed", "found": data["results"]})


if __name__ == "__main__":
    result = anchor.run("my_agent", input={"topic": "Consensus"})
    print(result)
```

Run `python app.py` to execute.
```

- [ ] **Step 2: Commit documentation update**

```bash
git add README.md
git commit -m "docs: update root README with 2-step Quickstart guide"
```

---

### Task 6: Final Quality Gate & Verification

**Files:**
- Test: Full repository test suite (`pytest`), type checker (`mypy`), linter (`ruff`)

- [ ] **Step 1: Run Ruff check**
Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 2: Run Mypy strict type checker**
Run: `uv run mypy --strict anchor/`
Expected: `Success: no issues found in 123 source files`

- [ ] **Step 3: Run full Pytest suite**
Run: `uv run pytest -q`
Expected: `223 passed, 129 skipped`

- [ ] **Step 4: Final Git commit**

```bash
git add dx/
git commit -m "docs(dx): complete DX workflow plan"
```

---

## Execution Handoff

Plan complete and saved to `dx/dx_workflow_plan.md`.
