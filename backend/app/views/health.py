import platform
from datetime import UTC, datetime

from fastapi import APIRouter

from app import __version__
from app.config import SettingsDep
from app.dependencies import DatabaseDep
from app.schemas.health import ComponentStatus, HealthResponse, OverallState

router = APIRouter(tags=["Health"])


def _derive_overall(components: dict[str, ComponentStatus]) -> OverallState:
    """Worst-of aggregation; treats `not_configured` as benign (Iteration 1)."""
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


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API liveness and component status",
)
async def health_check(
    settings: SettingsDep,
    database: DatabaseDep,
) -> HealthResponse:
    # Components for scheduler / AI provider / market data wire in during
    # later iterations. Each probe runs sequentially today; once we have
    # multiple I/O-bound checks, parallelise with asyncio.gather.
    components: dict[str, ComponentStatus] = {
        "database": await _probe_database(database),
        "scheduler": ComponentStatus(status="not_configured"),
    }

    return HealthResponse(
        status=_derive_overall(components),
        version=__version__,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        python_version=platform.python_version(),
        components=components,
    )
