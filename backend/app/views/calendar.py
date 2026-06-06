"""Calendar router — upcoming high-impact economic events for the news banner.

Thin like every view: it translates the ``within_hours`` query window and wraps
the controller's report in the shared envelope. The feature is guarded by
``ECONOMIC_CALENDAR_ENABLED`` — when off, the provider is the null one and this
returns ``enabled=false`` with no events (behaving exactly as before the feature
existed), so the endpoint is always safe to call.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.dependencies import CalendarControllerDep
from app.schemas.calendar import CalendarResponse
from app.schemas.common import APIResponse

router = APIRouter(prefix="/calendar", tags=["Calendar"])


@router.get(
    "",
    response_model=APIResponse[CalendarResponse],
    summary="Upcoming high-impact economic events",
)
async def get_calendar(
    controller: CalendarControllerDep,
    within_hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description="Look-ahead window in hours (1..168; default 24).",
    ),
) -> APIResponse[CalendarResponse]:
    report = await controller.get_upcoming(within_hours=within_hours)
    return APIResponse(data=report)
