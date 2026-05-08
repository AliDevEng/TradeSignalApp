"""Repository for the ``analysis_runs`` table.

Analysis runs are append-only from the application's perspective: the
scheduler creates a row in ``RUNNING`` state and updates it to a
terminal status (``SUCCESS`` / ``PARTIAL`` / ``FAILED``) when the
pipeline finishes. Listing is dominated by the dashboard's
"recent runs" widget, which is what the index on
``started_at`` is sized for.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import desc, func, select

from app.database.repository.base import BaseRepository
from app.models import AnalysisRun, AnalysisRunStatus


class AnalysisRunRepository(BaseRepository[AnalysisRun]):
    model = AnalysisRun

    async def list_recent(self, *, limit: int = 20) -> Sequence[AnalysisRun]:
        """Most-recent runs first — backs the operator dashboard."""
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        stmt = select(AnalysisRun).order_by(desc(AnalysisRun.started_at)).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_paginated(
        self,
        *,
        offset: int,
        limit: int,
        status: AnalysisRunStatus | None = None,
    ) -> Sequence[AnalysisRun]:
        """Paginated view, ordered newest-first, optionally filtered by status."""
        stmt = select(AnalysisRun)
        if status is not None:
            stmt = stmt.where(AnalysisRun.status == status)
        stmt = stmt.order_by(desc(AnalysisRun.started_at)).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_filtered(
        self,
        *,
        status: AnalysisRunStatus | None = None,
    ) -> int:
        """Row count matching the filter set used by :meth:`list_paginated`."""
        stmt = select(func.count()).select_from(AnalysisRun)
        if status is not None:
            stmt = stmt.where(AnalysisRun.status == status)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_latest_successful(self) -> AnalysisRun | None:
        """Most-recent run that reached ``SUCCESS``.

        Used by the health endpoint (a stale "last successful run"
        timestamp signals a stuck pipeline) and by the AI provider
        fallback path that reuses the previous run's signals when a
        live run fails.
        """
        stmt = (
            select(AnalysisRun)
            .where(AnalysisRun.status == AnalysisRunStatus.SUCCESS)
            .order_by(desc(AnalysisRun.started_at))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()
