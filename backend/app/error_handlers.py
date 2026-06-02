"""Centralised HTTP error-handling strategy.

Every error a request can hit is mapped to the project's single response
envelope (``ErrorResponse``) in exactly one place. Handlers live here rather
than inline in ``main.py`` so the *policy* — which failure becomes which status
code, what leaks to the client, what gets logged — is one auditable module
instead of a scattering of ``try/except`` at call sites.

The design follows the layers the rest of the codebase already establishes:

* **Domain errors are framework-agnostic.** Controllers raise
  ``ResourceNotFoundError``; services raise ``ServiceError`` subclasses. Neither
  knows an HTTP status code exists. This module is the boundary that translates
  them — so the same controllers/services stay reusable from a background job or
  a CLI, where "404" would be meaningless.

* **Clients get stable codes; servers get detail.** Each response carries a
  machine-readable ``code`` from a fixed vocabulary (``ErrorCode``) the frontend
  can branch on without parsing prose. For *expected* domain errors (not-found)
  the human message is safe to return verbatim; for *upstream/infrastructure*
  failures the client gets a generic, non-leaky message while the full cause is
  logged server-side. Unexpected exceptions only reveal their message in
  development.

Registration order is irrelevant to correctness — Starlette dispatches by the
exception's MRO, picking the most specific registered handler — but the list in
:func:`register_exception_handlers` is ordered specific→general for readability.
"""

from __future__ import annotations

import logging
from typing import Any, Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings
from app.controllers import ResourceNotFoundError
from app.database import DatabaseConnectionError
from app.schemas.common import ErrorDetail, ErrorResponse
from app.services import ServiceError
from app.services.market_data import RateLimitError

logger = logging.getLogger(__name__)


class ErrorCode:
    """The stable, client-facing error-code vocabulary.

    Kept as plain string constants (not an enum) because the only thing that
    matters about them is the wire value — the frontend branches on these
    strings, so they are part of the API contract and must not drift.
    """

    VALIDATION_ERROR: Final = "VALIDATION_ERROR"
    NOT_FOUND: Final = "NOT_FOUND"
    RATE_LIMITED: Final = "RATE_LIMITED"
    SERVICE_UNAVAILABLE: Final = "SERVICE_UNAVAILABLE"
    INTERNAL_ERROR: Final = "INTERNAL_ERROR"


def _error_response(
    code: str,
    message: str,
    status_code: int,
    fields: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Render an ``ErrorResponse`` envelope as JSON with the given status."""
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, fields=fields or []))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


# ── Domain errors ────────────────────────────────────────────────────────────


async def _not_found_handler(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    """Controller-layer not-found → 404. The message (e.g. "signal 'x' was not
    found") is safe to surface: it echoes the identifier the caller supplied."""
    return _error_response(ErrorCode.NOT_FOUND, str(exc), status_code=404)


async def _service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
    """An upstream dependency (market data / AI) failed.

    Mapped by kind: a rate-limit is a 429 the client can back off on; everything
    else is a 503 (the dependency is temporarily unavailable). The client never
    sees the provider's raw error text — that can carry vendor internals — so the
    message is generic and the real cause is logged.
    """
    if isinstance(exc, RateLimitError):
        logger.warning("Upstream rate limit on %s %s: %s", request.method, request.url.path, exc)
        return _error_response(
            ErrorCode.RATE_LIMITED,
            "An upstream provider rate limit was reached. Please retry shortly.",
            status_code=429,
        )
    logger.exception("Upstream service failure on %s %s", request.method, request.url.path)
    return _error_response(
        ErrorCode.SERVICE_UNAVAILABLE,
        "A required upstream service is temporarily unavailable.",
        status_code=503,
    )


# ── Infrastructure ───────────────────────────────────────────────────────────


async def _database_unavailable_handler(
    request: Request, exc: OperationalError | DatabaseConnectionError
) -> JSONResponse:
    """A database *connection/operational* failure → 503, not a blanket 500.

    Two shapes map here. ``OperationalError`` is SQLAlchemy's driver-agnostic
    category for "couldn't reach / talk to the database" (connection refused,
    server closed the connection, timeout). ``DatabaseConnectionError`` is the
    :class:`~app.database.Database` adapter's normalisation of driver-specific
    connection failures that escape *unwrapped* (notably asyncpg dropping a
    pooled connection mid-operation) — both are transient and retryable, as
    distinct from a programming error in a query. Surfacing them as 503 tells the
    client to retry rather than treating it as a bug. Connection detail is
    logged, never returned.
    """
    logger.exception("Database operational error on %s %s", request.method, request.url.path)
    return _error_response(
        ErrorCode.SERVICE_UNAVAILABLE,
        "The service is temporarily unable to reach its database.",
        status_code=503,
    )


# ── Framework / edge ─────────────────────────────────────────────────────────


async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Request validation (path/query/body) → 422 with one entry per failed field.

    The structured ``fields`` array lets the frontend render per-field messages
    directly; ``message`` keeps a human summary for logs and quick glances.
    """
    fields = [
        {
            "loc": [str(part) for part in err.get("loc", [])],
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    return _error_response(
        ErrorCode.VALIDATION_ERROR,
        f"{len(fields)} validation error(s)",
        status_code=422,
        fields=fields,
    )


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Re-wrap framework ``HTTPException``s (e.g. 405, 404 for unknown routes)
    into the same envelope so clients never see two error shapes."""
    return _error_response(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort: an unexpected exception is a bug → 500.

    The full traceback is logged. The message is only revealed in development;
    production returns a stable, non-leaky string.
    """
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    settings: Settings = request.app.state.settings
    message = str(exc) if settings.is_development else "An unexpected error occurred"
    return _error_response(ErrorCode.INTERNAL_ERROR, message, status_code=500)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every handler to ``app``. Called once from ``create_app``.

    One entry point keeps the registration list — and therefore the complete map
    of "what can go wrong → what the client sees" — in a single readable place.
    """
    app.add_exception_handler(ResourceNotFoundError, _not_found_handler)
    app.add_exception_handler(ServiceError, _service_error_handler)
    app.add_exception_handler(OperationalError, _database_unavailable_handler)
    app.add_exception_handler(DatabaseConnectionError, _database_unavailable_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
