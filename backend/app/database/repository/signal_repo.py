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

from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload

from app.database.repository.base import BaseRepository
from app.models import Signal, SignalOutcome, SignalType


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
        realized_r: object | None,
        mfe: object | None,
        mae: object | None,
        closed_at: object | None,
        last_evaluated_at: object,
    ) -> None:
        """Stage an outcome update onto an already-loaded signal.

        Like every write helper here it only *stages* the change on the session
        (mutating the tracked instance); the controller owns the commit. Kept as
        a named method so the outcome-field set lives in one place rather than
        being assigned ad hoc at the call site.
        """
        signal.outcome = outcome
        signal.realized_r = realized_r  # type: ignore[assignment]
        signal.mfe = mfe  # type: ignore[assignment]
        signal.mae = mae  # type: ignore[assignment]
        signal.closed_at = closed_at  # type: ignore[assignment]
        signal.last_evaluated_at = last_evaluated_at  # type: ignore[assignment]

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

    async def current_for_pair(self, pair_id: int) -> dict[SignalType, Signal | None]:
        """The pair's currently-open signal of each style (latest per style).

        Used both to feed the AI's keep-or-adjust loop and to render the "current
        scalp + swing" view. Returns every style as a key so callers can rely on
        the shape without a membership check; an absent style maps to ``None``.
        """
        current: dict[SignalType, Signal | None] = dict.fromkeys(SignalType)
        for style in SignalType:
            rows = await self.latest_for_pair(pair_id, limit=1, signal_type=style)
            current[style] = rows[0] if rows else None
        return current

    async def list_paginated(
        self,
        *,
        offset: int,
        limit: int,
        pair_id: int | None = None,
        analysis_run_id: uuid.UUID | None = None,
        signal_type: SignalType | None = None,
        outcome: SignalOutcome | None = None,
        eager_load_pair: bool = False,
    ) -> Sequence[Signal]:
        """Generic signal list with optional filters and IN-loaded pair.

        ``eager_load_pair=True`` fetches the related ``Pair`` row in a
        second IN query, which is what response models that surface the
        symbol need. Default off so callers that don't need it pay
        nothing.
        """
        stmt = select(Signal)
        if pair_id is not None:
            stmt = stmt.where(Signal.pair_id == pair_id)
        if analysis_run_id is not None:
            stmt = stmt.where(Signal.analysis_run_id == analysis_run_id)
        if signal_type is not None:
            stmt = stmt.where(Signal.signal_type == signal_type)
        if outcome is not None:
            stmt = stmt.where(Signal.outcome == outcome)
        if eager_load_pair:
            stmt = stmt.options(selectinload(Signal.pair))
        stmt = stmt.order_by(desc(Signal.generated_at)).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_filtered(
        self,
        *,
        pair_id: int | None = None,
        analysis_run_id: uuid.UUID | None = None,
        signal_type: SignalType | None = None,
        outcome: SignalOutcome | None = None,
    ) -> int:
        """Row count matching the same filters as :meth:`list_paginated`.

        Kept symmetric with ``list_paginated`` so the two together
        produce a consistent ``PaginatedResponse`` envelope.
        """
        stmt = select(func.count()).select_from(Signal)
        if pair_id is not None:
            stmt = stmt.where(Signal.pair_id == pair_id)
        if analysis_run_id is not None:
            stmt = stmt.where(Signal.analysis_run_id == analysis_run_id)
        if signal_type is not None:
            stmt = stmt.where(Signal.signal_type == signal_type)
        if outcome is not None:
            stmt = stmt.where(Signal.outcome == outcome)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

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

    async def delete_expired(self, *, now: datetime) -> int:
        """Drop signals whose ``expires_at`` has passed. Returns row count.

        Used by the retention sweep. Deliberately bulk DELETE rather
        than load-then-delete: expired-signal sweeps are dominated by
        rows that never need to be hydrated into Python.
        """
        return await self.delete_where(
            Signal.expires_at.is_not(None),
            Signal.expires_at < now,
        )
