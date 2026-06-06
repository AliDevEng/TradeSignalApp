"""FastAPI application factory and global exception handlers.

The factory pattern (`create_app`) keeps app construction side-effect free so
tests can build isolated instances with custom settings overrides. The bottom
of the module exposes `app` for `uvicorn app.main:app`.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import Settings, get_settings
from app.controllers import AnalysisController, OutcomeController
from app.database import Database
from app.error_handlers import register_exception_handlers
from app.logging_config import configure_logging
from app.services.ai import AIProvider, build_ai_provider
from app.services.calendar import (
    EconomicCalendarProvider,
    build_economic_calendar_provider,
)
from app.services.events import EventBus, build_event_bus
from app.services.market_data import (
    CachingMarketDataProvider,
    MarketDataProvider,
    build_market_data_provider,
)
from app.services.notifications import (
    NotificationDispatcher,
    Notifier,
    build_notifier,
    build_preferences,
)
from app.tasks import ANALYSIS_JOB_ID, OUTCOME_JOB_ID, AnalysisJob, OutcomeJob, Scheduler
from app.views import api_v1_router

logger = logging.getLogger(__name__)


def _build_database(settings: Settings) -> Database:
    return Database(
        url=settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle_seconds=settings.database_pool_recycle_seconds,
        pool_pre_ping=True,
        echo=settings.database_echo,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    database: Database = app.state.database
    logger.info(
        "Starting TradeSignal AI v%s | env=%s | ai_provider=%s | pairs=%s",
        __version__,
        settings.app_env,
        settings.ai_provider,
        ",".join(settings.active_pairs),
    )

    # External clients live for the serving lifetime — constructed here (not in
    # create_app) so that lightweight unit tests, which build an app without
    # entering the lifespan, never spin up real SDK/HTTP clients.
    #
    # The market-data provider is wrapped in a TTL cache so slow timeframes
    # (4h/1d) are not re-fetched every cycle — the dominant cost against the
    # provider's per-minute budget. The cache is itself a MarketDataProvider, so
    # the controller is unchanged; ``aclose`` delegates to the wrapped vendor.
    market_data: MarketDataProvider = CachingMarketDataProvider(
        build_market_data_provider(settings)
    )
    ai_provider: AIProvider = build_ai_provider(settings)
    # News awareness: a config-driven calendar (off by default → the null
    # provider, so the pipeline is unchanged unless explicitly enabled).
    economic_calendar: EconomicCalendarProvider = build_economic_calendar_provider(settings)
    # Real-time spine: a process-local event bus the pipelines publish to and the
    # SSE endpoint + notification dispatcher consume from. Always constructed (it
    # is cheap and inert without subscribers) so the stream endpoint always works.
    event_bus: EventBus = build_event_bus(settings)
    # Off-platform delivery: a config-driven notifier (off by default → the null
    # notifier) driven by a background dispatcher that consumes the event bus.
    notifier: Notifier = build_notifier(settings)
    notification_dispatcher = NotificationDispatcher(
        bus=event_bus,
        notifier=notifier,
        preferences=build_preferences(settings),
    )
    scheduler = Scheduler(
        timezone=settings.scheduler_timezone,
        misfire_grace_seconds=settings.scheduler_misfire_grace_seconds,
    )
    app.state.market_data_provider = market_data
    app.state.ai_provider = ai_provider
    app.state.economic_calendar = economic_calendar
    app.state.event_bus = event_bus
    app.state.notifier = notifier
    app.state.notification_dispatcher = notification_dispatcher
    app.state.scheduler = scheduler

    # The analysis controller is the pipeline. It manages its own database
    # sessions (it takes the Database adapter, not a request session) because a
    # run is a minutes-long background unit of work — which is exactly what makes
    # the same instance reusable from a future manual-trigger endpoint.
    analysis_controller = AnalysisController(
        database=database,
        market_data=market_data,
        ai_provider=ai_provider,
        settings=settings,
        economic_calendar=economic_calendar,
        event_bus=event_bus,
    )
    app.state.analysis_controller = analysis_controller

    # The outcome controller is the measurement pipeline: it re-checks open
    # signals against fresh candles. Like the analysis controller it owns its own
    # sessions (background unit of work, no request behind it) and is reused for
    # every sweep.
    outcome_controller = OutcomeController(
        database=database,
        market_data=market_data,
        settings=settings,
        event_bus=event_bus,
    )
    app.state.outcome_controller = outcome_controller

    # Register the analysis cadence with the real pipeline. `run_scheduled`
    # matches the job's `() -> Awaitable[None]` contract; the job wraps it with
    # error containment so a crashing cycle never kills the schedule.
    analysis_job = AnalysisJob(analysis_controller.run_scheduled)
    scheduler.add_interval_job(
        analysis_job.run,
        minutes=settings.analysis_interval_minutes,
        job_id=ANALYSIS_JOB_ID,
        name="Scheduled market analysis",
    )
    # The outcome sweep runs on its own (tighter) cadence so closes are detected
    # promptly without coupling to the heavier analysis interval.
    outcome_job = OutcomeJob(outcome_controller.run_scheduled)
    scheduler.add_interval_job(
        outcome_job.run,
        minutes=settings.outcome_interval_minutes,
        job_id=OUTCOME_JOB_ID,
        name="Scheduled outcome tracking",
    )
    if settings.scheduler_enabled:
        scheduler.start()
    else:
        logger.info("Scheduler disabled by configuration (scheduler_enabled=false)")

    # Start consuming events for off-platform delivery only when notifications are
    # enabled; otherwise the notifier is the null one and a running loop would be
    # pure overhead. The SSE stream needs no such task — it subscribes per request.
    if settings.notifications_enabled:
        notification_dispatcher.start()
    else:
        logger.info("Notifications disabled by configuration (notifications_enabled=false)")

    try:
        yield
    finally:
        # Reverse order of acquisition; each step guarded so one failure does
        # not abort the rest of the teardown.
        scheduler.shutdown(wait=False)
        await notification_dispatcher.stop()
        await economic_calendar.aclose()
        await ai_provider.aclose()
        await market_data.aclose()
        logger.info("Disposing database engine")
        await database.dispose()
        logger.info("Shutting down TradeSignal AI")


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
    # The engine is constructed eagerly but does NOT open connections —
    # asyncpg connects lazily on the first query. This keeps `create_app`
    # synchronous (tests can build apps without an event loop) while still
    # giving us a single, disposable Database for the app's lifetime.
    app.state.settings = settings
    app.state.database = _build_database(settings)

    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)

    app.include_router(api_v1_router)

    return app


app = create_app()
