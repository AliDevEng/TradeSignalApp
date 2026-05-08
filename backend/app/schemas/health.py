from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ComponentState = Literal["ok", "degraded", "down", "not_configured"]
OverallState = Literal["ok", "degraded", "down"]


class ComponentStatus(BaseModel):
    status: ComponentState
    detail: str | None = None


class HealthResponse(BaseModel):
    status: OverallState
    version: str
    environment: str
    timestamp: datetime
    python_version: str
    components: dict[str, ComponentStatus] = Field(default_factory=dict)
