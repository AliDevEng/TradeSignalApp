"""Performance aggregation service.

Public surface: the pure :class:`PerformanceCalculator` and its value objects.
Given a set of closed, R-scored signals it produces the track record the
performance API surfaces — overall and per-style summaries, a confidence
calibration table, and an equity curve. Like the outcome evaluator it is
deterministic and IO-free, so the arithmetic is unit-tested directly; loading the
rows and mapping them onto :class:`ClosedSignal` is the controller's job.
"""

from __future__ import annotations

from app.services.performance.calculator import (
    CalibrationBucket,
    ClosedSignal,
    EquityPoint,
    PerformanceCalculator,
    PerformanceReport,
    PerformanceSummary,
)

__all__ = [
    "CalibrationBucket",
    "ClosedSignal",
    "EquityPoint",
    "PerformanceCalculator",
    "PerformanceReport",
    "PerformanceSummary",
]
