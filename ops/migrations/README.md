# Migrations

Alembic, **forward-only** (no `downgrade()` bodies — see `env.py` and
`tests/boundary/test_migrations_forward_only.py`). Every constraint, trigger,
and function is raw SQL inside a migration, never expressed through
SQLAlchemy Core or ORM constructs — this is why `sqlalchemy` is confined to
this directory and nowhere else in `anchor/` (D-05, D-34's sibling rule).

Migrations run exactly once, in a dedicated one-shot `migrate` service
before the API or any worker starts (research.md D-45). No long-running
process ever calls `alembic upgrade` itself.
