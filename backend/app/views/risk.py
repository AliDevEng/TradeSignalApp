"""Risk router — stateless position sizing for a trade idea.

Thin, like every view: it accepts the validated request body and wraps the
controller's result in the shared response envelope. All arithmetic lives in the
pure sizing service; this router imports controllers and schemas only, and stores
nothing — no account data crosses into persistence.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.dependencies import RiskControllerDep
from app.schemas.common import APIResponse
from app.schemas.risk import PositionSizeRequest, PositionSizeResponse

router = APIRouter(prefix="/risk", tags=["Risk"])


@router.post(
    "/position-size",
    response_model=APIResponse[PositionSizeResponse],
    summary="Size a position from account balance, risk %, entry and stop",
)
async def position_size(
    payload: PositionSizeRequest,
    controller: RiskControllerDep,
) -> APIResponse[PositionSizeResponse]:
    return APIResponse(data=controller.size_position(payload))
