"""Twelve Data implementation of :class:`MarketDataProvider`.

Twelve Data quirks this adapter hides from the rest of the codebase:

- **Symbol format.** Their API expects ``EUR/USD`` / ``XAU/USD``; our config
  stores compact ``EURUSD`` / ``XAUUSD``. We insert the slash on the way out.
- **Interval names.** Their intervals are ``1min`` / ``1day`` etc.; we map
  from our canonical timeframe vocabulary.
- **Errors-in-200s.** A bad request can come back HTTP 200 with
  ``{"status": "error", "code": ..., "message": ...}`` in the body, so the
  HTTP status alone is not enough to decide success.
- **Newest-first ordering.** We request ``order=ASC`` so callers always get
  oldest-first series without re-sorting.

Transient failures (timeouts, connection resets, 5xx, 429) are retried with
exponential backoff; deterministic failures (unknown symbol, malformed
payload) are not — retrying them only wastes the rate-limit budget.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Final

import httpx
from pydantic import ValidationError

from app.services.market_data.base import (
    Candle,
    MarketDataParseError,
    MarketDataProvider,
    MarketDataUnavailableError,
    RateLimitError,
    SymbolNotFoundError,
)

logger = logging.getLogger(__name__)

# Canonical timeframe (app.config.Timeframe) → Twelve Data interval string.
_INTERVAL_MAP: Final[dict[str, str]] = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1day",
}

# Twelve Data error codes that mean "unknown instrument" rather than "retry".
_SYMBOL_ERROR_CODES: Final[frozenset[int]] = frozenset({400, 404})


def _to_provider_symbol(symbol: str) -> str:
    """Map ``EURUSD`` → ``EUR/USD``. Pass through anything already slashed
    or not a plain 6-character pair (so e.g. index/equity symbols survive)."""
    if "/" in symbol:
        return symbol
    if len(symbol) == 6 and symbol.isalpha():
        return f"{symbol[:3]}/{symbol[3:]}"
    return symbol


class TwelveDataProvider(MarketDataProvider):
    provider_name = "twelve_data"

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.twelvedata.com",
        timeout_seconds: float = 15.0,
        max_retries: int = 3,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._max_retries = max_retries
        # Accept an injected client (tests use httpx.MockTransport); otherwise
        # own one for the app's lifetime. ``_owns_client`` ensures we never
        # close a client we were handed.
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
        )

    def _interval(self, timeframe: str) -> str:
        try:
            return _INTERVAL_MAP[timeframe]
        except KeyError as exc:  # pragma: no cover - guarded by config Literal
            raise MarketDataParseError(f"Unsupported timeframe: {timeframe!r}") from exc

    async def fetch_candles(
        self,
        symbol: str,
        *,
        timeframe: str,
        count: int,
    ) -> list[Candle]:
        if count <= 0:
            raise ValueError("count must be a positive integer")

        params = {
            "symbol": _to_provider_symbol(symbol),
            "interval": self._interval(timeframe),
            "outputsize": str(count),
            "order": "ASC",
            "timezone": "UTC",
            "apikey": self._api_key,
        }
        payload = await self._get_with_retries("/time_series", params, symbol=symbol)
        return self._parse_candles(payload, symbol=symbol)

    async def _get_with_retries(
        self,
        path: str,
        params: dict[str, str],
        *,
        symbol: str,
    ) -> dict[str, Any]:
        """GET with exponential backoff on transient failures.

        Returns the decoded JSON body on success. Raises a typed
        :class:`MarketDataError` on failure; the secret ``apikey`` is never
        included in any raised message or log line.
        """
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(path, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                logger.warning(
                    "Twelve Data transport error for %s (attempt %d/%d): %s",
                    symbol,
                    attempt + 1,
                    self._max_retries + 1,
                    exc.__class__.__name__,
                )
            else:
                # 429 / 5xx are transient — fall through to backoff. Other
                # 4xx are deterministic and handled in the body parser below.
                if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
                    last_exc = RateLimitError(f"Rate limited fetching {symbol}")
                    logger.warning("Twelve Data rate limit hit for %s", symbol)
                elif response.status_code >= httpx.codes.INTERNAL_SERVER_ERROR:
                    last_exc = MarketDataUnavailableError(
                        f"Twelve Data returned {response.status_code} for {symbol}"
                    )
                    logger.warning(
                        "Twelve Data %d for %s (attempt %d/%d)",
                        response.status_code,
                        symbol,
                        attempt + 1,
                        self._max_retries + 1,
                    )
                else:
                    return self._decode_body(response, symbol=symbol)

            if attempt < self._max_retries:
                await asyncio.sleep(self._backoff_seconds(attempt))

        # Retries exhausted.
        if isinstance(last_exc, MarketDataUnavailableError):
            raise last_exc
        raise MarketDataUnavailableError(
            f"Twelve Data unreachable for {symbol} after {self._max_retries + 1} attempts"
        ) from last_exc

    @staticmethod
    def _backoff_seconds(attempt: int) -> float:
        """Exponential backoff: 0.5s, 1s, 2s, … capped at 8s."""
        return min(0.5 * (2**attempt), 8.0)

    def _decode_body(self, response: httpx.Response, *, symbol: str) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError as exc:
            raise MarketDataParseError(f"Non-JSON response for {symbol}") from exc
        if not isinstance(body, dict):
            raise MarketDataParseError(f"Unexpected response shape for {symbol}")

        # Twelve Data signals failure via an in-body status even on HTTP 200.
        if body.get("status") == "error":
            code = body.get("code")
            message = body.get("message", "unknown error")
            if isinstance(code, int) and code in _SYMBOL_ERROR_CODES:
                raise SymbolNotFoundError(f"Unknown symbol {symbol}: {message}")
            if code == httpx.codes.TOO_MANY_REQUESTS:
                raise RateLimitError(f"Rate limited fetching {symbol}: {message}")
            raise MarketDataUnavailableError(f"Twelve Data error for {symbol}: {message}")
        return body

    def _parse_candles(self, body: dict[str, Any], *, symbol: str) -> list[Candle]:
        values = body.get("values")
        if not isinstance(values, list) or not values:
            raise MarketDataParseError(f"No candle data returned for {symbol}")

        candles: list[Candle] = []
        for raw in values:
            try:
                candles.append(
                    Candle(
                        timestamp=raw["datetime"],
                        open=raw["open"],
                        high=raw["high"],
                        low=raw["low"],
                        close=raw["close"],
                        # Volume is absent for most spot FX/metals series.
                        volume=raw.get("volume") or None,
                    )
                )
            except (KeyError, ValidationError, TypeError) as exc:
                raise MarketDataParseError(f"Malformed candle for {symbol}: {exc}") from exc

        # ``order=ASC`` should already yield oldest-first, but sort defensively
        # so a provider-side change can never silently reverse indicator input.
        candles.sort(key=lambda c: c.timestamp)
        return candles

    async def aclose(self) -> None:
        if self._owns_client and not self._client.is_closed:
            await self._client.aclose()
