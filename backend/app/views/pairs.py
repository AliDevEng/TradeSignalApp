"""Pairs router — the tradable-instrument lookup API.

Pairs are small and enumerable, so the list endpoint is unpaginated. The
``{symbol}/signals`` sub-resource reuses the signal controller's
``list_latest_for_pair`` rather than duplicating that query here — the pair's
existence check and ORM→wire mapping already live in the controller layer.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.dependencies import PairControllerDep, SignalControllerDep
from app.schemas.common import APIResponse
from app.schemas.pair import PairResponse
from app.schemas.signal import SignalResponse

router = APIRouter(prefix="/pairs", tags=["Pairs"])


@router.get(
    "",
    response_model=APIResponse[list[PairResponse]],
    summary="List trading pairs",
)
async def list_pairs(
    controller: PairControllerDep,
    include_inactive: bool = Query(
        default=False,
        description="Include soft-disabled pairs (default: active only).",
    ),
) -> APIResponse[list[PairResponse]]:
    pairs = await controller.list_pairs(include_inactive=include_inactive)
    return APIResponse(data=pairs)


@router.get(
    "/{symbol}",
    response_model=APIResponse[PairResponse],
    summary="Get a single pair by symbol",
)
async def get_pair(
    symbol: str,
    controller: PairControllerDep,
) -> APIResponse[PairResponse]:
    pair = await controller.get_pair(symbol)
    return APIResponse(data=pair)


@router.get(
    "/{symbol}/signals",
    response_model=APIResponse[list[SignalResponse]],
    summary="Latest signals for a pair",
)
async def list_pair_signals(
    symbol: str,
    controller: SignalControllerDep,
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="How many of the most-recent signals to return.",
    ),
) -> APIResponse[list[SignalResponse]]:
    signals = await controller.list_latest_for_pair(symbol, limit=limit)
    return APIResponse(data=signals)
