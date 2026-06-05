"""The performance calculator — a pure function from "closed signals" to a
track record.

This is the aggregation counterpart to the :class:`~app.services.outcome.OutcomeEvaluator`:
where that one decides *what happened* to a single signal, this one rolls a whole
set of already-scored signals up into the numbers a trader judges a strategy by —
win-rate, profit factor, expectancy, total R — plus a confidence-calibration
table ("when the AI says 80%, is it right 80% of the time?") and an equity curve.

Like the evaluator it is **pure and IO-free**: it speaks plain value objects
(:class:`ClosedSignal`), never an ORM row, so it is fully back-testable and the
arithmetic is unit-tested directly rather than inferred from SQL shape. Fetching
the rows and mapping them onto :class:`ClosedSignal` is the controller's job; the
``Decimal`` discipline for R figures is preserved end-to-end (ratios such as
win-rate are statistics, not prices, so those stay ``float``).

A signal counts toward the track record only once it is **closed with a defined
R** — open signals have no result yet, and a stop-less signal has no risk to
denominate R in, so neither can be scored. A "win" is ``realized_r > 0`` (price
closed the trade in profit); everything else (a stop, or a negative
mark-to-market expiry) is a loss. Defining win by realised money rather than by
which enum was stamped keeps win-rate, profit factor and calibration all on one
honest, R-based denominator.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

SignalTypeLiteral = Literal["scalp", "swing"]

# R figures share the evaluator's 4-decimal scale (Numeric(12, 4)).
_R_QUANTUM = Decimal("0.0001")
_ZERO = Decimal("0")

# Confidence calibration is reported in five fixed 20-point buckets so the chart
# has a stable x-axis regardless of how the data happens to cluster.
_BUCKET_COUNT = 5
_BUCKET_WIDTH = 1.0 / _BUCKET_COUNT


def _q(value: Decimal) -> Decimal:
    """Round an R figure to the storage scale, so totals can't drift in display."""
    return value.quantize(_R_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class ClosedSignal:
    """One scored, closed signal — the calculator's only input shape.

    Plain values, never an ORM row. ``realized_r`` is required and signed (a stop
    is ``-1``, a winning TP positive); ``confidence`` is the stated 0-1 figure the
    AI emitted, which calibration tests against the realised hit-rate.
    """

    signal_id: uuid.UUID
    signal_type: SignalTypeLiteral
    confidence: float
    realized_r: Decimal
    closed_at: datetime


@dataclass(frozen=True, slots=True)
class PerformanceSummary:
    """Headline track-record numbers over one set of closed signals."""

    total: int
    wins: int
    losses: int
    win_rate: float
    total_r: Decimal
    avg_r: Decimal
    profit_factor: float | None
    gross_profit: Decimal
    gross_loss: Decimal


@dataclass(frozen=True, slots=True)
class CalibrationBucket:
    """Predicted vs realised hit-rate for one confidence band.

    ``avg_confidence`` is the mean *stated* confidence of the signals that fell in
    the band (the model's prediction); ``win_rate`` is what actually happened. A
    well-calibrated model has the two roughly equal across every populated bucket.
    """

    lower: float
    upper: float
    label: str
    count: int
    avg_confidence: float
    win_rate: float
    wins: int


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """One step of the cumulative-R equity curve."""

    signal_id: uuid.UUID
    closed_at: datetime
    realized_r: Decimal
    cumulative_r: Decimal


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    """The full track record: overall + per-style summaries, calibration, equity."""

    overall: PerformanceSummary
    by_type: dict[SignalTypeLiteral, PerformanceSummary]
    calibration: list[CalibrationBucket]
    equity_curve: list[EquityPoint]


class PerformanceCalculator:
    """Pure aggregator: a sequence of :class:`ClosedSignal` → a :class:`PerformanceReport`."""

    def compute(
        self,
        signals: Sequence[ClosedSignal],
        *,
        max_equity_points: int | None = None,
    ) -> PerformanceReport:
        """Roll the closed signals up into the full report.

        Input order is preserved for the equity curve, so the caller is expected
        to pass them oldest-close first (the repository orders by ``closed_at``).
        ``max_equity_points`` caps the returned curve length (the cumulative R is
        still computed over every signal first, then the curve is downsampled);
        ``None`` returns every point.
        """
        return PerformanceReport(
            overall=self._summarise(signals),
            by_type=self._summarise_by_type(signals),
            calibration=self._calibrate(signals),
            equity_curve=self._equity_curve(signals, max_points=max_equity_points),
        )

    # ── Summaries ──────────────────────────────────────────────────────────

    def _summarise(self, signals: Sequence[ClosedSignal]) -> PerformanceSummary:
        total = len(signals)
        if total == 0:
            return PerformanceSummary(
                total=0,
                wins=0,
                losses=0,
                win_rate=0.0,
                total_r=_ZERO,
                avg_r=_ZERO,
                profit_factor=None,
                gross_profit=_ZERO,
                gross_loss=_ZERO,
            )

        wins = sum(1 for s in signals if s.realized_r > 0)
        gross_profit = sum((s.realized_r for s in signals if s.realized_r > 0), _ZERO)
        gross_loss = -sum((s.realized_r for s in signals if s.realized_r < 0), _ZERO)
        total_r = sum((s.realized_r for s in signals), _ZERO)

        # Profit factor is undefined with no losing R (an infinite ratio); report
        # ``None`` rather than a misleading sentinel so the frontend can label it.
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else None

        return PerformanceSummary(
            total=total,
            wins=wins,
            losses=total - wins,
            win_rate=wins / total,
            total_r=_q(total_r),
            avg_r=_q(total_r / total),
            profit_factor=profit_factor,
            gross_profit=_q(gross_profit),
            gross_loss=_q(gross_loss),
        )

    def _summarise_by_type(
        self, signals: Sequence[ClosedSignal]
    ) -> dict[SignalTypeLiteral, PerformanceSummary]:
        # Always emit both styles (even when empty) so the KPI split has a stable
        # shape and the frontend never has to guard a missing key.
        styles: tuple[SignalTypeLiteral, ...] = ("scalp", "swing")
        return {
            style: self._summarise([s for s in signals if s.signal_type == style])
            for style in styles
        }

    # ── Calibration ────────────────────────────────────────────────────────

    def _calibrate(self, signals: Sequence[ClosedSignal]) -> list[CalibrationBucket]:
        buckets: list[list[ClosedSignal]] = [[] for _ in range(_BUCKET_COUNT)]
        for s in signals:
            buckets[self._bucket_index(s.confidence)].append(s)

        result: list[CalibrationBucket] = []
        for i, members in enumerate(buckets):
            lower = i * _BUCKET_WIDTH
            upper = (i + 1) * _BUCKET_WIDTH
            count = len(members)
            wins = sum(1 for s in members if s.realized_r > 0)
            avg_conf = sum(s.confidence for s in members) / count if count else 0.0
            win_rate = wins / count if count else 0.0
            result.append(
                CalibrationBucket(
                    lower=lower,
                    upper=upper,
                    label=f"{int(lower * 100)}-{int(upper * 100)}%",
                    count=count,
                    avg_confidence=avg_conf,
                    win_rate=win_rate,
                    wins=wins,
                )
            )
        return result

    @staticmethod
    def _bucket_index(confidence: float) -> int:
        """Map a 0-1 confidence onto a bucket index, clamping the closed top edge.

        ``confidence == 1.0`` would land in a sixth bucket without the clamp; it
        belongs in the top (80-100%) band.
        """
        idx = int(confidence * _BUCKET_COUNT)
        return min(max(idx, 0), _BUCKET_COUNT - 1)

    # ── Equity curve ───────────────────────────────────────────────────────

    def _equity_curve(
        self, signals: Sequence[ClosedSignal], *, max_points: int | None = None
    ) -> list[EquityPoint]:
        curve: list[EquityPoint] = []
        running = _ZERO
        for s in signals:
            running += s.realized_r
            curve.append(
                EquityPoint(
                    signal_id=s.signal_id,
                    closed_at=s.closed_at,
                    realized_r=_q(s.realized_r),
                    cumulative_r=_q(running),
                )
            )
        return self._downsample(curve, max_points)

    @staticmethod
    def _downsample(curve: list[EquityPoint], max_points: int | None) -> list[EquityPoint]:
        """Thin an equity curve to at most ``max_points`` evenly-spaced points.

        The running total is already baked into each point, so dropping
        intermediate points only reduces resolution — it never distorts the
        levels. Even striding keeps the curve's shape, and the final point is
        always retained so the chart still ends on the true cumulative R.
        """
        if max_points is None or len(curve) <= max_points:
            return curve
        stride = math.ceil(len(curve) / max_points)
        sampled = curve[::stride]
        if sampled[-1] is not curve[-1]:
            sampled.append(curve[-1])
        return sampled
