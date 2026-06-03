"""A caching decorator over a :class:`MarketDataProvider`.

Slow timeframes only produce a new bar every few hours (4h) or once a day (1d),
but the analysis cycle runs far more often than that (every few minutes). Re-
fetching those candles every run spends the data provider's per-minute budget
on bars that *cannot* have changed since the last fetch — the dominant cost
against the Twelve Data free tier (see the rate-limit note in project memory).

This wrapper memoises the most recent fetch per ``(symbol, timeframe)`` and
reuses it until a new bar closes, so a cycle only spends a network call when a
fresh bar could plausibly exist. It *is* a :class:`MarketDataProvider` (same
ABC), so the controller is unchanged — it still calls :meth:`fetch_candles` and
neither knows nor cares that a cache sits in front of the real provider.

Freshness is aligned to bar-close boundaries, not a wall-clock TTL from the
fetch: a cached series is reused only while ``now`` falls in the same bar window
as the fetch, so it is dropped the moment a new bar closes (a 1h entry fetched
at 10:50 expires at 11:00, not 11:50). All supported timeframes divide evenly
into a day, so the windows align to UTC midnight — exactly where the provider's
bars close. Fast timeframes (≤ the run interval) effectively never hit the
cache, which is correct: they close a new bar every run.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from app.services.market_data.base import Candle, MarketDataProvider

logger = logging.getLogger(__name__)

# Bar duration (minutes) per timeframe, used to bucket a moment into the bar
# window it falls in. An unknown timeframe maps to 0 so it is never served from
# cache (always delegated to the wrapped provider).
_TIMEFRAME_MINUTES: Final[dict[str, int]] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}

# Bar windows are counted from this instant. Since every supported timeframe
# divides a day, epoch-aligned windows coincide with UTC-midnight-aligned ones —
# where the provider closes its bars.
_EPOCH: Final[datetime] = datetime(1970, 1, 1, tzinfo=UTC)


def _utcnow() -> datetime:
    """Timezone-aware UTC now. Injected via the constructor so tests can pin it."""
    return datetime.now(UTC)


@dataclass(slots=True)
class _Entry:
    """One cached fetch: the candles, the count requested when fetched, and when."""

    candles: list[Candle]
    count: int
    fetched_at: datetime


class CachingMarketDataProvider(MarketDataProvider):
    """Wraps a concrete provider with a per-``(symbol, timeframe)`` TTL cache."""

    def __init__(
        self,
        inner: MarketDataProvider,
        *,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._inner = inner
        self._clock = clock
        # Mirror the wrapped provider's identity so provenance stamped on signals
        # is the real vendor, not the cache.
        self.provider_name = inner.provider_name
        self._entries: dict[tuple[str, str], _Entry] = {}
        # One lock per key so a manual run overlapping the scheduled one can't
        # both miss and stampede the upstream provider for the same series.
        self._locks: dict[tuple[str, str], asyncio.Lock] = {}

    @staticmethod
    def _bar_index(ts: datetime, timeframe: str) -> int | None:
        """Which bar window ``ts`` falls in, or ``None`` for an uncacheable tf.

        Windows are aligned to :data:`_EPOCH`; since every supported timeframe
        divides a day, that is the same as aligning to UTC midnight — where the
        provider closes its bars. Two moments share an index iff no bar boundary
        lies between them.
        """
        minutes = _TIMEFRAME_MINUTES.get(timeframe, 0)
        if minutes <= 0:
            return None
        elapsed_minutes = int((ts - _EPOCH).total_seconds() // 60)
        return elapsed_minutes // minutes

    def _is_fresh(self, entry: _Entry, *, timeframe: str, count: int, now: datetime) -> bool:
        # A request for more history than we cached is a miss — we can't synthesise
        # bars we never fetched.
        if entry.count < count:
            return False
        # Fresh only while no new bar has closed since the fetch. An unknown
        # timeframe (index None) is never served from cache.
        current = self._bar_index(now, timeframe)
        return current is not None and current == self._bar_index(entry.fetched_at, timeframe)

    async def fetch_candles(
        self,
        symbol: str,
        *,
        timeframe: str,
        count: int,
    ) -> list[Candle]:
        key = (symbol, timeframe)

        entry = self._entries.get(key)
        if entry is not None and self._is_fresh(
            entry, timeframe=timeframe, count=count, now=self._clock()
        ):
            return entry.candles[-count:]

        # Miss: serialise concurrent fetchers for this key so only one hits the
        # network; the rest re-check and reuse the freshly-filled entry.
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            entry = self._entries.get(key)
            if entry is not None and self._is_fresh(
                entry, timeframe=timeframe, count=count, now=self._clock()
            ):
                return entry.candles[-count:]

            candles = await self._inner.fetch_candles(symbol, timeframe=timeframe, count=count)
            self._entries[key] = _Entry(candles=candles, count=count, fetched_at=self._clock())
            logger.debug("Cache fill %s %s (count=%d)", symbol, timeframe, count)
            return candles

    async def aclose(self) -> None:
        """Release the wrapped provider's resources. Idempotent (delegates)."""
        await self._inner.aclose()
