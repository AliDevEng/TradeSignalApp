"""Market-data service package.

Public surface: the ``Candle`` value object, the ``MarketDataProvider``
contract, the typed error hierarchy, and a single factory that maps the
configured ``market_data_provider`` to a concrete implementation. Consumers
depend on the abstraction and the factory — never on a vendor module
directly — so adding a provider is an additive change.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.market_data.base import (
    Candle,
    MarketDataError,
    MarketDataParseError,
    MarketDataProvider,
    MarketDataUnavailableError,
    RateLimitError,
    SymbolNotFoundError,
)
from app.services.market_data.cache import CachingMarketDataProvider
from app.services.market_data.twelve_data import TwelveDataProvider

if TYPE_CHECKING:
    from app.config import Settings

__all__ = [
    "CachingMarketDataProvider",
    "Candle",
    "MarketDataError",
    "MarketDataParseError",
    "MarketDataProvider",
    "MarketDataUnavailableError",
    "RateLimitError",
    "SymbolNotFoundError",
    "TwelveDataProvider",
    "build_market_data_provider",
]


def build_market_data_provider(settings: Settings) -> MarketDataProvider:
    """Construct the provider selected by ``settings.market_data_provider``.

    The match is exhaustive over the ``MarketDataProvider`` config Literal;
    adding a new vendor to that Literal without wiring it here is a type
    error, which is exactly the fail-fast behaviour we want.
    """
    match settings.market_data_provider:
        case "twelve_data":
            return TwelveDataProvider(
                settings.twelve_data_api_key,
                base_url=settings.twelve_data_base_url,
                timeout_seconds=settings.market_data_timeout_seconds,
                max_retries=settings.market_data_max_retries,
            )
