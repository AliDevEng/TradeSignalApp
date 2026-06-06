"""Unit tests for the pure market-structure analyzer.

Structure detection is deterministic geometry, so these assert exact pivots and
levels on hand-built series rather than statistical properties.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services.market_data import Candle
from app.services.structure import StructureAnalyzer, StructureSnapshot, find_pivots


def _candles(values: list[tuple[float, float, float, float]]) -> list[Candle]:
    """Build a candle series from (open, high, low, close) tuples."""
    base = datetime(2024, 1, 1, tzinfo=UTC)
    return [
        Candle(
            timestamp=base + timedelta(hours=i),
            open=Decimal(str(o)),
            high=Decimal(str(h)),
            low=Decimal(str(low)),
            close=Decimal(str(c)),
        )
        for i, (o, h, low, c) in enumerate(values)
    ]


# ── find_pivots ───────────────────────────────────────────────────────────────


def test_find_pivot_high_picks_the_local_maximum():
    # Index 2 (value 5) is the strict max of [1,3,5,3,1].
    assert find_pivots([1, 3, 5, 3, 1], left=2, right=2, high=True) == [2]


def test_find_pivot_low_picks_the_local_minimum():
    assert find_pivots([9, 7, 2, 7, 9], left=2, right=2, high=False) == [2]


def test_find_pivots_needs_a_full_window_on_both_sides():
    # The max sits at the very end with no right-side confirmation → no pivot.
    assert find_pivots([1, 2, 3, 4, 5], left=2, right=2, high=True) == []


def test_find_pivots_ignores_plateaus():
    # A flat top is not a strict pivot (>= on either side disqualifies it).
    assert find_pivots([1, 5, 5, 5, 1], left=1, right=1, high=True) == []


# ── StructureAnalyzer ─────────────────────────────────────────────────────────


def test_too_few_candles_yields_an_empty_snapshot():
    snap = StructureAnalyzer().analyze(_candles([(1, 1, 1, 1)] * 3))
    assert snap == StructureSnapshot()
    assert snap.is_empty


def test_detects_swing_high_low_and_nearest_levels():
    # A clear peak at index 2 (high 1.20) and trough at index 6 (low 1.00),
    # last close 1.10 sits between them.
    candles = _candles(
        [
            (1.10, 1.12, 1.08, 1.11),
            (1.11, 1.15, 1.10, 1.14),
            (1.14, 1.20, 1.13, 1.16),  # swing high 1.20
            (1.16, 1.17, 1.12, 1.13),
            (1.13, 1.14, 1.05, 1.07),
            (1.07, 1.08, 1.02, 1.04),
            (1.04, 1.05, 1.00, 1.03),  # swing low 1.00
            (1.03, 1.09, 1.02, 1.08),
            (1.08, 1.13, 1.07, 1.10),  # last close 1.10
        ]
    )
    snap = StructureAnalyzer().analyze(candles)

    assert snap.swing_high == Decimal("1.20")
    assert snap.swing_low == Decimal("1.00")
    # Nearest resistance is the lowest pivot high above the close; nearest
    # support the highest pivot low below it.
    assert snap.nearest_resistance == Decimal("1.20")
    assert snap.nearest_support == Decimal("1.00")
    assert snap.range_high == Decimal("1.20")
    assert snap.range_low == Decimal("1.00")


def test_to_dict_is_json_safe_strings():
    snap = StructureSnapshot(swing_high=Decimal("1.2345"), swing_low=None)
    out = snap.to_dict()
    assert out["swing_high"] == "1.2345"
    assert out["swing_low"] is None
