"""Technical-indicator service package.

Exposes the pure :class:`IndicatorCalculator`, its :class:`IndicatorSnapshot`
output, and the error hierarchy. No factory is needed — the calculator is
stateless and configuration-free, so callers construct it directly.
"""

from app.services.indicators.calculator import (
    MIN_CANDLES,
    IndicatorCalculator,
    IndicatorError,
    IndicatorSnapshot,
    InsufficientDataError,
)

__all__ = [
    "MIN_CANDLES",
    "IndicatorCalculator",
    "IndicatorError",
    "IndicatorSnapshot",
    "InsufficientDataError",
]
