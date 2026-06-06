"""Unit tests for the risk / position-sizing service and controller.

The sizer is pure, so its correctness is tested directly: feed it an account + a
trade, assert the lots, the real risk, and the reward to each TP. The two safety
properties get their own tests — rounding **down** to the lot step never exceeds
the risk budget, and a trade too small to place at the step rounds to zero rather
than over-risking. The controller test covers the only non-pure step: an unknown
instrument raises the standard not-found error.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from app.controllers.exceptions import ResourceNotFoundError
from app.controllers.risk_controller import RiskController
from app.schemas.risk import PositionSizeRequest
from app.services.risk import (
    PositionSizingError,
    compute_position_size,
    get_contract_spec,
)

XAUUSD = get_contract_spec("XAUUSD")
assert XAUUSD is not None


# ── Contract spec lookup ────────────────────────────────────────────────────


def test_get_contract_spec_is_case_insensitive():
    assert get_contract_spec("xauusd") is XAUUSD


def test_get_contract_spec_unknown_returns_none():
    assert get_contract_spec("EURUSD") is None


def test_pip_value_per_lot_derives_from_contract_size_and_pip():
    assert XAUUSD.pip_value_per_lot == Decimal("1")  # 100 oz * $0.01


# ── Sizing maths ────────────────────────────────────────────────────────────


def test_sizes_a_clean_position_with_rr_and_profit_per_tp():
    result = compute_position_size(
        account_balance=Decimal("10000"),
        risk_percent=Decimal("1"),
        entry=Decimal("2000"),
        stop_loss=Decimal("1990"),
        take_profits=[Decimal("2020"), Decimal("2015")],
        spec=XAUUSD,
    )

    assert result.requested_risk_amount == Decimal("100.00")
    assert result.stop_distance == Decimal("10")
    assert result.lots == Decimal("0.10")
    assert result.units == Decimal("10.00")  # 0.10 * 100
    assert result.risk_amount == Decimal("100.00")
    assert result.position_value == Decimal("20000.00")
    assert result.pip_value == Decimal("0.10")

    tp1, tp2 = result.take_profits
    assert (tp1.price, tp1.risk_reward, tp1.profit_amount) == (
        Decimal("2020"),
        Decimal("2.00"),
        Decimal("200.00"),
    )
    assert (tp2.risk_reward, tp2.profit_amount) == (Decimal("1.50"), Decimal("150.00"))


def test_sizes_a_short_using_absolute_distances():
    # Stop above entry, TP below — a short. Distances are absolute, so the lots
    # and R:R match the mirror-image long.
    result = compute_position_size(
        account_balance=Decimal("10000"),
        risk_percent=Decimal("1"),
        entry=Decimal("2000"),
        stop_loss=Decimal("2010"),
        take_profits=[Decimal("1980")],
        spec=XAUUSD,
    )
    assert result.lots == Decimal("0.10")
    assert result.take_profits[0].risk_reward == Decimal("2.00")


def test_rounds_lots_down_so_risk_never_exceeds_budget():
    result = compute_position_size(
        account_balance=Decimal("10000"),
        risk_percent=Decimal("1"),
        entry=Decimal("2000"),
        stop_loss=Decimal("1993"),  # stop distance 7 → raw lots 0.142857…
        spec=XAUUSD,
    )
    assert result.lots == Decimal("0.14")  # floored to the 0.01 step
    assert result.risk_amount == Decimal("98.00")  # ≤ the $100 budget
    assert result.risk_amount <= result.requested_risk_amount


def test_unaffordable_trade_rounds_to_zero_lots():
    result = compute_position_size(
        account_balance=Decimal("100"),
        risk_percent=Decimal("1"),  # $1 budget
        entry=Decimal("2000"),
        stop_loss=Decimal("1990"),  # one 0.01 lot already risks $10
        spec=XAUUSD,
    )
    assert result.lots == Decimal("0")
    assert result.units == Decimal("0")
    assert result.risk_amount == Decimal("0.00")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"account_balance": Decimal("0")},
        {"risk_percent": Decimal("0")},
        {"entry": Decimal("0")},
        {"stop_loss": Decimal("2000")},  # equal to entry → zero risk distance
    ],
)
def test_invalid_inputs_raise_position_sizing_error(kwargs):
    base = {
        "account_balance": Decimal("10000"),
        "risk_percent": Decimal("1"),
        "entry": Decimal("2000"),
        "stop_loss": Decimal("1990"),
        "spec": XAUUSD,
    }
    with pytest.raises(PositionSizingError):
        compute_position_size(**{**base, **kwargs})


# ── Controller ──────────────────────────────────────────────────────────────


def test_controller_maps_spec_and_result_onto_the_wire_schema():
    response = RiskController().size_position(
        PositionSizeRequest(
            pair="xauusd",
            account_balance=Decimal("10000"),
            risk_percent=Decimal("1"),
            entry=Decimal("2000"),
            stop_loss=Decimal("1990"),
            take_profits=[Decimal("2020")],
        )
    )
    assert response.pair == "XAUUSD"  # normalised from the spec
    assert response.quote_currency == "USD"
    assert response.contract_size == Decimal("100")
    assert response.lots == Decimal("0.10")
    assert response.take_profits[0].risk_reward == Decimal("2.00")


def test_controller_raises_not_found_for_unknown_pair():
    with pytest.raises(ResourceNotFoundError):
        RiskController().size_position(
            PositionSizeRequest(
                pair="EURUSD",
                account_balance=Decimal("10000"),
                risk_percent=Decimal("1"),
                entry=Decimal("2000"),
                stop_loss=Decimal("1990"),
            )
        )
