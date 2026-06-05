"""Unit tests for :class:`PerformanceController` — the read-side aggregation service.

Exercised against ``AsyncMock`` repositories: the controller's job is
orchestration (resolve a symbol → id, cast the wire ``signal_type`` to the ORM
enum, drive the repo, hand the rows to the pure calculator, map the result to the
wire schema). The aggregation maths itself is proven in
``test_performance_calculator``; here we pin the boundary conversions and the
ORM→wire mapping.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from app.controllers.exceptions import ResourceNotFoundError
from app.controllers.performance_controller import PerformanceController
from app.models import SignalOutcome, SignalType
from app.schemas.performance import PerformanceResponse

from tests._factories import make_pair, make_signal

_FIXED_NOW = datetime(2026, 6, 4, 9, 0, tzinfo=UTC)


def _controller(*, signals: AsyncMock | None = None, pairs: AsyncMock | None = None):
    signals = signals or AsyncMock()
    pairs = pairs or AsyncMock()
    controller = PerformanceController(
        signals=signals,
        pairs=pairs,
        clock=lambda: _FIXED_NOW,
    )
    return controller, signals, pairs


def _closed_signal(*, realized_r: str, signal_type=SignalType.SWING, confidence: float = 0.7):
    return make_signal(
        signal_type=signal_type,
        confidence=confidence,
        outcome=SignalOutcome.HIT_TP1 if Decimal(realized_r) > 0 else SignalOutcome.HIT_SL,
        realized_r=Decimal(realized_r),
        closed_at=_FIXED_NOW,
    )


async def test_get_performance_returns_mapped_response():
    ctrl, signals, _ = _controller()
    signals.list_closed_for_performance.return_value = [
        _closed_signal(realized_r="2.0"),
        _closed_signal(realized_r="-1.0"),
    ]

    result = await ctrl.get_performance()

    assert isinstance(result, PerformanceResponse)
    assert result.overall.total == 2
    assert result.overall.wins == 1
    assert result.overall.total_r == Decimal("1.0000")
    assert result.generated_at == _FIXED_NOW
    # Both styles + all five calibration buckets always present.
    assert set(result.by_type) == {"scalp", "swing"}
    assert len(result.calibration) == 5
    assert len(result.equity_curve) == 2


async def test_get_performance_empty_set_is_zeroed_not_error():
    ctrl, signals, _ = _controller()
    signals.list_closed_for_performance.return_value = []

    result = await ctrl.get_performance()

    assert result.overall.total == 0
    assert result.overall.profit_factor is None
    assert result.equity_curve == []


async def test_get_performance_resolves_pair_symbol_to_id():
    pair = make_pair(id=11, symbol="XAUUSD")
    ctrl, signals, pairs = _controller()
    pairs.get_by_symbol.return_value = pair
    signals.list_closed_for_performance.return_value = []

    await ctrl.get_performance(pair_symbol="XAUUSD")

    pairs.get_by_symbol.assert_awaited_once_with("XAUUSD")
    assert signals.list_closed_for_performance.await_args.kwargs["pair_id"] == 11


async def test_get_performance_unknown_pair_raises_not_found():
    ctrl, _, pairs = _controller()
    pairs.get_by_symbol.return_value = None

    with pytest.raises(ResourceNotFoundError) as exc:
        await ctrl.get_performance(pair_symbol="NOPE")
    assert exc.value.resource == "pair"
    assert exc.value.identifier == "NOPE"


async def test_get_performance_casts_signal_type_to_model_enum():
    ctrl, signals, _ = _controller()
    signals.list_closed_for_performance.return_value = []

    await ctrl.get_performance(signal_type="scalp")

    assert signals.list_closed_for_performance.await_args.kwargs["signal_type"] is SignalType.SCALP


async def test_get_performance_forwards_date_window():
    ctrl, signals, _ = _controller()
    signals.list_closed_for_performance.return_value = []
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 6, 4, tzinfo=UTC)

    await ctrl.get_performance(start=start, end=end)

    kwargs = signals.list_closed_for_performance.await_args.kwargs
    assert kwargs["start"] == start
    assert kwargs["end"] == end


async def test_get_performance_applies_default_lookback_when_no_window():
    # No explicit from/to → the controller bounds the query to the recent window
    # rather than scanning all history.
    signals = AsyncMock()
    signals.list_closed_for_performance.return_value = []
    ctrl = PerformanceController(
        signals=signals,
        pairs=AsyncMock(),
        clock=lambda: _FIXED_NOW,
        default_lookback_days=30,
    )

    await ctrl.get_performance()

    kwargs = signals.list_closed_for_performance.await_args.kwargs
    assert kwargs["start"] == _FIXED_NOW - timedelta(days=30)
    assert kwargs["end"] is None


async def test_get_performance_lookback_zero_means_all_time():
    signals = AsyncMock()
    signals.list_closed_for_performance.return_value = []
    ctrl = PerformanceController(
        signals=signals,
        pairs=AsyncMock(),
        clock=lambda: _FIXED_NOW,
        default_lookback_days=0,
    )

    await ctrl.get_performance()

    assert signals.list_closed_for_performance.await_args.kwargs["start"] is None


async def test_get_performance_preserves_decimal_r():
    ctrl, signals, _ = _controller()
    signals.list_closed_for_performance.return_value = [_closed_signal(realized_r="2.7531")]

    result = await ctrl.get_performance()

    assert isinstance(result.overall.total_r, Decimal)
    assert result.equity_curve[0].cumulative_r == Decimal("2.7531")
