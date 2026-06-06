"""Unit tests for the indicator calculator.

These assert *structural* properties (which fields populate, value ranges,
NaN handling, determinism) rather than hand-computed indicator values — the
numeric correctness of RSI/MACD/etc. is pandas-ta-classic's responsibility,
not ours, and pinning exact floats would make the suite brittle against a
library patch release.
"""

from __future__ import annotations

import math
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.services.indicators import (
    MIN_CANDLES,
    IndicatorCalculator,
    IndicatorSnapshot,
    InsufficientDataError,
)
from app.services.indicators.calculator import _clean, classify_regime
from app.services.market_data import Candle


def _make_candles(n: int, *, seed: int = 1) -> list[Candle]:
    """A plausible ascending-ish random walk of ``n`` valid candles."""
    rng = random.Random(seed)
    base = datetime(2024, 1, 1, tzinfo=UTC)
    price = 1.1000
    candles: list[Candle] = []
    for i in range(n):
        price += rng.uniform(-0.002, 0.0025)
        close = price
        open_ = price - rng.uniform(-0.001, 0.001)
        high = max(open_, close) + rng.uniform(0.0001, 0.0015)
        low = min(open_, close) - rng.uniform(0.0001, 0.0015)
        candles.append(
            Candle(
                timestamp=base + timedelta(hours=i),
                open=Decimal(str(round(open_, 5))),
                high=Decimal(str(round(high, 5))),
                low=Decimal(str(round(low, 5))),
                close=Decimal(str(round(close, 5))),
            )
        )
    return candles


# ── _clean helper ────────────────────────────────────────────────────────────


def test_clean_collapses_nan_and_inf_to_none():
    assert _clean(float("nan")) is None
    assert _clean(float("inf")) is None
    assert _clean(float("-inf")) is None
    assert _clean(None) is None


def test_clean_rounds_finite_values():
    assert _clean(1.123456789123) == round(1.123456789123, 8)


# ── compute() ────────────────────────────────────────────────────────────────


def test_compute_rejects_insufficient_candles():
    calc = IndicatorCalculator()
    with pytest.raises(InsufficientDataError):
        calc.compute(_make_candles(MIN_CANDLES - 1))


def test_compute_populates_core_indicators():
    calc = IndicatorCalculator()
    snap = calc.compute(_make_candles(80))

    assert isinstance(snap, IndicatorSnapshot)
    assert snap.candles_analyzed == 80
    assert snap.last_close is not None
    # Core windows are satisfied by 80 candles.
    for field in ("rsi_14", "ema_20", "ema_50", "sma_20", "atr_14"):
        assert getattr(snap, field) is not None, field
    for field in ("macd", "macd_signal", "macd_histogram"):
        assert getattr(snap, field) is not None, field
    for field in ("bb_upper", "bb_middle", "bb_lower", "bb_percent"):
        assert getattr(snap, field) is not None, field
    # RSI is bounded; ATR is a positive distance.
    assert 0.0 <= snap.rsi_14 <= 100.0
    assert snap.atr_14 >= 0.0
    # Bollinger ordering must hold.
    assert snap.bb_lower <= snap.bb_middle <= snap.bb_upper


def test_compute_leaves_long_window_none_when_history_short():
    """EMA-200 needs far more than 80 bars; it must be None, not NaN."""
    snap = IndicatorCalculator().compute(_make_candles(80))
    assert snap.ema_200 is None


def test_compute_sets_as_of_to_latest_candle():
    candles = _make_candles(60)
    snap = IndicatorCalculator().compute(candles)
    assert snap.as_of == candles[-1].timestamp


def test_compute_sorts_unordered_input():
    candles = _make_candles(60)
    shuffled = candles[:]
    random.Random(7).shuffle(shuffled)
    snap = IndicatorCalculator().compute(shuffled)
    # Even with shuffled input, as_of is the chronologically latest candle.
    assert snap.as_of == max(c.timestamp for c in candles)


def test_compute_is_deterministic():
    candles = _make_candles(70)
    a = IndicatorCalculator().compute(candles)
    b = IndicatorCalculator().compute(candles)
    assert a.model_dump() == b.model_dump()


# ── trajectory + regime + divergence (Iteration 10 evidence enrichment) ───────


def test_trajectory_fields_populate_with_enough_history():
    snap = IndicatorCalculator().compute(_make_candles(80))
    # The "previous" reads are present so a consumer can see momentum *turning*.
    assert snap.rsi_14_prev is not None
    assert snap.macd_histogram_prev is not None


def test_regime_label_is_derived_from_adx():
    snap = IndicatorCalculator().compute(_make_candles(80))
    assert snap.adx_14 is not None
    assert snap.regime in {"trending", "ranging", "transitional"}


def test_classify_regime_thresholds():
    assert classify_regime(30.0) == "trending"
    assert classify_regime(25.0) == "trending"
    assert classify_regime(22.0) == "transitional"
    assert classify_regime(10.0) == "ranging"
    assert classify_regime(None) is None


def test_divergence_field_is_valid_or_none():
    snap = IndicatorCalculator().compute(_make_candles(80))
    assert snap.rsi_divergence in {"bullish", "bearish", None}


def test_diverges_detects_bullish_disagreement():
    # Two swing lows: price lower (10 → 8) while RSI higher (25 → 30) ⇒ bullish.
    prices = [None, None, 10.0, None, 8.0]
    rsis = [None, None, 25.0, None, 30.0]
    assert IndicatorCalculator._diverges([2, 4], prices, rsis, price_lower=True) is True


def test_diverges_false_when_rsi_agrees_with_price():
    prices = [10.0, 8.0]
    rsis = [25.0, 20.0]  # RSI also lower → no divergence
    assert IndicatorCalculator._diverges([0, 1], prices, rsis, price_lower=True) is False


def test_diverges_needs_two_pivots():
    assert IndicatorCalculator._diverges([3], [1.0], [50.0], price_lower=True) is False


# ── to_storage_dict() ────────────────────────────────────────────────────────


def test_to_storage_dict_is_json_safe():
    snap = IndicatorCalculator().compute(_make_candles(60))
    payload = snap.to_storage_dict()

    # as_of serialises to an ISO string for JSONB.
    assert isinstance(payload["as_of"], str)
    # No non-finite floats may leak into the column.
    for key, value in payload.items():
        if isinstance(value, float):
            assert math.isfinite(value), key
