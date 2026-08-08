"""Alembic environment.

Reads the database URL from `ANCHOR_DATABASE_URL` rather than
`alembic.ini`, so the same configuration works unmodified across compose,
CI, and a bare `alembic upgrade head` run by a developer. Migrations run
synchronously (`psycopg`-style sync engine) even though the application is
async throughout — this is the one place a sync driver is appropriate,
since migrations run once, in the one-shot `migrate` service, never inside
the API or a worker's event loop.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # No ORM models: every object is raw SQL (D-05).


def _sync_url() -> str:
    """`ANCHOR_DATABASE_URL` is an asyncpg-style DSN for the application;
    Alembic's sync engine needs the `postgresql+psycopg://` scheme.
    """
    url = os.environ["ANCHOR_DATABASE_URL"]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _sync_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
