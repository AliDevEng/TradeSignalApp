"""Wire-format models for the performance / track-record API.

Transport-agnostic (pydantic + stdlib only), like every other schema module: the
ORM→wire mapping and the aggregation live in the controller and the pure
performance service, never here. R figures are ``Decimal`` and serialise to JSON
**strings**, the same "never float for money" discipline the signal schema keeps;
ratios (win-rate, profit factor, average confidence) are genuine statistics, not
prices, so they cross the wire as plain numbers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

SignalType = Literal["scalp", "swing"]


class PerformanceSummary(BaseModel):
    """Headline track-record numbers over a set of closed, R-scored signals."""

    total: int = Field(ge=0, description="Closed signals with a defined R in this set.")
    wins: int = Field(ge=0)
    losses: int = Field(ge=0)
    win_rate: float = Field(ge=0.0, le=1.0)
    total_r: Decimal = Field(description="Sum of realised R across the set.")
    avg_r: Decimal = Field(description="Expectancy — average realised R per signal.")
    # None when the set has no losing R (an infinite ratio); the frontend labels
    # it rather than rendering a misleading number.
    profit_factor: float | None = Field(
        default=None, description="Gross profit ÷ gross loss; null when there is no losing R."
    )
    gross_profit: Decimal
    gross_loss: Decimal


class CalibrationBucket(BaseModel):
    """Predicted vs realised hit-rate for one 20-point confidence band."""

    label: str = Field(description='Human band label, e.g. "60-80%".')
    lower: float = Field(ge=0.0, le=1.0)
    upper: float = Field(ge=0.0, le=1.0)
    count: int = Field(ge=0)
    avg_confidence: float = Field(
        ge=0.0, le=1.0, description="Mean stated confidence in the band (the prediction)."
    )
    win_rate: float = Field(ge=0.0, le=1.0, description="Realised hit-rate in the band.")
    wins: int = Field(ge=0)


class EquityPoint(BaseModel):
    """One step of the cumulative-R equity curve, ordered by close time."""

    signal_id: uuid.UUID
    closed_at: datetime
    realized_r: Decimal
    cumulative_r: Decimal


class PerformanceResponse(BaseModel):
    """The full track record returned by ``GET /api/v1/performance``.

    ``by_type`` always carries both ``scalp`` and ``swing`` keys (each an empty
    summary when that style has no closed signals) so the frontend KPI split has a
    stable shape. ``calibration`` always carries all five buckets for a stable
    chart x-axis; empty buckets report zero counts.
    """

    overall: PerformanceSummary
    by_type: dict[SignalType, PerformanceSummary]
    calibration: list[CalibrationBucket]
    equity_curve: list[EquityPoint]
    generated_at: datetime
