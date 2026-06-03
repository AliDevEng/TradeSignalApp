"""Unit tests for :class:`CachingMarketDataProvider`.

The cache is a decorator over a provider, so the tests use a counting fake as
the inner provider and a pinned clock to drive TTL expiry deterministically —
no network, no real time.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services.market_data import CachingMarketDataProvider
from app.services.market_data.base import Candle, MarketDataProvider

_T0 = datetime(2026, 6, 3, 12, 0, tzinfo=UTC)


def _candles(n: int) -> list[Candle]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Candle(
            timestamp=base + timedelta(minutes=i),
            open=Decimal("1.10"),
            high=Decimal("1.12"),
            low=Decimal("1.09"),
            close=Decimal("1.11"),
        )
        for i in range(n)
    ]


class _CountingProvider(MarketDataProvider):
    """Records every fetch and yields once, so concurrent callers can interleave."""

    provider_name = "counting"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []
        self.closed = False

    async def fetch_candles(self, symbol, *, timeframe, count):
        await asyncio.sleep(0)  # force a yield so the lock test can race
        self.calls.append((symbol, timeframe, count))
        return _candles(count)

    async def aclose(self):
        self.closed = True


class _Clock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += timedelta(**kwargs)


async def test_hit_within_same_bar_serves_from_cache():
    inner = _CountingProvider()
    clock = _Clock(_T0)  # 12:00 — start of a 4h bar window [12:00, 16:00)
    cache = CachingMarketDataProvider(inner, clock=clock)

    await cache.fetch_candles("XAUUSD", timeframe="4h", count=200)
    clock.advance(minutes=30)  # still inside the same 4h bar
    await cache.fetch_candles("XAUUSD", timeframe="4h", count=200)

    assert len(inner.calls) == 1  # second request served from cache


async def test_refetches_after_a_bar_closes():
    inner = _CountingProvider()
    clock = _Clock(_T0)  # 12:00
    cache = CachingMarketDataProvider(inner, clock=clock)

    await cache.fetch_candles("XAUUSD", timeframe="1h", count=200)
    clock.advance(minutes=61)  # crossed the 13:00 boundary
    await cache.fetch_candles("XAUUSD", timeframe="1h", count=200)

    assert len(inner.calls) == 2


async def test_crossing_bar_boundary_refetches_even_minutes_later():
    # The boundary-aligned fix: only 2 minutes elapse, but they straddle the
    # 13:00 bar close, so the cache must refresh (a wall-clock TTL would not).
    inner = _CountingProvider()
    clock = _Clock(datetime(2026, 6, 3, 12, 59, tzinfo=UTC))
    cache = CachingMarketDataProvider(inner, clock=clock)

    await cache.fetch_candles("XAUUSD", timeframe="1h", count=200)
    clock.advance(minutes=2)  # 13:01 — a new 1h bar has closed
    await cache.fetch_candles("XAUUSD", timeframe="1h", count=200)

    assert len(inner.calls) == 2


async def test_insufficient_cached_count_refetches():
    inner = _CountingProvider()
    cache = CachingMarketDataProvider(inner, clock=_Clock(_T0))

    await cache.fetch_candles("XAUUSD", timeframe="1d", count=100)
    # Same bar, but more history is requested than was cached → miss.
    await cache.fetch_candles("XAUUSD", timeframe="1d", count=200)

    assert len(inner.calls) == 2


async def test_serves_requested_count_from_larger_cache():
    inner = _CountingProvider()
    cache = CachingMarketDataProvider(inner, clock=_Clock(_T0))

    await cache.fetch_candles("XAUUSD", timeframe="1d", count=200)
    candles = await cache.fetch_candles("XAUUSD", timeframe="1d", count=50)

    assert len(inner.calls) == 1
    assert len(candles) == 50  # sliced from the cached series


async def test_distinct_keys_cached_independently():
    inner = _CountingProvider()
    cache = CachingMarketDataProvider(inner, clock=_Clock(_T0))

    await cache.fetch_candles("XAUUSD", timeframe="4h", count=10)
    await cache.fetch_candles("EURUSD", timeframe="4h", count=10)
    await cache.fetch_candles("XAUUSD", timeframe="1d", count=10)

    assert len(inner.calls) == 3  # both symbol and timeframe key the cache


async def test_unknown_timeframe_never_cached():
    inner = _CountingProvider()
    cache = CachingMarketDataProvider(inner, clock=_Clock(_T0))

    await cache.fetch_candles("XAUUSD", timeframe="3h", count=10)
    await cache.fetch_candles("XAUUSD", timeframe="3h", count=10)

    assert len(inner.calls) == 2  # TTL 0 → always delegated


async def test_concurrent_miss_fetches_once():
    inner = _CountingProvider()
    cache = CachingMarketDataProvider(inner, clock=_Clock(_T0))

    await asyncio.gather(
        *[cache.fetch_candles("XAUUSD", timeframe="4h", count=10) for _ in range(5)]
    )

    assert len(inner.calls) == 1  # the per-key lock collapses the stampede


async def test_provider_name_mirrors_inner():
    inner = _CountingProvider()
    cache = CachingMarketDataProvider(inner, clock=_Clock(_T0))
    assert cache.provider_name == "counting"


async def test_aclose_delegates_to_inner():
    inner = _CountingProvider()
    cache = CachingMarketDataProvider(inner, clock=_Clock(_T0))
    await cache.aclose()
    assert inner.closed is True
