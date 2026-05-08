from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.views import analysis, health, pairs, signals


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: DB pool initialisation and scheduler start wired in Iteration 2–3
    yield
    # Shutdown: graceful teardown wired in Iteration 3


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

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(signals.router, prefix="/api/v1")
    app.include_router(pairs.router, prefix="/api/v1")
    app.include_router(analysis.router, prefix="/api/v1")

    return app


app = create_app()
