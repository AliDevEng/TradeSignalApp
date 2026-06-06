"""Wire-format models for the risk / position-sizing endpoint.

Transport-agnostic (pydantic + stdlib only): the pure sizing service speaks value
objects, and the controller maps them onto these schemas. Money and prices are
``Decimal`` and serialise to JSON **strings** — the same "never float for prices"
discipline the rest of the API keeps. ``risk_reward`` is a ratio (a statistic, not
money) but is kept ``Decimal`` so it round-trips at a fixed scale rather than
picking up float noise.

The request carries no account identity and nothing is persisted — sizing is a
stateless calculation over values the client already holds.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

# A take-profit price must be positive; at most three rungs (TP1/TP2/TP3), matching
# the signal model.
_Price = Annotated[Decimal, Field(gt=0)]


class PositionSizeRequest(BaseModel):
    """Inputs for a single position-size calculation.

    ``risk_percent`` is a percentage (``1`` = 1% of balance). ``entry`` and
    ``stop_loss`` define the risk; ``take_profits`` are optional reward targets.
    """

    pair: str = Field(min_length=1, description="Instrument symbol, e.g. XAUUSD.")
    account_balance: Decimal = Field(gt=0, description="Account equity in the quote currency.")
    risk_percent: Decimal = Field(gt=0, le=100, description="Percent of balance to risk (1 = 1%).")
    entry: _Price = Field(description="Planned entry price.")
    stop_loss: _Price = Field(description="Protective stop price.")
    take_profits: list[_Price] = Field(
        default_factory=list, max_length=3, description="Up to three take-profit prices."
    )

    @model_validator(mode="after")
    def _stop_differs_from_entry(self) -> PositionSizeRequest:
        # A zero-distance stop has no definable risk to size against; reject it at
        # the edge as a 422 rather than letting the pure sizer raise.
        if self.entry == self.stop_loss:
            raise ValueError("stop_loss must differ from entry")
        return self


class TakeProfitProjectionResponse(BaseModel):
    """The reward picture for one take-profit at the sized position."""

    price: Decimal
    distance: Decimal = Field(description="Absolute price distance from entry.")
    risk_reward: Decimal = Field(description="Reward:risk ratio against the stop distance.")
    profit_amount: Decimal = Field(description="Account-currency profit if this TP is hit.")


class PositionSizeResponse(BaseModel):
    """A sized position: the order, its real risk, and the reward to each TP."""

    pair: str
    quote_currency: str
    contract_size: Decimal
    min_lot: Decimal
    lot_step: Decimal
    requested_risk_amount: Decimal = Field(description="Balance x risk% — the intended risk.")
    stop_distance: Decimal
    lots: Decimal = Field(
        description="Lot size, rounded down to the lot step (0 if not affordable)."
    )
    units: Decimal = Field(description="Base units = lots x contract size.")
    risk_amount: Decimal = Field(description="Actual loss at the stop for the sized lots.")
    position_value: Decimal = Field(description="Notional value = units x entry.")
    pip_value: Decimal = Field(description="Value of one pip move for the sized position.")
    take_profits: list[TakeProfitProjectionResponse]
