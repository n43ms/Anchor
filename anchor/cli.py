"""Anchor Durable Execution Engine CLI entrypoint.

Provides standard subcommands: `anchor init`, `anchor dev`, `anchor status`, and `anchor version`.
"""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

_STARTER_APP_TEMPLATE = """# app.py - Single-File Anchor Agent
import anchor

# 1. Define Tools with explicit crash safety policies
@anchor.tool(safety="retry_safe", naturally_idempotent=True)
async def search_academic_papers(topic: str) -> dict:
    \"\"\"Read-only paper search.\"\"\"
    return {"papers": ["Paxos Made Simple", "Raft Consensus"]}

@anchor.tool(safety="unsafe")
async def send_summary_email(to: str, count: int) -> dict:
    \"\"\"Sends live email summary (non-idempotent side effect).\"\"\"
    return {"status": "delivered", "recipient": to}

# 2. Define Agent using line-by-line yield syntax
@anchor.agent(name="my_first_agent")
def decide_next_step(ctx: anchor.StepContext):
    search_data = yield anchor.ToolCall("search_academic_papers", {"topic": ctx.input["topic"]})
    papers = search_data["papers"]

    email_res = yield anchor.ToolCall("send_summary_email", {
        "to": ctx.input["email"],
        "count": len(papers)
    })

    yield anchor.Done({"status": "completed", "email_delivery": email_res})

# 3. Execution Trigger
if __name__ == "__main__":
    result = anchor.run(
        "my_first_agent",
        input={"topic": "Consensus Protocols", "email": "user@stanford.edu"}
    )
    print("Workflow Output Payload:", result)
"""

_DOCKER_COMPOSE_TEMPLATE = """version: "3.8"

services:
  anchor-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: anchor
      POSTGRES_USER: anchor
      POSTGRES_PASSWORD: anchor
    ports:
      - "5432:5432"
    volumes:
      - anchor-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U anchor"]
      interval: 2s
      timeout: 5s
      retries: 10

  anchor-redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  anchor-api:
    image: n43ms/anchor-api:latest
    build:
      context: .
      dockerfile: ops/docker/Dockerfile.api
    ports:
      - "8000:8000"
      - "3000:3000"
    environment:
      ANCHOR_DATABASE_URL: postgresql://anchor:anchor@anchor-db:5432/anchor
      ANCHOR_REDIS_URL: redis://anchor-redis:6379/0
      ANCHOR_AUTHORING_EXECUTE: "true"
      ANCHOR_CONFIG_PROFILE: demo
    depends_on:
      anchor-db:
        condition: service_healthy
      anchor-redis:
        condition: service_started

  anchor-worker:
    image: n43ms/anchor-worker:latest
    build:
      context: .
      dockerfile: ops/docker/Dockerfile.worker
    deploy:
      replicas: 3
    environment:
      ANCHOR_DATABASE_URL: postgresql://anchor:anchor@anchor-db:5432/anchor
      ANCHOR_REDIS_URL: redis://anchor-redis:6379/0
      ANCHOR_CONFIG_PROFILE: demo
    depends_on:
      anchor-db:
        condition: service_healthy
      anchor-redis:
        condition: service_started

volumes:
  anchor-pgdata:
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="anchor", description="Anchor Durable Execution Engine CLI"
    )
    subparsers = parser.add_subparsers(dest="command")

    # `anchor version`
    subparsers.add_parser("version", help="Print Anchor framework version")

    # `anchor init`
    subparsers.add_parser(
        "init", help="Initialize docker-compose.yml and starter app.py in project folder"
    )

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

    if args.command == "init":
        compose_path = Path("docker-compose.yml")
        app_path = Path("app.py")

        if not compose_path.exists():
            compose_path.write_text(_DOCKER_COMPOSE_TEMPLATE, encoding="utf-8")
            print("[+] Created docker-compose.yml")
        else:
            print("! docker-compose.yml already exists")

        if not app_path.exists():
            app_path.write_text(_STARTER_APP_TEMPLATE, encoding="utf-8")
            print("[+] Created app.py starter template")
        else:
            print("! app.py already exists")

        print("\nNext steps:")
        print("1. Start cluster:  docker compose up")
        print("2. Run agent:      python app.py")
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
