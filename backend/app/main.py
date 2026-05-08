"""FastAPI application factory and global exception handlers.

The factory pattern (`create_app`) keeps app construction side-effect free so
tests can build isolated instances with custom settings overrides. The bottom
of the module exposes `app` for `uvicorn app.main:app`.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.config import Settings, get_settings
from app.logging_config import configure_logging
from app.schemas.common import ErrorDetail, ErrorResponse
from app.views import api_v1_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    logger.info(
        "Starting TradeSignal AI v%s | env=%s | ai_provider=%s | pairs=%s",
        __version__,
        settings.app_env,
        settings.ai_provider,
        ",".join(settings.active_pairs),
    )
    # DB pool, scheduler, AI providers wire in during later iterations.
    yield
    logger.info("Shutting down TradeSignal AI")


def _error_response(
    code: str,
    message: str,
    status_code: int,
    fields: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, fields=fields or []))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _error_response(
        code=f"HTTP_{exc.status_code}",
        message=str(exc.detail),
        status_code=exc.status_code,
    )


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return one structured entry per failed field instead of a flattened string.

    Frontends can render per-field errors directly from the `fields` array,
    while `message` keeps a human-readable summary for logs and quick glances.
    """
    fields = [
        {
            "loc": [str(part) for part in err.get("loc", [])],
            "msg": err.get("msg", ""),
            "type": err.get("type", ""),
        }
        for err in exc.errors()
    ]
    summary = f"{len(fields)} validation error(s)"
    return _error_response(
        code="VALIDATION_ERROR",
        message=summary,
        status_code=422,
        fields=fields,
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    settings: Settings = request.app.state.settings
    message = str(exc) if settings.is_development else "An unexpected error occurred"
    return _error_response(code="INTERNAL_ERROR", message=message, status_code=500)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build a fresh FastAPI app. Tests can pass a custom Settings."""
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="TradeSignal AI",
        description="Automated Forex and Gold trade signal generation API",
        version=__version__,
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
        openapi_url="/api/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Stash on state so handlers/lifespan don't reach into module globals.
    app.state.settings = settings

    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)

    app.include_router(api_v1_router)

    return app


app = create_app()
