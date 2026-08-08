"""Configuration load precedence (FR-059).

`runtime_config` is authoritative for every timing, retry, and concurrency
value. The environment supplies exactly two things: which profile to seed
from on first boot, and the bootstrap database DSN needed to reach
`runtime_config` in the first place. No timing constant is readable from
anywhere else — `tests/boundary/test_no_hardcoded_constants.py` enforces
this by walking the AST of `anchor/`.
"""

from __future__ import annotations

import json
from typing import Any

import asyncpg
from pydantic_settings import BaseSettings, SettingsConfigDict

from anchor.core.config.profiles import ConfigProfile
from anchor.core.config.settings import RuntimeSettings


class BootstrapEnv(BaseSettings):
    """The handful of values that must come from the environment because
    they are needed before a database connection exists to read anything
    else from.
    """

    model_config = SettingsConfigDict(env_prefix="ANCHOR_")

    database_url: str
    redis_url: str
    config_profile: ConfigProfile = ConfigProfile.DEMO
    authoring_execute: bool = False
    worker_label_pool: str = "worker-a,worker-b,worker-c"
    code_version: str = "dev"

    @property
    def worker_labels(self) -> list[str]:
        return [label.strip() for label in self.worker_label_pool.split(",") if label.strip()]


# The field names of RuntimeSettings, which are exactly the seeded keys of
# `runtime_config` (data-model.md §9). Kept in one place so a field added to
# RuntimeSettings without a matching migration seed is caught by
# tests/unit/test_config_assertion.py rather than discovered at runtime.
_RUNTIME_CONFIG_FIELDS = tuple(RuntimeSettings.model_fields.keys())


async def load_runtime_settings(conn: asyncpg.Connection[Any]) -> RuntimeSettings:
    """Read every seeded key from `runtime_config` and assemble a
    `RuntimeSettings`. Raises `KeyError` naming the first missing key if the
    table has not been seeded — this should never happen past migration
    001, and a clear `KeyError` here is preferable to a `pydantic`
    validation error that hides which key was absent.
    """
    rows = await conn.fetch(
        "SELECT key, value FROM runtime_config WHERE key = ANY($1::text[])",
        list(_RUNTIME_CONFIG_FIELDS),
    )
    values: dict[str, Any] = {row["key"]: json.loads(row["value"]) for row in rows}
    missing = [key for key in _RUNTIME_CONFIG_FIELDS if key not in values]
    if missing:
        raise KeyError(f"runtime_config is missing seeded key(s): {', '.join(missing)}")
    settings = RuntimeSettings.model_validate(values)
    settings.assert_relationships()
    return settings
