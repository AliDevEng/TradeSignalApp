import platform
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app import __version__
from app.config import SettingsDep
from app.dependencies import DatabaseDep
from app.schemas.health import ComponentStatus, HealthResponse, OverallState

router = APIRouter(tags=["Health"])


def _derive_overall(components: dict[str, ComponentStatus]) -> OverallState:
    """Worst-of aggregation; treats `not_configured` as benign."""
    statuses = {c.status for c in components.values()}
    if "down" in statuses:
        return "down"
    if "degraded" in statuses:
        return "degraded"
    return "ok"


async def _probe_database(database: DatabaseDep) -> ComponentStatus:
    if await database.healthcheck():
        return ComponentStatus(status="ok")
    return ComponentStatus(status="down", detail="Database unreachable")


def _scheduler_status(scheduler: object, *, enabled: bool) -> ComponentStatus:
    """Map the scheduler's runtime state to a component status.

    The four cases are distinct on purpose:
    - absent (e.g. app built without entering the lifespan) → not_configured
    - running → ok
    - present but stopped while it *should* be enabled → down (a real anomaly)
    - present but stopped because config disabled it → not_configured (benign)
    """
    if scheduler is None:
        return ComponentStatus(status="not_configured", detail="Scheduler not started")
    if getattr(scheduler, "running", False):
        return ComponentStatus(status="ok")
    if enabled:
        return ComponentStatus(status="down", detail="Scheduler enabled but not running")
    return ComponentStatus(status="not_configured", detail="Scheduler disabled by config")


def _notifications_status(
    notifier: object, dispatcher: object, *, enabled: bool
) -> ComponentStatus:
    """Map the notification subsystem's state to a component status.

    Mirrors the scheduler's four-case logic so "off by config" reads as benign
    (``not_configured``) while "should be running but isn't" reads as a real
    anomaly (``down``):
    - disabled by config                         → not_configured (benign)
    - absent (app built without lifespan)        → not_configured
    - enabled and the dispatcher is consuming     → ok
    - enabled but the dispatcher stopped/crashed  → down (a real anomaly)
    """
    if not enabled:
        return ComponentStatus(status="not_configured", detail="Notifications disabled by config")
    if notifier is None or dispatcher is None:
        return ComponentStatus(status="not_configured", detail="Notifications not initialised")
    if getattr(dispatcher, "running", False):
        return ComponentStatus(status="ok")
    return ComponentStatus(status="down", detail="Notifications enabled but dispatcher not running")


def _readiness(component: object, label: str) -> ComponentStatus:
    """Presence-based readiness for external providers.

    Health intentionally does *not* make a live API call here — probing a paid
    AI/market-data endpoint on every health check would burn rate-limit budget
    and could itself cause flapping. Presence means the client was constructed
    at startup and is ready to use.
    """
    if component is None:
        return ComponentStatus(status="not_configured", detail=f"{label} not initialised")
    return ComponentStatus(status="ok")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API liveness and component status",
)
async def health_check(
    settings: SettingsDep,
    database: DatabaseDep,
    request: Request,
) -> HealthResponse:
    state = request.app.state
    components: dict[str, ComponentStatus] = {
        "database": await _probe_database(database),
        "scheduler": _scheduler_status(
            getattr(state, "scheduler", None), enabled=settings.scheduler_enabled
        ),
        "market_data": _readiness(
            getattr(state, "market_data_provider", None), "Market data provider"
        ),
        "ai_provider": _readiness(getattr(state, "ai_provider", None), "AI provider"),
        "notifications": _notifications_status(
            getattr(state, "notifier", None),
            getattr(state, "notification_dispatcher", None),
            enabled=settings.notifications_enabled,
        ),
    }

    return HealthResponse(
        status=_derive_overall(components),
        version=__version__,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        python_version=platform.python_version(),
        components=components,
    )
