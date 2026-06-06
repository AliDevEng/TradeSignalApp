"""Technical-indicator computation over a candle series.

The calculator is **pure**: candles in, an :class:`IndicatorSnapshot` out, no
IO and no hidden state. That makes it trivially unit-testable and safe to run
inside the analysis pipeline without worrying about ordering or shared
mutation.

Interpretation lives elsewhere on purpose. This layer only reports *numbers*
(RSI is 71.3, MACD histogram is negative); deciding what they *mean* for a
trade is the AI provider's job. Keeping the two apart means we can swap the
reasoning model without touching the math, and back-test the math without an
AI key.

Indicator values are persisted verbatim into ``signals.indicators_snapshot``
(JSONB) so a signal stays explainable against the exact inputs that produced
it, long after the live market has moved on.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from datetime import datetime
from typing import Final

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel

from app.services import ServiceError
from app.services.market_data.base import Candle
from app.services.structure import find_pivots

logger = logging.getLogger(__name__)

# Longest *required* lookback: MACD needs slow(26) + signal(9) ≈ 35 bars before
# its histogram is meaningful. Indicators with longer windows (EMA-200) are
# reported as ``None`` when there isn't enough history rather than blocking the
# whole snapshot.
MIN_CANDLES: Final[int] = 35

# Rounding keeps the JSONB payload compact and stable across float noise
# without throwing away precision that matters at FX/metals scales.
_ROUND_DP: Final[int] = 8

# How many bars back the "previous" trajectory values look. The point of these
# is *direction of change* (is RSI turning up? is the MACD histogram shrinking?),
# which a single-bar delta is too noisy to show — three bars is a clean read.
_TRAJECTORY_LOOKBACK: Final[int] = 3

# ADX needs ~2x its length to settle. Below ~28 bars its value is unreliable, so
# the regime label is left ``None`` rather than asserting a trend from noise.
_ADX_MIN_ROWS: Final[int] = 28
# ADX regime thresholds — the conventional reads: a strong directional move
# above 25, a directionless/ranging market below 20, transitional in between.
_ADX_TRENDING: Final[float] = 25.0
_ADX_RANGING: Final[float] = 20.0


def classify_regime(adx: float | None) -> str | None:
    """Map an ADX value onto a coarse regime label the AI and gate both read.

    ``None`` ADX (too little history) yields ``None`` — an honest "unknown"
    rather than a fabricated regime.
    """
    if adx is None:
        return None
    if adx >= _ADX_TRENDING:
        return "trending"
    if adx < _ADX_RANGING:
        return "ranging"
    return "transitional"


class IndicatorError(ServiceError):
    """Base for indicator-calculation failures."""


class InsufficientDataError(IndicatorError):
    """Fewer candles than the shortest required indicator window."""


def _clean(value: object) -> float | None:
    """Coerce a pandas/numpy scalar to a JSON-safe float, or ``None``.

    NaN and ±inf collapse to ``None`` so consumers (and the JSONB column)
    never have to reason about non-finite floats — a NaN that leaks into the
    AI prompt as the literal ``"nan"`` is a silent correctness bug.
    """
    if value is None:
        return None
    try:
        as_float = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(as_float):
        return None
    return round(as_float, _ROUND_DP)


class IndicatorSnapshot(BaseModel):
    """The latest value of each indicator, plus provenance metadata.

    Fields are ``None`` when the series was too short for that particular
    window. ``as_of`` is the timestamp of the most recent candle, not wall
    clock — two runs over the same candles produce identical snapshots.
    """

    # ``pd.Timestamp`` is a ``datetime`` subclass, so the index value assigned
    # below validates and serialises (ISO-8601) like any other datetime.
    as_of: datetime | None = None
    candles_analyzed: int = 0

    last_close: float | None = None

    sma_20: float | None = None
    sma_50: float | None = None
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None

    rsi_14: float | None = None
    # RSI ``_TRAJECTORY_LOOKBACK`` bars ago — lets a consumer see whether
    # momentum is turning (RSI 33 rising off 28 is a very different signal from
    # RSI 33 falling). ``None`` when there isn't enough history.
    rsi_14_prev: float | None = None
    # Whether price made a higher/lower extreme while RSI did the opposite over
    # the recent swings: ``"bullish"`` (price lower low, RSI higher low),
    # ``"bearish"`` (price higher high, RSI lower high), or ``None``. One of the
    # strongest reversal tells, and invisible from a single snapshot value.
    rsi_divergence: str | None = None

    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    # MACD histogram ``_TRAJECTORY_LOOKBACK`` bars ago — a shrinking histogram
    # warns of fading momentum before the MACD line itself crosses.
    macd_histogram_prev: float | None = None

    atr_14: float | None = None

    # Trend-strength + the regime label derived from it. ``regime`` is one of
    # ``"trending"``/``"ranging"``/``"transitional"`` (or ``None`` when ADX has
    # too little history) — the single most useful context for deciding whether a
    # trend-following or mean-reverting plan even makes sense.
    adx_14: float | None = None
    regime: str | None = None

    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_percent: float | None = None

    def to_storage_dict(self) -> dict[str, object]:
        """JSON-serialisable dict for the ``indicators_snapshot`` JSONB column."""
        return self.model_dump(mode="json")


class IndicatorCalculator:
    """Computes an :class:`IndicatorSnapshot` from an ordered candle series."""

    def compute(self, candles: list[Candle]) -> IndicatorSnapshot:
        if len(candles) < MIN_CANDLES:
            raise InsufficientDataError(f"Need at least {MIN_CANDLES} candles, got {len(candles)}")

        # Defensive sort: every downstream window assumes oldest-first.
        ordered = sorted(candles, key=lambda c: c.timestamp)
        n = len(ordered)
        frame = self._to_frame(ordered)

        close = frame["close"]
        # RSI is computed once as a full series (not just its last value) so the
        # trajectory and divergence reads can reuse it without recomputation.
        rsi_series = ta.rsi(close, length=14) if n >= 15 else None
        snapshot = IndicatorSnapshot(
            as_of=frame.index[-1],
            candles_analyzed=n,
            last_close=_clean(close.iloc[-1]),
            # Each indicator is gated on having enough history for its window.
            # Calling pandas-ta with too few rows both wastes work and makes it
            # print a "Series has N rows but indicator requires M" line to
            # stdout — guarding here keeps logs clean and the result honest.
            sma_20=self._windowed(20, n, lambda: ta.sma(close, length=20)),
            sma_50=self._windowed(50, n, lambda: ta.sma(close, length=50)),
            ema_20=self._windowed(20, n, lambda: ta.ema(close, length=20)),
            ema_50=self._windowed(50, n, lambda: ta.ema(close, length=50)),
            ema_200=self._windowed(200, n, lambda: ta.ema(close, length=200)),
            rsi_14=self._last(rsi_series),
            rsi_14_prev=self._at(rsi_series, -1 - _TRAJECTORY_LOOKBACK),
            atr_14=self._windowed(
                15, n, lambda: ta.atr(frame["high"], frame["low"], close, length=14)
            ),
        )
        self._apply_macd(snapshot, close, n)
        self._apply_bbands(snapshot, close, n)
        self._apply_regime(snapshot, frame, n)
        self._apply_divergence(snapshot, close, rsi_series)
        return snapshot

    def _windowed(
        self,
        min_rows: int,
        available: int,
        compute: Callable[[], pd.Series | None],
    ) -> float | None:
        """Run ``compute`` only when enough rows exist for the window."""
        if available < min_rows:
            return None
        return self._last(compute())

    @staticmethod
    def _to_frame(candles: list[Candle]) -> pd.DataFrame:
        """Build a float OHLC frame indexed by timestamp.

        Decimal → float conversion happens here, at the single boundary where
        pandas requires it; everything upstream keeps full ``Decimal`` price
        fidelity.
        """
        frame = pd.DataFrame(
            {
                "open": [float(c.open) for c in candles],
                "high": [float(c.high) for c in candles],
                "low": [float(c.low) for c in candles],
                "close": [float(c.close) for c in candles],
            },
            index=pd.DatetimeIndex([c.timestamp for c in candles], name="timestamp"),
        )
        return frame

    @staticmethod
    def _last(series: pd.Series | None) -> float | None:
        """Last finite value of an indicator series, or ``None``.

        pandas-ta returns ``None`` (not an empty Series) when a window can't
        be satisfied, so both cases are handled.
        """
        if series is None or len(series) == 0:
            return None
        return _clean(series.iloc[-1])

    @staticmethod
    def _at(series: pd.Series | None, index: int) -> float | None:
        """Finite value at a (typically negative) positional ``index``, or ``None``.

        Used for the "previous" trajectory reads. Out-of-range or non-finite
        values collapse to ``None`` so a short series never raises.
        """
        if series is None or len(series) < abs(index):
            return None
        return _clean(series.iloc[index])

    # MACD needs slow(26) + signal(9) bars before its histogram is meaningful.
    _MACD_MIN_ROWS = 35

    def _apply_macd(self, snapshot: IndicatorSnapshot, close: pd.Series, n: int) -> None:
        if n < self._MACD_MIN_ROWS:
            return
        macd = ta.macd(close)
        if macd is None or macd.empty:
            return
        # Reference by prefix rather than the full ``MACD_12_26_9`` name so a
        # future parameter tweak doesn't silently null these out.
        histogram = self._column(macd, "MACDh_")
        snapshot.macd = self._last(self._column(macd, "MACD_"))
        snapshot.macd_histogram = self._last(histogram)
        snapshot.macd_histogram_prev = self._at(histogram, -1 - _TRAJECTORY_LOOKBACK)
        snapshot.macd_signal = self._last(self._column(macd, "MACDs_"))

    def _apply_bbands(self, snapshot: IndicatorSnapshot, close: pd.Series, n: int) -> None:
        if n < 20:
            return
        bands = ta.bbands(close, length=20)
        if bands is None or bands.empty:
            return
        snapshot.bb_lower = self._last(self._column(bands, "BBL_"))
        snapshot.bb_middle = self._last(self._column(bands, "BBM_"))
        snapshot.bb_upper = self._last(self._column(bands, "BBU_"))
        snapshot.bb_percent = self._last(self._column(bands, "BBP_"))

    def _apply_regime(self, snapshot: IndicatorSnapshot, frame: pd.DataFrame, n: int) -> None:
        """Compute ADX and the regime label it implies (trending/ranging/…)."""
        if n < _ADX_MIN_ROWS:
            return
        adx = ta.adx(frame["high"], frame["low"], frame["close"], length=14)
        if adx is None or adx.empty:
            return
        snapshot.adx_14 = self._last(self._column(adx, "ADX_"))
        snapshot.regime = classify_regime(snapshot.adx_14)

    def _apply_divergence(
        self, snapshot: IndicatorSnapshot, close: pd.Series, rsi: pd.Series | None
    ) -> None:
        """Detect regular RSI divergence against the two most-recent price swings.

        Bullish: price prints a lower swing low while RSI prints a higher low
        (selling pressure fading). Bearish: price a higher swing high while RSI a
        lower high. Compares only confirmed fractal pivots and skips any pivot
        whose RSI is undefined, so a short or noisy series simply yields ``None``.
        """
        if rsi is None:
            return
        closes = [_clean(value) for value in close.tolist()]
        rsis = [_clean(value) for value in rsi.tolist()]

        lows = find_pivots(closes, left=2, right=2, high=False)
        if self._diverges(lows, closes, rsis, price_lower=True):
            snapshot.rsi_divergence = "bullish"
            return
        highs = find_pivots(closes, left=2, right=2, high=True)
        if self._diverges(highs, closes, rsis, price_lower=False):
            snapshot.rsi_divergence = "bearish"

    @staticmethod
    def _diverges(
        pivots: list[int],
        prices: list[float | None],
        rsis: list[float | None],
        *,
        price_lower: bool,
    ) -> bool:
        """Whether the last two ``pivots`` show price/RSI disagreement.

        ``price_lower`` picks the bullish read (price falls, RSI rises) vs the
        bearish one (price rises, RSI falls). Returns ``False`` unless both
        pivots carry finite price *and* RSI values.
        """
        if len(pivots) < 2:
            return False
        older, newer = pivots[-2], pivots[-1]
        p_old, p_new = prices[older], prices[newer]
        r_old, r_new = rsis[older], rsis[newer]
        if None in (p_old, p_new, r_old, r_new):
            return False
        if price_lower:
            return p_new < p_old and r_new > r_old  # type: ignore[operator]
        return p_new > p_old and r_new < r_old  # type: ignore[operator]

    @staticmethod
    def _column(frame: pd.DataFrame, prefix: str) -> pd.Series | None:
        for name in frame.columns:
            if str(name).startswith(prefix):
                return frame[name]
        return None
