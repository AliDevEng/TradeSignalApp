import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.schemas.common import ErrorDetail, ErrorResponse
from app.views import analysis, health, pairs, signals

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(
        "Starting TradeSignal AI | env=%s | ai_provider=%s | pairs=%s",
        settings.app_env,
        settings.ai_provider,
        settings.active_pairs,
    )
    # DB pool and scheduler wired in later iterations
    yield
    logger.info("Shutting down TradeSignal AI")


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
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
    message = "; ".join(
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
        for e in exc.errors()
    )
    return _error_response(code="VALIDATION_ERROR", message=message, status_code=422)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url)
    settings = get_settings()
    message = str(exc) if settings.is_development else "An unexpected error occurred"
    return _error_response(code="INTERNAL_ERROR", message=message, status_code=500)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="TradeSignal AI",
        description="Automated Forex and Gold trade signal generation API",
        version="0.1.0",
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
        openapi_url="/api/openapi.json" if settings.is_development else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(signals.router, prefix="/api/v1")
    app.include_router(pairs.router, prefix="/api/v1")
    app.include_router(analysis.router, prefix="/api/v1")

    return app


app = create_app()
