"""Performance router — the aggregated track record for the frontend dashboard.

Thin, like every view: it translates HTTP (query params, the ``from``/``to``
window) and wraps the controller's report in the shared response envelope. All
aggregation and ORM→wire mapping lives in the
:class:`~app.controllers.performance_controller.PerformanceController` and the
pure performance service; this router imports controllers and schemas only.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from app.dependencies import PerformanceControllerDep
from app.schemas.common import APIResponse
from app.schemas.performance import PerformanceResponse
from app.schemas.signal import SignalType

router = APIRouter(prefix="/performance", tags=["Performance"])


@router.get(
    "",
    response_model=APIResponse[PerformanceResponse],
    summary="Aggregated track record (summary, calibration, equity curve)",
)
async def get_performance(
    controller: PerformanceControllerDep,
    pair: str | None = Query(
        default=None,
        description="Filter by pair symbol (e.g. XAUUSD). 404 if the symbol is unknown.",
    ),
    signal_type: SignalType | None = Query(
        default=None,
        description="Filter by trade style (scalp/swing).",
    ),
    from_: datetime | None = Query(
        default=None,
        alias="from",
        description="Only include signals closed at/after this time (ISO 8601).",
    ),
    to: datetime | None = Query(
        default=None,
        alias="to",
        description="Only include signals closed at/before this time (ISO 8601).",
    ),
) -> APIResponse[PerformanceResponse]:
    report = await controller.get_performance(
        pair_symbol=pair,
        signal_type=signal_type,
        start=from_,
        end=to,
    )
    return APIResponse(data=report)
