"""`contracts/openapi.yaml` `Error` — `{error, message, detail}` — shaped
consistently across every response this API can return, not just the ones
written with it in mind from the start.

**Why one module rather than fixing every `raise HTTPException(...)` call
site.** `anchor/api/routers/runs.py` alone raises a dozen `HTTPException`s
with a plain string `detail`, from phase 1 onward, before this schema was
being checked against. Rewriting every one individually is the more
"obviously correct per call site" change, but it is also the larger,
higher-risk one, touching request/response behaviour at a dozen
independent locations for a shape concern that is identical at all of
them. The lower-risk, equally-complete alternative: two global exception
handlers (`http_exception_handler`, `validation_exception_handler`,
registered in `anchor.api.app.create_app`) that reshape *any* response an
existing `raise HTTPException(status_code=X, detail="a string")` produces
into `{error, message}`, with `error` defaulted from the status code
(`_DEFAULT_ERROR_CODE_BY_STATUS`) when the raise site didn't specify one.

**Raise sites that want a specific, contract-named machine code** (e.g.
`unknown_agent`, matching `contracts/openapi.yaml`'s own example) use
`ApiError` instead of a bare `HTTPException` — its `detail` is already the
`{error, message}` dict, which both handlers recognize and pass through
unchanged rather than re-deriving a generic code over it.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

_DEFAULT_ERROR_CODE_BY_STATUS: dict[int, str] = {
    400: "bad_request",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
    503: "unavailable",
}


class ApiError(HTTPException):
    """Raise this instead of `fastapi.HTTPException` when the call site
    knows the specific machine code `contracts/openapi.yaml`'s `Error`
    schema wants (e.g. `unknown_agent`) rather than the generic one its
    status code would default to (e.g. `not_found`).
    """

    def __init__(
        self,
        status_code: int,
        *,
        error: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        body: dict[str, Any] = {"error": error, "message": message}
        if detail is not None:
            body["detail"] = detail
        super().__init__(status_code=status_code, detail=body)


def error_body(status_code: int, message: str) -> dict[str, Any]:
    """The fallback shape for a plain-string `HTTPException.detail` (or any
    other exception this API surfaces without an explicit machine code) —
    `error` derived from the status code alone, since that is the only
    signal available at this generic a handling point.
    """
    return {
        "error": _DEFAULT_ERROR_CODE_BY_STATUS.get(status_code, "internal_error"),
        "message": message,
    }
