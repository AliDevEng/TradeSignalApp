"""The performance controller — read-side business logic for the track record.

This is the aggregation companion to the outcome work: the
:class:`~app.controllers.outcome_controller.OutcomeController` *records* what
price did to each signal, and this controller *rolls those records up* into the
numbers the frontend's performance dashboard charts — win-rate, profit factor,
expectancy, total R (overall and per style), a confidence-calibration table, and
an equity curve.

Like the other read controllers it is **request-scoped**: it borrows the
request's session through injected repositories and never owns transaction
lifecycle. Its job is the translation the view must not do itself — resolve a
pair *symbol* → id, cast the wire ``signal_type`` literal to the ORM enum, fetch
the closed rows, hand them to the pure :class:`PerformanceCalculator`, and map the
result onto the wire :class:`PerformanceResponse`.

The arithmetic deliberately lives in the pure calculator, not in SQL: it keeps
the track-record maths fully unit-testable and back-testable (the same discipline
as the outcome evaluator), and the closed-signal set for a single-pair focus is
small enough that in-memory aggregation is the honest, cheaper-to-trust choice.

Layering: imports services, repositories, models, schemas; never ``app.views`` or
``fastapi``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from app.controllers.exceptions import ResourceNotFoundError
from app.database.repository import PairRepository, SignalRepository
from app.models import Signal, SignalType
from app.schemas.performance import (
    CalibrationBucket,
    EquityPoint,
    PerformanceResponse,
    PerformanceSummary,
)
from app.services.performance import (
    ClosedSignal,
    PerformanceCalculator,
)
from app.services.performance import (
    PerformanceSummary as CalcSummary,
)


def _utcnow() -> datetime:
    """Timezone-aware UTC now. Injected so tests can pin the report timestamp."""
    return datetime.now(UTC)


class PerformanceController:
    """Serves the aggregated track record over the ``signals`` table."""

    def __init__(
        self,
        *,
        signals: SignalRepository,
        pairs: PairRepository,
        calculator: PerformanceCalculator | None = None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._signals = signals
        self._pairs = pairs
        self._calculator = calculator or PerformanceCalculator()
        self._clock = clock

    async def get_performance(
        self,
        *,
        pair_symbol: str | None = None,
        signal_type: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> PerformanceResponse:
        """The full track record over the closed signals matching the filters.

        ``pair_symbol``/``signal_type`` arrive as the validated wire inputs and are
        converted to ORM identifiers here, at the boundary. A ``pair_symbol`` that
        names no known pair raises :class:`ResourceNotFoundError` rather than
        quietly returning an empty report — a filter that names a concrete resource
        should fail honestly when that resource is unknown.
        """
        pair_id = await self._resolve_pair_id(pair_symbol)
        style = SignalType(signal_type) if signal_type is not None else None

        rows = await self._signals.list_closed_for_performance(
            pair_id=pair_id,
            signal_type=style,
            start=start,
            end=end,
        )
        report = self._calculator.compute(self._to_closed(rows))

        return PerformanceResponse(
            overall=self._summary_to_wire(report.overall),
            by_type={
                style_key: self._summary_to_wire(summary)
                for style_key, summary in report.by_type.items()
            },
            calibration=[
                CalibrationBucket(
                    label=b.label,
                    lower=b.lower,
                    upper=b.upper,
                    count=b.count,
                    avg_confidence=b.avg_confidence,
                    win_rate=b.win_rate,
                    wins=b.wins,
                )
                for b in report.calibration
            ],
            equity_curve=[
                EquityPoint(
                    signal_id=p.signal_id,
                    closed_at=p.closed_at,
                    realized_r=p.realized_r,
                    cumulative_r=p.cumulative_r,
                )
                for p in report.equity_curve
            ],
            generated_at=self._clock(),
        )

    # ── Mapping ──────────────────────────────────────────────────────────────

    async def _resolve_pair_id(self, symbol: str | None) -> int | None:
        if symbol is None:
            return None
        pair = await self._pairs.get_by_symbol(symbol)
        if pair is None:
            raise ResourceNotFoundError("pair", symbol)
        return pair.id

    @staticmethod
    def _to_closed(rows: Sequence[Signal]) -> list[ClosedSignal]:
        """Map ORM rows onto the calculator's ORM-free input.

        Reads scalar columns only (no ``pair`` relationship access), so it is safe
        without eager loading and cannot trigger a lazy load. The repository
        guarantees ``realized_r`` is set, so the ``assert`` is a contract check,
        not control flow.
        """
        closed: list[ClosedSignal] = []
        for row in rows:
            assert row.realized_r is not None  # repository invariant: scored rows only
            assert row.closed_at is not None  # set whenever a signal is closed
            closed.append(
                ClosedSignal(
                    signal_id=row.id,
                    signal_type=row.signal_type.value,  # type: ignore[arg-type]
                    confidence=row.confidence,
                    realized_r=row.realized_r,
                    closed_at=row.closed_at,
                )
            )
        return closed

    @staticmethod
    def _summary_to_wire(summary: CalcSummary) -> PerformanceSummary:
        return PerformanceSummary(
            total=summary.total,
            wins=summary.wins,
            losses=summary.losses,
            win_rate=summary.win_rate,
            total_r=summary.total_r,
            avg_r=summary.avg_r,
            profit_factor=summary.profit_factor,
            gross_profit=summary.gross_profit,
            gross_loss=summary.gross_loss,
        )
