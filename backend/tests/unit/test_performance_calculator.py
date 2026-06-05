"""Unit tests for :class:`PerformanceCalculator` — the pure track-record aggregator.

The calculator is the arithmetic heart of the performance API, and being pure it
is tested directly: feed it value objects, assert the numbers. This is where the
correctness of win-rate, profit factor, expectancy, the calibration bucketing,
and the equity curve actually lives — the repository and route tests only check
that the right rows reach it and the right envelope leaves.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.services.performance import ClosedSignal, PerformanceCalculator

_BASE = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def _closed(
    *,
    realized_r: str,
    confidence: float = 0.7,
    signal_type: str = "swing",
    offset_minutes: int = 0,
) -> ClosedSignal:
    return ClosedSignal(
        signal_id=uuid.uuid4(),
        signal_type=signal_type,  # type: ignore[arg-type]
        confidence=confidence,
        realized_r=Decimal(realized_r),
        closed_at=_BASE + timedelta(minutes=offset_minutes),
    )


def _calc() -> PerformanceCalculator:
    return PerformanceCalculator()


# ── Equity-curve downsampling ──────────────────────────────────────────────────


def test_equity_curve_downsamples_to_cap_and_keeps_final_point():
    signals = [_closed(realized_r="1.0", offset_minutes=i) for i in range(100)]
    report = _calc().compute(signals, max_equity_points=10)

    # Capped (allowing the always-kept final point), and the curve still ends on
    # the true cumulative R over *all* 100 signals.
    assert len(report.equity_curve) <= 11
    assert report.equity_curve[-1].cumulative_r == Decimal("100.0000")
    # The headline total is unaffected by downsampling — it sums every signal.
    assert report.overall.total == 100
    assert report.overall.total_r == Decimal("100.0000")


def test_equity_curve_not_downsampled_below_cap():
    signals = [_closed(realized_r="1.0", offset_minutes=i) for i in range(5)]
    report = _calc().compute(signals, max_equity_points=500)
    assert len(report.equity_curve) == 5


# ── Empty input ──────────────────────────────────────────────────────────────


def test_empty_input_yields_zeroed_report():
    report = _calc().compute([])

    assert report.overall.total == 0
    assert report.overall.wins == 0
    assert report.overall.losses == 0
    assert report.overall.win_rate == 0.0
    assert report.overall.total_r == Decimal("0")
    assert report.overall.avg_r == Decimal("0")
    assert report.overall.profit_factor is None
    assert report.equity_curve == []
    # Both styles are always present, even when empty.
    assert set(report.by_type) == {"scalp", "swing"}
    assert report.by_type["scalp"].total == 0
    # All five calibration buckets are always present.
    assert len(report.calibration) == 5
    assert all(b.count == 0 for b in report.calibration)


# ── Summary maths ─────────────────────────────────────────────────────────────


def test_summary_counts_wins_losses_and_totals():
    signals = [
        _closed(realized_r="2.0"),
        _closed(realized_r="3.0"),
        _closed(realized_r="-1.0"),
        _closed(realized_r="-1.0"),
    ]
    summary = _calc().compute(signals).overall

    assert summary.total == 4
    assert summary.wins == 2
    assert summary.losses == 2
    assert summary.win_rate == 0.5
    assert summary.total_r == Decimal("3.0000")
    assert summary.avg_r == Decimal("0.7500")
    assert summary.gross_profit == Decimal("5.0000")
    assert summary.gross_loss == Decimal("2.0000")
    assert summary.profit_factor == 2.5


def test_profit_factor_is_none_with_no_losses():
    summary = _calc().compute([_closed(realized_r="2.0"), _closed(realized_r="1.0")]).overall

    assert summary.wins == 2
    assert summary.losses == 0
    assert summary.win_rate == 1.0
    assert summary.profit_factor is None
    assert summary.gross_loss == Decimal("0.0000")


def test_breakeven_counts_as_loss_not_win():
    """A zero-R close did not make money, so it must not inflate win-rate."""
    summary = _calc().compute([_closed(realized_r="0.0"), _closed(realized_r="2.0")]).overall

    assert summary.wins == 1
    assert summary.losses == 1
    assert summary.win_rate == 0.5
    # Breakeven contributes to neither gross profit nor gross loss.
    assert summary.gross_profit == Decimal("2.0000")
    assert summary.gross_loss == Decimal("0.0000")
    assert summary.profit_factor is None


def test_expectancy_can_be_negative():
    summary = (
        _calc()
        .compute(
            [_closed(realized_r="1.0"), _closed(realized_r="-1.0"), _closed(realized_r="-1.0")]
        )
        .overall
    )

    assert summary.total_r == Decimal("-1.0000")
    assert summary.avg_r < 0


# ── Per-type split ────────────────────────────────────────────────────────────


def test_by_type_splits_scalp_and_swing():
    signals = [
        _closed(realized_r="2.0", signal_type="scalp"),
        _closed(realized_r="-1.0", signal_type="scalp"),
        _closed(realized_r="3.0", signal_type="swing"),
    ]
    by_type = _calc().compute(signals).by_type

    assert by_type["scalp"].total == 2
    assert by_type["scalp"].wins == 1
    assert by_type["swing"].total == 1
    assert by_type["swing"].wins == 1
    assert by_type["swing"].total_r == Decimal("3.0000")


# ── Calibration ───────────────────────────────────────────────────────────────


def test_calibration_buckets_by_stated_confidence():
    signals = [
        # 60-80% band: one win, one loss → realised 0.5 vs predicted ~0.7
        _closed(realized_r="2.0", confidence=0.70),
        _closed(realized_r="-1.0", confidence=0.70),
        # 80-100% band: both win → realised 1.0
        _closed(realized_r="1.5", confidence=0.90),
        _closed(realized_r="2.0", confidence=0.85),
    ]
    buckets = {b.label: b for b in _calc().compute(signals).calibration}

    assert buckets["60-80%"].count == 2
    assert buckets["60-80%"].win_rate == 0.5
    assert abs(buckets["60-80%"].avg_confidence - 0.70) < 1e-9
    assert buckets["80-100%"].count == 2
    assert buckets["80-100%"].win_rate == 1.0
    # Untouched bands stay empty but present.
    assert buckets["0-20%"].count == 0


def test_calibration_boundary_values_land_in_expected_bucket():
    # Exactly 0.2 → 20-40% band; exactly 1.0 → top 80-100% band (clamped).
    signals = [
        _closed(realized_r="1.0", confidence=0.2),
        _closed(realized_r="1.0", confidence=1.0),
        _closed(realized_r="1.0", confidence=0.0),
    ]
    buckets = {b.label: b for b in _calc().compute(signals).calibration}

    assert buckets["20-40%"].count == 1
    assert buckets["80-100%"].count == 1
    assert buckets["0-20%"].count == 1


def test_calibration_always_has_five_ordered_buckets():
    buckets = _calc().compute([]).calibration
    assert [b.label for b in buckets] == ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"]


# ── Equity curve ──────────────────────────────────────────────────────────────


def test_equity_curve_accumulates_in_input_order():
    signals = [
        _closed(realized_r="2.0", offset_minutes=0),
        _closed(realized_r="-1.0", offset_minutes=10),
        _closed(realized_r="3.0", offset_minutes=20),
    ]
    curve = _calc().compute(signals).equity_curve

    assert [p.cumulative_r for p in curve] == [
        Decimal("2.0000"),
        Decimal("1.0000"),
        Decimal("4.0000"),
    ]
    # The per-point realised R is preserved alongside the running total.
    assert [p.realized_r for p in curve] == [
        Decimal("2.0000"),
        Decimal("-1.0000"),
        Decimal("3.0000"),
    ]


def test_equity_curve_final_matches_total_r():
    signals = [_closed(realized_r="1.5"), _closed(realized_r="-1.0"), _closed(realized_r="2.25")]
    report = _calc().compute(signals)

    assert report.equity_curve[-1].cumulative_r == report.overall.total_r
