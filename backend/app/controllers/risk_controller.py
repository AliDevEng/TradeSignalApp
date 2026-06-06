"""The risk controller — stateless position sizing for the frontend.

This is the thinnest controller in the project on purpose: position sizing is a
pure calculation with no persistence, so the controller's only jobs are resolving
the instrument's :class:`ContractSpec` (raising the standard
:class:`ResourceNotFoundError` for an unknown symbol, mapped to a 404 in one
place) and mapping the pure service's value objects onto the wire schema. No
session, no repositories, no account data is stored.

Layering: imports services and schemas only; never ``app.views`` or ``fastapi``.
"""

from __future__ import annotations

from app.controllers.exceptions import ResourceNotFoundError
from app.schemas.risk import (
    PositionSizeRequest,
    PositionSizeResponse,
    TakeProfitProjectionResponse,
)
from app.services.risk import compute_position_size, get_contract_spec


class RiskController:
    """Serves stateless position-size calculations."""

    def size_position(self, request: PositionSizeRequest) -> PositionSizeResponse:
        """Size a position for the request, or raise if the instrument is unknown.

        The request schema has already enforced the field-level invariants
        (positive balance/risk/prices, stop ≠ entry), so the pure sizer cannot
        raise here in practice; the spec lookup is the only resolution step.
        """
        spec = get_contract_spec(request.pair)
        if spec is None:
            raise ResourceNotFoundError("pair", request.pair)

        result = compute_position_size(
            account_balance=request.account_balance,
            risk_percent=request.risk_percent,
            entry=request.entry,
            stop_loss=request.stop_loss,
            take_profits=request.take_profits,
            spec=spec,
        )

        return PositionSizeResponse(
            pair=spec.symbol,
            quote_currency=spec.quote_currency,
            contract_size=spec.contract_size,
            min_lot=spec.min_lot,
            lot_step=spec.lot_step,
            requested_risk_amount=result.requested_risk_amount,
            stop_distance=result.stop_distance,
            lots=result.lots,
            units=result.units,
            risk_amount=result.risk_amount,
            position_value=result.position_value,
            pip_value=result.pip_value,
            take_profits=[
                TakeProfitProjectionResponse(
                    price=tp.price,
                    distance=tp.distance,
                    risk_reward=tp.risk_reward,
                    profit_amount=tp.profit_amount,
                )
                for tp in result.take_profits
            ],
        )
