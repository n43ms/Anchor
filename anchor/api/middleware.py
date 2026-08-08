"""Request logging middleware (plan.md P1.7, T103).

Emits one structured JSON line per request, carrying `run_id` when the
route path carries one — so an API-side event (e.g. `RUN_SUBMITTED`) is
traceable back to the HTTP call that caused it, the same way a worker's
log line carries the epoch that caused a fencing incident (D-40).
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

logger = logging.getLogger("anchor.api.request")

_RUN_ID_IN_PATH = re.compile(r"/api/runs/(\d+)")


async def log_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000

    match = _RUN_ID_IN_PATH.search(request.url.path)
    extra = {
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
    }
    if match:
        extra["run_id"] = int(match.group(1))

    logger.info("request handled", extra=extra)
    return response
