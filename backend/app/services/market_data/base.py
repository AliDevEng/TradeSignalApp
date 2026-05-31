"""Market-data domain contract: the ``Candle`` value object + provider ABC.

This module is deliberately provider-agnostic. ``Candle`` is the single shape
the rest of the pipeline (indicators, AI prompt, persistence) speaks in, so
swapping Twelve Data for another vendor is a matter of adding one
``MarketDataProvider`` implementation — nothing downstream changes.

OHLC values are stored as ``Decimal`` rather than ``float`` to stay faithful
to the project's "never float for prices" rule (see the signals model). The
indicator calculator converts to ``float`` only at the boundary where pandas
requires it, so precision is preserved everywhere it can be.
"""

from __future__ import annotations

import abc
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.services import ServiceError


class MarketDataError(ServiceError):
    """Base for every market-data failure."""


class MarketDataUnavailableError(MarketDataError):
    """The provider could not be reached or returned a transient error.

    Raised after retries are exhausted. The pipeline treats this as a
    per-pair failure (the run continues for other pairs) rather than a hard
    crash.
    """


class SymbolNotFoundError(MarketDataError):
    """The provider does not recognise the requested instrument symbol."""


class RateLimitError(MarketDataUnavailableError):
    """The provider rejected the request for exceeding its rate limit.

    Subclasses ``MarketDataUnavailableError`` because, from the pipeline's
    perspective, a rate-limited request is just another transient outage.
    """


class MarketDataParseError(MarketDataError):
    """The provider responded, but the payload could not be parsed into candles."""


class Candle(BaseModel):
    """A single OHLCV bar, normalised across providers.

    Immutable (``frozen``) because a candle is a historical fact — once
    fetched it must not be mutated in place by a downstream transform.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    # Spot FX/metals feeds frequently omit real volume; keep it optional
    # rather than inventing a zero that an indicator might trust.
    volume: Decimal | None = None

    @field_validator("open", "high", "low", "close")
    @classmethod
    def _prices_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("OHLC prices must be positive")
        return value

    @model_validator(mode="after")
    def _ohlc_bounds_consistent(self) -> Candle:
        """High must be the max and low the min of the bar; otherwise the
        bar is corrupt and would silently poison every indicator."""
        if self.high < self.low:
            raise ValueError("high must be >= low")
        if self.high < self.open or self.high < self.close:
            raise ValueError("high must be >= open and close")
        if self.low > self.open or self.low > self.close:
            raise ValueError("low must be <= open and close")
        return self


class MarketDataProvider(abc.ABC):
    """Async fetcher for OHLCV candle series.

    Implementations own whatever client/connection they need and release it
    via :meth:`aclose`, which the application lifespan calls on shutdown.
    """

    #: Stable identifier persisted alongside signals for provenance.
    provider_name: str

    @abc.abstractmethod
    async def fetch_candles(
        self,
        symbol: str,
        *,
        timeframe: str,
        count: int,
    ) -> list[Candle]:
        """Return ``count`` candles for ``symbol`` ending at the latest close.

        Candles are ordered oldest-first so indicator windows read naturally.
        Raises a :class:`MarketDataError` subclass on failure — never a raw
        provider/transport exception.
        """

    @abc.abstractmethod
    async def aclose(self) -> None:
        """Release any held network resources. Must be idempotent."""
