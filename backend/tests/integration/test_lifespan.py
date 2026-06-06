"""Integration test for the application lifespan wiring (Iteration 3).

Unlike the rest of the suite, this test deliberately *enters* the lifespan so
the external service clients and the scheduler are actually constructed,
started, and torn down. The SDK clients are built with dummy keys but never
make a network call (no analysis cycle fires inside the test window), so this
stays hermetic.
"""

from __future__ import annotations

import asyncio

from app.config import Settings
from app.main import ANALYSIS_JOB_ID, OUTCOME_JOB_ID, create_app


def _settings(**overrides) -> Settings:
    base = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "ai_api_key": "k",
        "twelve_data_api_key": "k",
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


async def test_lifespan_constructs_and_starts_services():
    app = create_app(_settings())
    async with app.router.lifespan_context(app):
        state = app.state
        assert state.market_data_provider is not None
        assert state.ai_provider is not None
        assert state.scheduler.running is True
        # Both cadences are registered under their shared job ids.
        assert state.scheduler.get_job(ANALYSIS_JOB_ID) is not None
        assert state.scheduler.get_job(OUTCOME_JOB_ID) is not None
        # The outcome controller is constructed for the sweep + any future endpoint.
        assert state.outcome_controller is not None

    # Shutdown must stop the scheduler. AsyncIOScheduler finalises its stop on
    # the next loop tick, so yield once before observing the flag.
    await asyncio.sleep(0)
    assert app.state.scheduler.running is False


async def test_lifespan_constructs_event_bus_and_notifications_off_by_default():
    app = create_app(_settings())
    async with app.router.lifespan_context(app):
        state = app.state
        # The event bus always exists (the stream endpoint always works)…
        assert state.event_bus is not None
        # …but the notifier is the null one and the dispatcher is not running
        # while notifications are disabled (the default).
        assert state.notifier.provider_name == "null"
        assert state.notification_dispatcher.running is False


async def test_lifespan_starts_dispatcher_when_notifications_enabled():
    app = create_app(
        _settings(
            notifications_enabled=True,
            telegram_bot_token="token",
            telegram_chat_id="123",
        )
    )
    async with app.router.lifespan_context(app):
        state = app.state
        assert state.notifier.provider_name == "telegram"
        assert state.notification_dispatcher.running is True

    # Shutdown cancels the dispatcher task.
    await asyncio.sleep(0)
    assert app.state.notification_dispatcher.running is False


async def test_lifespan_respects_scheduler_disabled():
    app = create_app(_settings(scheduler_enabled=False))
    async with app.router.lifespan_context(app):
        # Job is still registered (intent is recorded) but dispatching is off.
        assert app.state.scheduler.get_job(ANALYSIS_JOB_ID) is not None
        assert app.state.scheduler.running is False


async def test_lifespan_health_reports_running_components():
    """With the lifespan active, health surfaces scheduler + providers as ok."""
    from httpx import ASGITransport, AsyncClient

    app = create_app(_settings())
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            components = (await ac.get("/api/v1/health")).json()["components"]

    assert components["scheduler"]["status"] == "ok"
    assert components["market_data"]["status"] == "ok"
    assert components["ai_provider"]["status"] == "ok"
