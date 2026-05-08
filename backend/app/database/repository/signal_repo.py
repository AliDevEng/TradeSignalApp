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
from app.models import Signal


class SignalRepository(BaseRepository[Signal]):
    model = Signal

    async def latest_for_pair(
        self,
        pair_id: int,
        *,
        limit: int = 10,
    ) -> Sequence[Signal]:
        """The N most-recent signals for a pair, newest first.

        Hits the ``ix_signals_pair_id_generated_at`` composite index in
        a single backwards scan — no sort required at the planner
        level for typical PG configurations.
        """
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        stmt = (
            select(Signal)
            .where(Signal.pair_id == pair_id)
            .order_by(desc(Signal.generated_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_paginated(
        self,
        *,
        offset: int,
        limit: int,
        pair_id: int | None = None,
        analysis_run_id: uuid.UUID | None = None,
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
