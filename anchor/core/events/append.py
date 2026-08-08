"""`core.events.append` — the single append path (plan.md P1.2, D-07).

Transaction comment: the increment of `runs.last_seq` and the insert into
`run_events` must happen in the same statement. A gap in `seq` is
indistinguishable, to every downstream reader, from a lost event — so the
counter and the row it allocates for must never be separable, not even by a
crash between two statements. Expressing both as one CTE removes the
possibility rather than merely making it rare: there is no intermediate
state in which the counter has advanced but the row does not exist, or vice
versa, because there is only one statement.

The payload ceiling (D-51) is enforced here, before the statement is ever
issued, rather than as a database `CHECK`: the size test requires casting
`jsonb` to `text`, and that cast is `stable`, not `immutable` — PostgreSQL
rejects a non-immutable expression in a `CHECK`. Nothing is ever truncated:
truncating would let replay reconstruct different messages than the
original execution, which is exactly the divergence a payload check exists
to prevent.

This module is the **only** place any code may `INSERT INTO run_events`
(`tests/boundary/test_single_append_path.py`).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import asyncpg

from anchor.core.db.errors import PayloadTooLargeError
from anchor.core.events.payloads import PAYLOAD_MODELS
from anchor.core.events.types import EventType

# One CTE: increments runs.last_seq and inserts the event in a single
# statement, so the two effects cannot be observed apart from one another.
_APPEND_SQL = """
WITH allocated AS (
    UPDATE runs
    SET last_seq = last_seq + 1
    WHERE id = $1
    RETURNING last_seq AS seq
)
INSERT INTO run_events (run_id, seq, type, payload, epoch, worker_id, step_index)
SELECT $1, allocated.seq, $2, $3::jsonb, $4, $5, $6
FROM allocated
RETURNING seq, created_at
"""


async def append(
    conn: asyncpg.Connection[Any],
    *,
    run_id: int,
    type: EventType | str,
    payload: dict[str, Any],
    epoch: int,
    worker_id: str,
    step_index: int | None = None,
    max_payload_bytes: int,
) -> tuple[int, datetime]:
    """Append one event and return the allocated `(seq, created_at)`.

    The caller's transaction is what makes this atomic with any other write
    (e.g. the claim statement's own `RUN_CLAIMED` append, or the submission
    transaction's `RUN_SUBMITTED`) — this function issues one statement and
    does not open its own transaction, so it composes into a larger one.

    Crash behaviour: a crash before commit leaves no event and no counter
    advance — `runs.last_seq` is exactly as if `append` had never been
    called, because the UPDATE and the INSERT are one statement inside
    whatever transaction the caller controls.
    """
    event_type = EventType(type)
    model = PAYLOAD_MODELS[event_type.value]
    # Validates at construction — a malformed payload raises here, never at
    # replay (plan.md P1.1).
    validated_payload = model.model_validate(payload).model_dump(mode="json")

    encoded = json.dumps(validated_payload)
    measured_bytes = len(encoded.encode("utf-8"))
    if measured_bytes > max_payload_bytes:
        raise PayloadTooLargeError(
            event_type=event_type.value,
            measured_bytes=measured_bytes,
            ceiling_bytes=max_payload_bytes,
        )

    row = await conn.fetchrow(
        _APPEND_SQL,
        run_id,
        event_type.value,
        encoded,
        epoch,
        worker_id,
        step_index,
    )
    if row is None:
        raise ValueError(f"run {run_id} does not exist; nothing to append to")
    return int(row["seq"]), row["created_at"]
