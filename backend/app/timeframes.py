"""Canonical timeframe metadata — the single source of truth for bar durations.

Several layers reason about how long a timeframe's bar lasts: the candle cache
(when could a new bar have closed?), the analysis controller and AI prompt
(order frames high→low, pick the lowest/highest per style), and config (order
the per-style union low→high). Keeping the mapping in one dependency-free module
stops those copies from drifting — add a timeframe here once and every layer
agrees.

Deliberately free of any ``app`` imports of its own, so it is safe to import
from anywhere (``app.config`` included) without risking an import cycle.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

#: Bar duration in minutes per supported timeframe. The keys are exactly the
#: ``Timeframe`` literal in :mod:`app.config`.
TIMEFRAME_MINUTES: Final[dict[str, int]] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


def timeframe_minutes(timeframe: str) -> int:
    """Bar duration of ``timeframe`` in minutes, or ``0`` if unrecognised.

    The ``0`` fallback is load-bearing for callers: the cache treats it as
    "never cacheable", and the ordering helpers sort an unknown frame first.
    """
    return TIMEFRAME_MINUTES.get(timeframe, 0)


def sort_timeframes(timeframes: Iterable[str], *, descending: bool = False) -> list[str]:
    """Order timeframes by bar duration (ascending by default, high→low if descending)."""
    return sorted(timeframes, key=timeframe_minutes, reverse=descending)
