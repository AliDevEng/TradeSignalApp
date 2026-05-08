import platform
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(tags=["Health"])

APP_VERSION = "0.1.0"


class ComponentStatus(BaseModel):
    status: str
    detail: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime
    python_version: str
    components: dict[str, ComponentStatus]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API liveness and component status",
)
async def health_check() -> HealthResponse:
    settings = get_settings()

    components: dict[str, ComponentStatus] = {
        "database": ComponentStatus(status="not_configured"),
        "scheduler": ComponentStatus(status="not_configured"),
    }

    overall = (
        "ok"
        if all(c.status in ("ok", "not_configured") for c in components.values())
        else "degraded"
    )

    return HealthResponse(
        status=overall,
        version=APP_VERSION,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
        python_version=platform.python_version(),
        components=components,
    )
