"""Unit tests for the Twelve Data market-data provider.

A live HTTP call is replaced with ``httpx.MockTransport`` so we exercise the
real request-building, retry, and parsing code paths without a network. The
backoff sleep is patched to a no-op so retry tests stay fast.
"""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
from app.services.market_data import (
    Candle,
    MarketDataParseError,
    MarketDataUnavailableError,
    RateLimitError,
    SymbolNotFoundError,
    TwelveDataProvider,
)
from app.services.market_data.twelve_data import _to_provider_symbol


def _ok_payload(n: int = 3) -> dict:
    """A well-formed ``time_series`` body with ``n`` ascending candles."""
    values = [
        {
            "datetime": f"2024-01-0{i + 1} 00:00:00",
            "open": f"{1.10 + i * 0.01:.5f}",
            "high": f"{1.12 + i * 0.01:.5f}",
            "low": f"{1.09 + i * 0.01:.5f}",
            "close": f"{1.11 + i * 0.01:.5f}",
        }
        for i in range(n)
    ]
    return {"status": "ok", "values": values}


def _provider_with_handler(handler, *, max_retries: int = 0) -> TwelveDataProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://td.test")
    return TwelveDataProvider("secret-key", max_retries=max_retries, client=client)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    """Make backoff instant so retry tests don't actually wait."""

    async def _instant(_seconds: float) -> None:
        return None

    monkeypatch.setattr("app.services.market_data.twelve_data.asyncio.sleep", _instant)


# ── Symbol mapping ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("EURUSD", "EUR/USD"),
        ("XAUUSD", "XAU/USD"),
        ("GBPUSD", "GBP/USD"),
        ("EUR/USD", "EUR/USD"),  # already slashed → unchanged
        ("AAPL", "AAPL"),  # not a 6-letter pair → unchanged
    ],
)
def test_to_provider_symbol(raw, expected):
    assert _to_provider_symbol(raw) == expected


# ── Happy path ───────────────────────────────────────────────────────────────


async def test_fetch_candles_parses_and_orders_ascending():
    captured: dict[str, httpx.QueryParams] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["params"] = request.url.params
        return httpx.Response(200, json=_ok_payload(3))

    provider = _provider_with_handler(handler)
    candles = await provider.fetch_candles("EURUSD", timeframe="1h", count=3)

    assert len(candles) == 3
    assert all(isinstance(c, Candle) for c in candles)
    # Oldest first.
    assert candles[0].timestamp < candles[-1].timestamp
    assert candles[0].open == Decimal("1.10000")
    # Request carried the mapped symbol + interval and never leaked nothing odd.
    assert captured["params"]["symbol"] == "EUR/USD"
    assert captured["params"]["interval"] == "1h"
    assert captured["params"]["outputsize"] == "3"
    await provider.aclose()


async def test_parsed_candle_timestamps_are_utc_aware():
    """Twelve Data returns naive ``"YYYY-MM-DD HH:MM:SS"`` strings (queried with
    ``timezone=UTC``); the ``Candle`` must normalise them to tz-aware UTC.

    Regression guard: left naive, a candle timestamp can't be compared against the
    timezone-aware ``generated_at`` the database stores, which broke the outcome
    evaluator with ``can't compare offset-naive and offset-aware datetimes``.
    """
    from datetime import UTC

    provider = _provider_with_handler(lambda r: httpx.Response(200, json=_ok_payload(2)))
    candles = await provider.fetch_candles("EURUSD", timeframe="1h", count=2)

    assert candles, "expected at least one candle"
    for candle in candles:
        assert candle.timestamp.tzinfo is not None, "timestamp must be timezone-aware"
        assert candle.timestamp.utcoffset() == UTC.utcoffset(None)
    await provider.aclose()


async def test_fetch_candles_maps_daily_interval():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["interval"] = request.url.params["interval"]
        return httpx.Response(200, json=_ok_payload(1))

    provider = _provider_with_handler(handler)
    await provider.fetch_candles("XAUUSD", timeframe="1d", count=1)
    assert seen["interval"] == "1day"
    await provider.aclose()


async def test_fetch_candles_rejects_non_positive_count():
    provider = _provider_with_handler(lambda r: httpx.Response(200, json=_ok_payload()))
    with pytest.raises(ValueError, match="count"):
        await provider.fetch_candles("EURUSD", timeframe="1h", count=0)
    await provider.aclose()


# ── Error mapping ────────────────────────────────────────────────────────────


async def test_in_body_symbol_error_raises_symbol_not_found():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "error", "code": 404, "message": "no symbol"})

    provider = _provider_with_handler(handler)
    with pytest.raises(SymbolNotFoundError):
        await provider.fetch_candles("ZZZZZZ", timeframe="1h", count=5)
    await provider.aclose()


async def test_in_body_rate_limit_raises_rate_limit_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "error", "code": 429, "message": "slow down"})

    provider = _provider_with_handler(handler)
    with pytest.raises(RateLimitError):
        await provider.fetch_candles("EURUSD", timeframe="1h", count=5)
    await provider.aclose()


async def test_http_429_retried_then_rate_limit_error():
    attempts = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(429, json={})

    provider = _provider_with_handler(handler, max_retries=2)
    with pytest.raises(RateLimitError):
        await provider.fetch_candles("EURUSD", timeframe="1h", count=5)
    assert attempts["n"] == 3  # initial + 2 retries
    await provider.aclose()


async def test_http_500_retried_then_unavailable():
    attempts = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(503, text="upstream down")

    provider = _provider_with_handler(handler, max_retries=1)
    with pytest.raises(MarketDataUnavailableError):
        await provider.fetch_candles("EURUSD", timeframe="1h", count=5)
    assert attempts["n"] == 2
    await provider.aclose()


async def test_transport_timeout_retried_then_unavailable():
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        raise httpx.TimeoutException("timed out", request=request)

    provider = _provider_with_handler(handler, max_retries=2)
    with pytest.raises(MarketDataUnavailableError):
        await provider.fetch_candles("EURUSD", timeframe="1h", count=5)
    assert attempts["n"] == 3
    await provider.aclose()


async def test_empty_values_raises_parse_error():
    provider = _provider_with_handler(
        lambda r: httpx.Response(200, json={"status": "ok", "values": []})
    )
    with pytest.raises(MarketDataParseError):
        await provider.fetch_candles("EURUSD", timeframe="1h", count=5)
    await provider.aclose()


async def test_malformed_candle_raises_parse_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        # high < low → Candle validation fails → surfaced as parse error.
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "values": [
                    {
                        "datetime": "2024-01-01 00:00:00",
                        "open": "1.10",
                        "high": "1.05",
                        "low": "1.20",
                        "close": "1.11",
                    }
                ],
            },
        )

    provider = _provider_with_handler(handler)
    with pytest.raises(MarketDataParseError):
        await provider.fetch_candles("EURUSD", timeframe="1h", count=1)
    await provider.aclose()


async def test_non_json_body_raises_parse_error():
    provider = _provider_with_handler(lambda r: httpx.Response(200, text="<html>nope</html>"))
    with pytest.raises(MarketDataParseError):
        await provider.fetch_candles("EURUSD", timeframe="1h", count=1)
    await provider.aclose()


# ── Client ownership ─────────────────────────────────────────────────────────


async def test_aclose_does_not_close_injected_client():
    """An injected client is owned by the caller; the provider must not close it."""
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=_ok_payload())),
        base_url="http://td.test",
    )
    provider = TwelveDataProvider("k", client=client)
    await provider.aclose()
    assert client.is_closed is False
    await client.aclose()
