"""Position sizing — a *pure* function from a trade idea + an account to an exact,
risk-bounded order.

This is the risk counterpart to the other pure services (the outcome evaluator,
the performance calculator): given an account balance, a risk budget, the entry
and stop, and the instrument's :class:`ContractSpec`, it returns the lot size that
risks no more than the budget, plus the R:R and projected profit to each
take-profit. Deterministic and IO-free — no DB, no network, no account is
stored — so the arithmetic is unit-tested directly and the endpoint built on it
stays stateless.

Two safety decisions are baked in. Lots are rounded **down** to the broker's lot
step, so rounding can only ever risk *less* than the budget, never more (a
position too small to take at the step rounds to zero rather than silently
over-risking). And ``Decimal`` is used throughout — money and prices never touch
float.

Currency assumption: P&L is in the instrument's quote currency, which is taken to
be the account currency (true for XAUUSD→USD, the current focus). A
cross-currency account would need an FX conversion factor; that is a deliberate
future extension, not silently wrong maths.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app.services.risk.contracts import ContractSpec

_MONEY_Q = Decimal("0.01")
_RR_Q = Decimal("0.01")
_ZERO = Decimal("0")


class PositionSizingError(ValueError):
    """The inputs cannot yield a valid position size (e.g. stop equals entry)."""


@dataclass(frozen=True, slots=True)
class TakeProfitProjection:
    """The reward picture for one take-profit at the sized position."""

    price: Decimal
    distance: Decimal
    risk_reward: Decimal
    profit_amount: Decimal


@dataclass(frozen=True, slots=True)
class PositionSize:
    """The sizing result: the order, its real risk, and the reward to each TP."""

    requested_risk_amount: Decimal
    stop_distance: Decimal
    lots: Decimal
    units: Decimal
    risk_amount: Decimal
    position_value: Decimal
    pip_value: Decimal
    take_profits: list[TakeProfitProjection]


def _money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY_Q, rounding=ROUND_HALF_UP)


def compute_position_size(
    *,
    account_balance: Decimal,
    risk_percent: Decimal,
    entry: Decimal,
    stop_loss: Decimal,
    take_profits: Sequence[Decimal] = (),
    spec: ContractSpec,
) -> PositionSize:
    """Size a position so the loss at the stop is at most ``risk_percent`` of balance.

    ``risk_percent`` is a percentage (``1`` = 1%, not ``0.01``). Distances are
    absolute, so the same maths serves long and short. Raises
    :class:`PositionSizingError` for inputs that can't be sized (non-positive
    balance/risk, or a stop equal to the entry — a zero-risk trade is undefined);
    the API schema rejects these at the edge, so this is defence-in-depth.
    """
    if account_balance <= 0:
        raise PositionSizingError("account balance must be positive")
    if risk_percent <= 0:
        raise PositionSizingError("risk percent must be positive")
    if entry <= 0:
        raise PositionSizingError("entry price must be positive")

    stop_distance = abs(entry - stop_loss)
    if stop_distance == 0:
        raise PositionSizingError("stop loss must differ from the entry price")

    requested_risk = account_balance * (risk_percent / Decimal("100"))

    # Loss for one standard lot if the stop is hit, in the quote currency.
    risk_per_lot = stop_distance * spec.contract_size
    raw_lots = requested_risk / risk_per_lot

    # Round DOWN to the broker's lot step so rounding can only reduce risk. A
    # position too small to place at the step rounds to zero (not affordable at
    # this risk), which the caller can surface rather than over-risk.
    steps = (raw_lots / spec.lot_step).to_integral_value(rounding=ROUND_DOWN)
    lots = steps * spec.lot_step

    units = lots * spec.contract_size
    risk_amount = lots * risk_per_lot
    position_value = units * entry
    pip_value = lots * spec.pip_value_per_lot

    projections = [
        _project_take_profit(tp, entry=entry, stop_distance=stop_distance, lots=lots, spec=spec)
        for tp in take_profits
    ]

    return PositionSize(
        requested_risk_amount=_money(requested_risk),
        stop_distance=stop_distance,
        lots=lots,
        units=units,
        risk_amount=_money(risk_amount),
        position_value=_money(position_value),
        pip_value=_money(pip_value),
        take_profits=projections,
    )


def _project_take_profit(
    price: Decimal,
    *,
    entry: Decimal,
    stop_distance: Decimal,
    lots: Decimal,
    spec: ContractSpec,
) -> TakeProfitProjection:
    distance = abs(price - entry)
    # stop_distance is guaranteed non-zero by the caller's guard.
    risk_reward = (distance / stop_distance).quantize(_RR_Q, rounding=ROUND_HALF_UP)
    profit = lots * spec.contract_size * distance
    return TakeProfitProjection(
        price=price,
        distance=distance,
        risk_reward=risk_reward,
        profit_amount=_money(profit),
    )
