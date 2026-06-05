"""Repository for the ``signals`` table — the read-heavy entity.

Signals are the only thing the frontend actually paginates over, and
the analysis pipeline writes to this table once per pair per run. The
query helpers here are tuned around two access patterns:

1. *Latest signals for pair X* — covered by the composite
   ``(pair_id, generated_at)`` index declared on the model.
2. *All signals for run Y* — used by the post-run reporting view.

Bulk reads use ``selectinload(Signal.pair)`` rather than the model's
default ``lazy="joined"`` because that default is sized for individual
row hydration; for paginated lists, an IN-loaded follow-up query
beats N+1 lazy loads when the request happens to bypass the eager join
(e.g. via raw ``select`` with explicit ``options``).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, asc, desc, func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import ColumnExpressionArgument

from app.database.repository.base import BaseRepository
from app.models import Pair, Signal, SignalDirection, SignalOutcome, SignalType

# Result-category filter → the concrete outcomes it covers. Mirrors the frontend
# ``outcomeCategory`` grouping so a "Wins" filter means any take-profit rung.
_RESULT_OUTCOMES: dict[str, tuple[SignalOutcome, ...]] = {
    "open": (SignalOutcome.OPEN,),
    "win": (SignalOutcome.HIT_TP1, SignalOutcome.HIT_TP2, SignalOutcome.HIT_TP3),
    "loss": (SignalOutcome.HIT_SL,),
    "expired": (SignalOutcome.EXPIRED, SignalOutcome.CANCELLED),
}


class SignalRepository(BaseRepository[Signal]):
    model = Signal

    async def list_open(self, *, pair_id: int | None = None) -> Sequence[Signal]:
        """Every still-``OPEN`` signal, oldest first, optionally scoped to a pair.

        Drives the outcome job: these are the rows the evaluator re-checks each
        cycle. Oldest-first so a bounded batch (if ever introduced) processes the
        longest-waiting signals first. Hits ``ix_signals_outcome``.
        """
        stmt = select(Signal).where(Signal.outcome == SignalOutcome.OPEN)
        if pair_id is not None:
            stmt = stmt.where(Signal.pair_id == pair_id)
        stmt = stmt.order_by(Signal.generated_at)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    def mark_outcome(
        self,
        signal: Signal,
        *,
        outcome: SignalOutcome,
        realized_r: Decimal | None,
        mfe: Decimal | None,
        mae: Decimal | None,
        closed_at: datetime | None,
        last_evaluated_at: datetime,
    ) -> None:
        """Stage an outcome update onto an already-loaded signal.

        Like every write helper here it only *stages* the change on the session
        (mutating the tracked instance); the controller owns the commit. Kept as
        a named method so the outcome-field set lives in one place rather than
        being assigned ad hoc at the call site. The precise parameter types mean
        the type checker guards this write path (a stray ``float`` R, say) instead
        of being silenced by a blanket ignore.
        """
        signal.outcome = outcome
        signal.realized_r = realized_r
        signal.mfe = mfe
        signal.mae = mae
        signal.closed_at = closed_at
        signal.last_evaluated_at = last_evaluated_at

    async def latest_for_pair(
        self,
        pair_id: int,
        *,
        limit: int = 10,
        signal_type: SignalType | None = None,
    ) -> Sequence[Signal]:
        """The N most-recent signals for a pair, newest first.

        Optionally scoped to a single style. Hits the
        ``ix_signals_pair_id_signal_type_generated_at`` composite index (or the
        ``(pair_id, generated_at)`` one when unscoped) in a single backwards
        scan — no sort required at the planner level for typical PG configs.
        """
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        stmt = select(Signal).where(Signal.pair_id == pair_id)
        if signal_type is not None:
            stmt = stmt.where(Signal.signal_type == signal_type)
        stmt = stmt.order_by(desc(Signal.generated_at)).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def latest_open_by_pair(
        self, pair_ids: Sequence[int]
    ) -> dict[int, dict[SignalType, Signal | None]]:
        """Each pair's currently-**open** signal of each style, in one query.

        Feeds the AI's keep-or-adjust loop: the model should reason about the
        position that is actually live, so this filters to ``OPEN`` (a signal
        that already hit a TP/SL is closed and must not be presented as the
        current idea to keep). Batched across all active pairs — one indexed
        query instead of the previous two-per-pair N+1 — and bounded by the set
        of open signals (small: recent, unexpired rows), so it can't grow into
        the unbounded scan the recent-closed feedback deliberately avoids.

        Rows are ordered ascending by ``generated_at`` so a simple last-write-wins
        fold leaves the newest open signal per ``(pair, style)``. Every requested
        pair and every style is present as a key (mapping to ``None`` when absent)
        so callers never need a membership check.
        """
        result: dict[int, dict[SignalType, Signal | None]] = {
            pair_id: dict.fromkeys(SignalType) for pair_id in pair_ids
        }
        if not pair_ids:
            return result

        stmt = (
            select(Signal)
            .where(Signal.outcome == SignalOutcome.OPEN, Signal.pair_id.in_(pair_ids))
            .order_by(Signal.pair_id, Signal.signal_type, Signal.generated_at)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        for row in rows:
            result[row.pair_id][row.signal_type] = row
        return result

    @staticmethod
    def _filter_conditions(
        *,
        pair_id: int | None,
        analysis_run_id: uuid.UUID | None,
        signal_type: SignalType | None,
        outcome: SignalOutcome | None,
        direction: SignalDirection | None,
        result: str | None,
        status: str | None,
        now: datetime | None,
    ) -> list[ColumnExpressionArgument[bool]]:
        """The shared WHERE clauses for the signal list + its count.

        Factored so :meth:`list_paginated` and :meth:`count_filtered` can never
        drift — a filter applied to one but not the other would make the
        pagination total disagree with the rows. ``status`` is lifecycle-derived
        (direction + expiry vs. ``now``); ``result`` maps a result category onto
        its outcome set.
        """
        conditions: list[ColumnExpressionArgument[bool]] = []
        if pair_id is not None:
            conditions.append(Signal.pair_id == pair_id)
        if analysis_run_id is not None:
            conditions.append(Signal.analysis_run_id == analysis_run_id)
        if signal_type is not None:
            conditions.append(Signal.signal_type == signal_type)
        if outcome is not None:
            conditions.append(Signal.outcome == outcome)
        if direction is not None:
            conditions.append(Signal.direction == direction)
        if result is not None and result in _RESULT_OUTCOMES:
            conditions.append(Signal.outcome.in_(_RESULT_OUTCOMES[result]))
        if status is not None and now is not None:
            unexpired = or_(Signal.expires_at.is_(None), Signal.expires_at >= now)
            if status == "expired":
                conditions.append(
                    and_(Signal.expires_at.is_not(None), Signal.expires_at < now)
                )
            elif status == "watchlist":
                conditions.append(and_(Signal.direction == SignalDirection.NEUTRAL, unexpired))
            elif status == "active":
                conditions.append(and_(Signal.direction != SignalDirection.NEUTRAL, unexpired))
        return conditions

    @staticmethod
    def _order_by(sort: str | None) -> list[ColumnExpressionArgument[object]]:
        """Map a sort key to ORDER BY columns (default: newest first).

        ``symbol`` orders by the pair's symbol and so requires the caller to join
        ``Pair`` (``list_paginated`` does); ``generated_at`` is always the final
        tiebreak for a stable, deterministic order.
        """
        if sort == "confidence":
            return [desc(Signal.confidence), desc(Signal.generated_at)]
        if sort == "symbol":
            return [asc(Pair.symbol), desc(Signal.generated_at)]
        return [desc(Signal.generated_at)]

    async def list_paginated(
        self,
        *,
        offset: int,
        limit: int,
        pair_id: int | None = None,
        analysis_run_id: uuid.UUID | None = None,
        signal_type: SignalType | None = None,
        outcome: SignalOutcome | None = None,
        direction: SignalDirection | None = None,
        result: str | None = None,
        status: str | None = None,
        sort: str | None = None,
        now: datetime | None = None,
        eager_load_pair: bool = False,
    ) -> Sequence[Signal]:
        """Generic signal list with optional filters, sort, and IN-loaded pair.

        ``eager_load_pair=True`` fetches the related ``Pair`` row in a second IN
        query, which is what response models that surface the symbol need.
        Filters/sort are pushed to the database (not applied to a loaded page) so
        the result is correct and complete across pagination.
        """
        stmt = select(Signal).where(
            *self._filter_conditions(
                pair_id=pair_id,
                analysis_run_id=analysis_run_id,
                signal_type=signal_type,
                outcome=outcome,
                direction=direction,
                result=result,
                status=status,
                now=now,
            )
        )
        if sort == "symbol":
            stmt = stmt.join(Pair, Signal.pair_id == Pair.id)
        if eager_load_pair:
            stmt = stmt.options(selectinload(Signal.pair))
        stmt = stmt.order_by(*self._order_by(sort)).offset(offset).limit(limit)
        result_set = await self._session.execute(stmt)
        return result_set.scalars().all()

    async def count_filtered(
        self,
        *,
        pair_id: int | None = None,
        analysis_run_id: uuid.UUID | None = None,
        signal_type: SignalType | None = None,
        outcome: SignalOutcome | None = None,
        direction: SignalDirection | None = None,
        result: str | None = None,
        status: str | None = None,
        now: datetime | None = None,
    ) -> int:
        """Row count matching the same filters as :meth:`list_paginated`.

        Shares :meth:`_filter_conditions` with the list query so the two can't
        drift and the ``PaginatedResponse`` total always matches the rows.
        """
        stmt = select(func.count()).select_from(Signal).where(
            *self._filter_conditions(
                pair_id=pair_id,
                analysis_run_id=analysis_run_id,
                signal_type=signal_type,
                outcome=outcome,
                direction=direction,
                result=result,
                status=status,
                now=now,
            )
        )
        count_result = await self._session.execute(stmt)
        return int(count_result.scalar_one())

    async def list_closed_for_performance(
        self,
        *,
        pair_id: int | None = None,
        signal_type: SignalType | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> Sequence[Signal]:
        """Closed, R-scored signals for the performance API, oldest-close first.

        The performance track record is built only from signals that have both a
        terminal outcome *and* a defined ``realized_r`` — open signals have no
        result yet, and a stop-less signal has no risk to denominate R in, so
        neither can be scored. ``realized_r IS NOT NULL`` already excludes the open
        rows (R is only stamped at close), but the explicit ``outcome`` filter
        keeps the intent readable and the index (``ix_signals_outcome``) usable.

        Ordered by ``closed_at`` (then ``generated_at``, then ``id`` for
        determinism) so the controller can build the equity curve straight from
        the rows without re-sorting. ``start``/``end`` bound the *close* time,
        matching the ``from``/``to`` query window the equity curve is read over.
        """
        stmt = select(Signal).where(
            Signal.outcome != SignalOutcome.OPEN,
            Signal.realized_r.is_not(None),
        )
        if pair_id is not None:
            stmt = stmt.where(Signal.pair_id == pair_id)
        if signal_type is not None:
            stmt = stmt.where(Signal.signal_type == signal_type)
        if start is not None:
            stmt = stmt.where(Signal.closed_at >= start)
        if end is not None:
            stmt = stmt.where(Signal.closed_at <= end)
        stmt = stmt.order_by(Signal.closed_at, Signal.generated_at, Signal.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_recent_closed(
        self,
        *,
        pair_id: int,
        signal_type: SignalType | None = None,
        limit: int = 20,
    ) -> Sequence[Signal]:
        """The most-recent closed, R-scored signals for a pair, newest first.

        Backs the Iteration 9 feedback loop: the analysis controller summarises
        these into the "your recent track record" block fed back to the model.
        Same scored set as the performance API (terminal outcome *and* a defined
        ``realized_r``), but bounded and newest-first so the feedback reflects
        *recent* behaviour rather than the whole history.
        """
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        stmt = select(Signal).where(
            Signal.outcome != SignalOutcome.OPEN,
            Signal.realized_r.is_not(None),
        )
        if signal_type is not None:
            stmt = stmt.where(Signal.signal_type == signal_type)
        stmt = stmt.where(Signal.pair_id == pair_id)
        stmt = stmt.order_by(desc(Signal.closed_at)).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_for_run(self, analysis_run_id: uuid.UUID) -> Sequence[Signal]:
        """All signals produced by a single analysis run, ordered by pair.

        Used by the run-detail report. Pair-ordered output keeps the
        report stable across re-renders.
        """
        stmt = (
            select(Signal).where(Signal.analysis_run_id == analysis_run_id).order_by(Signal.pair_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
