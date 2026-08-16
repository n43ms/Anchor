"""Request logging middleware (plan.md P1.7, T103) and per-IP rate
limiting (plan.md P6.12, T359-T360; D-39, FR-006).

**Rate-limit values are module constants, not `runtime_config` keys.**
D-39 says the limit and window "live in configuration", but data-model.md
§9 is explicit that `runtime_config` seeds exactly fifteen keys, none of
them rate limits — adding a sixteenth would contradict a specifically
documented invariant. These constants are API-tier-only (no worker ever
reads them) and, like `anchor.api.serializers.workers.STALE_AFTER_SECONDS`,
are operational values no correctness invariant depends on: widening or
narrowing them changes how quickly an abusive visitor gets throttled,
never whether execution stays correct.

**In-process is the whole fleet, by design** (D-39): there is exactly one
web service in this deployment (`ops/compose/docker-compose.yml`), so a
token bucket held in this process's memory is adequate — it would not be,
the instant a second API instance existed, without moving to a shared
store (Redis, most naturally). That assumption is stated here so a future
change to the deployment topology finds it rather than silently breaking
the limiter (data-model.md's own convention for undocumented assumptions).
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger("anchor.api.request")

_RUN_ID_IN_PATH = re.compile(r"/api/runs/(\d+)")

# --- Rate limiting (T359-T360) ---

SUBMISSION_LIMIT_PER_MINUTE = 10
KILL_LIMIT_PER_MINUTE = 5
DEMO_HOURLY_CAP = 20

_SUBMISSION_WINDOW_S = 60.0
_KILL_WINDOW_S = 60.0
_DEMO_CAP_WINDOW_S = 3600.0


class _TokenBucket:
    """Fixed-window counter per key (client IP), reset when the window
    elapses. A window counter, not a leaky/rolling bucket — simpler, and
    adequate for "don't let one visitor dominate a shared demo instance",
    which is the entire requirement (§21.6).
    """

    def __init__(self, *, limit: int, window_s: float) -> None:
        self._limit = limit
        self._window_s = window_s
        self._windows: dict[str, tuple[float, int]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window_start, count = self._windows.get(key, (now, 0))
        if now - window_start >= self._window_s:
            window_start, count = now, 0
        if count >= self._limit:
            self._windows[key] = (window_start, count)
            return False
        self._windows[key] = (window_start, count + 1)
        return True


_submission_bucket = _TokenBucket(limit=SUBMISSION_LIMIT_PER_MINUTE, window_s=_SUBMISSION_WINDOW_S)
_kill_bucket = _TokenBucket(limit=KILL_LIMIT_PER_MINUTE, window_s=_KILL_WINDOW_S)
_demo_cap_bucket = _TokenBucket(limit=DEMO_HOURLY_CAP, window_s=_DEMO_CAP_WINDOW_S)

_KILL_PATH = re.compile(r"^/api/workers/[^/]+/kill$")


def _client_key(request: Request) -> str:
    client = request.client
    return client.host if client is not None else "unknown"


async def rate_limit_requests(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Applied to submission and kill only (FR-006, §21.6: "the kill
    endpoint should also be rate-limited — not for safety, but so the
    fleet view stays readable"). Every other route is unaffected.

    Returns a `JSONResponse` directly rather than raising `HTTPException`:
    Starlette's `ExceptionMiddleware` (what normally turns an `HTTPException`
    into a JSON 4xx) sits *inside* user middleware registered via
    `app.middleware("http")`, not outside it — an `HTTPException` raised
    here would reach only the outer `ServerErrorMiddleware` and surface as
    a bare 500, not the 429 a rate-limited caller should see.
    """
    key = _client_key(request)

    # contracts/openapi.yaml names "rate_limited" as one of its two
    # explicit `Error.error` examples — every 429 this middleware returns
    # uses it, so the machine code is stable regardless of which bucket
    # (submission, demo cap, kill) triggered it; `message` still says which.
    if request.method == "POST" and request.url.path == "/api/runs":
        if not _submission_bucket.allow(key):
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limited", "message": "submission rate limit exceeded"},
            )
        if not _demo_cap_bucket.allow(key):
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limited", "message": "hourly demo run cap exceeded"},
            )
    elif request.method == "POST" and _KILL_PATH.match(request.url.path):
        if not _kill_bucket.allow(key):
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limited", "message": "kill rate limit exceeded"},
            )

    return await call_next(request)


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
