"""Signals router — the read API the frontend paginates over.

Views are thin on purpose: they translate HTTP (path/query params, pagination,
status codes) and wrap controller output in the shared response envelope. All
business logic — filtering, ORM→wire mapping, not-found semantics — lives in the
:class:`~app.controllers.signal_controller.SignalController`. The router imports
controllers and schemas only; it never touches a repository or the database
directly (see the layering table in ``backend/README.md``).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.dependencies import PaginationDep, SignalControllerDep
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.signal import (
    SignalDirection,
    SignalOutcome,
    SignalResponse,
    SignalResultFilter,
    SignalSort,
    SignalStatusFilter,
    SignalType,
)

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get(
    "",
    response_model=PaginatedResponse[SignalResponse],
    summary="List signals (paginated, filterable)",
)
async def list_signals(
    controller: SignalControllerDep,
    pagination: PaginationDep,
    pair: str | None = Query(
        default=None,
        description="Filter by pair symbol (e.g. EURUSD). 404 if the symbol is unknown.",
    ),
    run_id: uuid.UUID | None = Query(
        default=None,
        description="Filter to signals produced by one analysis run.",
    ),
    signal_type: SignalType | None = Query(
        default=None,
        description="Filter by trade style (scalp/swing).",
    ),
    outcome: SignalOutcome | None = Query(
        default=None,
        description="Filter by exact outcome (open/hit_tp1.../hit_sl/expired/cancelled).",
    ),
    direction: SignalDirection | None = Query(
        default=None,
        description="Filter by direction (buy/sell/neutral).",
    ),
    status: SignalStatusFilter | None = Query(
        default=None,
        description="Lifecycle status (active/watchlist/expired), derived from direction + expiry.",
    ),
    result: SignalResultFilter | None = Query(
        default=None,
        description="Result category (open/win/loss/expired); a 'win' is any take-profit.",
    ),
    sort: SignalSort | None = Query(
        default=None,
        description="Order by confidence, newest (default), or symbol.",
    ),
) -> PaginatedResponse[SignalResponse]:
    page = await controller.list_signals(
        offset=pagination.offset,
        limit=pagination.limit,
        pair_symbol=pair,
        analysis_run_id=run_id,
        signal_type=signal_type,
        outcome=outcome,
        direction=direction,
        status=status,
        result=result,
        sort=sort,
    )
    return PaginatedResponse(
        data=page.items,
        pagination=PaginationMeta(
            total=page.total,
            page=pagination.page,
            per_page=pagination.per_page,
        ),
    )


@router.get(
    "/{signal_id}",
    response_model=APIResponse[SignalResponse],
    summary="Get a single signal by id",
)
async def get_signal(
    signal_id: uuid.UUID,
    controller: SignalControllerDep,
) -> APIResponse[SignalResponse]:
    signal = await controller.get_signal(signal_id)
    return APIResponse(data=signal)
