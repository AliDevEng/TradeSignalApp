"""Pure swing-structure detection over a candle series.

The analyzer is **pure**: candles in, a :class:`StructureSnapshot` out, no IO and
no hidden state — the same discipline the indicator calculator keeps. It reports
the levels that matter for framing a trade:

* the most recent confirmed **swing high / swing low** (a fractal pivot),
* the **nearest resistance above** and **nearest support below** the last close
  (so a stop has a real level to sit beyond, and a target a real level to aim
  at), and
* the **range high / low** over the lookback window (the box price is trading
  in).

These are handed to the model so "place the stop beyond structure" stops being a
contradiction with "do not invent levels": the structure is computed here,
deterministically, and the model anchors to it rather than hallucinating it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Protocol

from app.services.market_data.base import Candle

# A pivot is confirmed when it is the strict extreme of ``left`` bars before and
# ``right`` bars after it. ``right`` is what makes a pivot *confirmed* — it can
# only be declared once that many later bars have printed, so a pivot never
# repaints. Two-and-two is the standard short-swing fractal.
_PIVOT_LEFT: Final[int] = 2
_PIVOT_RIGHT: Final[int] = 2

# How many of the most-recent bars structure is read from. Bounded so the levels
# reflect *current* structure (and the scan stays O(window)), not ancient bars
# the price action has long since left behind.
_STRUCTURE_WINDOW: Final[int] = 120


class _Comparable(Protocol):
    def __lt__(self, other: object, /) -> bool: ...
    def __gt__(self, other: object, /) -> bool: ...


def find_pivots[T: _Comparable](
    values: Sequence[T], *, left: int, right: int, high: bool
) -> list[int]:
    """Indices of confirmed fractal pivots in ``values``.

    A pivot **high** at ``i`` is strictly greater than every one of the ``left``
    values before and ``right`` values after it; a pivot **low** is strictly
    less. Only indices with a full window on both sides are considered, so a
    returned pivot is always confirmed (never repaints on the next bar). Generic
    over any orderable value, so it serves both price structure (``Decimal``
    highs/lows) and indicator divergence (``float`` RSI/close).
    """
    n = len(values)
    pivots: list[int] = []
    for i in range(left, n - right):
        center = values[i]
        is_pivot = True
        for j in range(i - left, i + right + 1):
            if j == i:
                continue
            if high and values[j] >= center:
                is_pivot = False
                break
            if not high and values[j] <= center:
                is_pivot = False
                break
        if is_pivot:
            pivots.append(i)
    return pivots


@dataclass(frozen=True, slots=True)
class StructureSnapshot:
    """The latest structural levels for one timeframe. All ``None`` when the
    series is too short to confirm any pivot."""

    swing_high: Decimal | None = None
    swing_low: Decimal | None = None
    nearest_resistance: Decimal | None = None
    nearest_support: Decimal | None = None
    range_high: Decimal | None = None
    range_low: Decimal | None = None

    @property
    def is_empty(self) -> bool:
        """True when no level could be derived — the prompt/persistence omit it."""
        return all(
            value is None
            for value in (
                self.swing_high,
                self.swing_low,
                self.nearest_resistance,
                self.nearest_support,
                self.range_high,
                self.range_low,
            )
        )

    def to_dict(self) -> dict[str, str | None]:
        """JSON-safe projection (``Decimal`` → string, mirroring the wire rule)."""

        def s(value: Decimal | None) -> str | None:
            return str(value) if value is not None else None

        return {
            "swing_high": s(self.swing_high),
            "swing_low": s(self.swing_low),
            "nearest_resistance": s(self.nearest_resistance),
            "nearest_support": s(self.nearest_support),
            "range_high": s(self.range_high),
            "range_low": s(self.range_low),
        }


class StructureAnalyzer:
    """Computes a :class:`StructureSnapshot` from an ordered candle series."""

    def __init__(
        self,
        *,
        left: int = _PIVOT_LEFT,
        right: int = _PIVOT_RIGHT,
        window: int = _STRUCTURE_WINDOW,
    ) -> None:
        self._left = left
        self._right = right
        self._window = window

    def analyze(self, candles: Sequence[Candle]) -> StructureSnapshot:
        # Need at least one full pivot window; otherwise no pivot can be confirmed.
        if len(candles) < self._left + self._right + 1:
            return StructureSnapshot()

        # Defensive sort + bound to the recent window (every caller already
        # passes oldest-first, but structure must never depend on that holding).
        ordered = sorted(candles, key=lambda c: c.timestamp)[-self._window :]
        highs = [c.high for c in ordered]
        lows = [c.low for c in ordered]
        last_close = ordered[-1].close

        high_pivots = find_pivots(highs, left=self._left, right=self._right, high=True)
        low_pivots = find_pivots(lows, left=self._left, right=self._right, high=False)

        resistances = [highs[i] for i in high_pivots if highs[i] > last_close]
        supports = [lows[i] for i in low_pivots if lows[i] < last_close]

        return StructureSnapshot(
            swing_high=highs[high_pivots[-1]] if high_pivots else None,
            swing_low=lows[low_pivots[-1]] if low_pivots else None,
            nearest_resistance=min(resistances) if resistances else None,
            nearest_support=max(supports) if supports else None,
            range_high=max(highs),
            range_low=min(lows),
        )
