"""The analysis-run controller — read-side business logic for the run ledger.

This is the *query* companion to the
:class:`~app.controllers.analysis_controller.AnalysisController` (which *writes*
runs as it executes the pipeline). Splitting read from write keeps the two
construction styles honest: the orchestrator owns its own sessions because it
runs in the background, whereas this controller is request-scoped and borrows
the request session through an injected ``AnalysisRunRepository``.

It backs the operator dashboard's "recent runs" view and the run-detail page,
mapping the ORM ``AnalysisRun`` onto the wire :class:`AnalysisRunResponse`.
"""

from __future__ import annotations

import uuid

from app.controllers.exceptions import ResourceNotFoundError
from app.controllers.results import Page
from app.database.repository import AnalysisRunRepository
from app.models import AnalysisRun, AnalysisRunStatus
from app.schemas.analysis import AnalysisRunResponse


class AnalysisRunController:
    """Serves paginated and single-resource reads over ``analysis_runs``."""

    def __init__(self, *, runs: AnalysisRunRepository) -> None:
        self._runs = runs

    async def list_runs(
        self,
        *,
        offset: int,
        limit: int,
        status: str | None = None,
    ) -> Page[AnalysisRunResponse]:
        """A page of runs, newest first, optionally filtered by status.

        ``status`` arrives as the validated wire literal; it is converted to the
        ORM enum here, at the boundary, so the view never imports the model enum.
        """
        status_enum = AnalysisRunStatus(status) if status is not None else None

        total = await self._runs.count_filtered(status=status_enum)
        if total == 0:
            return Page(items=[], total=0)

        rows = await self._runs.list_paginated(offset=offset, limit=limit, status=status_enum)
        return Page(items=[self._to_response(run) for run in rows], total=total)

    async def get_run(self, run_id: uuid.UUID) -> AnalysisRunResponse:
        """A single run by id, or :class:`ResourceNotFoundError` if absent."""
        run = await self._runs.get(run_id)
        if run is None:
            raise ResourceNotFoundError("analysis run", run_id)
        return self._to_response(run)

    @staticmethod
    def _to_response(run: AnalysisRun) -> AnalysisRunResponse:
        return AnalysisRunResponse(
            id=run.id,
            status=run.status.value,
            trigger=run.trigger.value,
            timeframe=run.timeframe,
            candle_count=run.candle_count,
            started_at=run.started_at,
            finished_at=run.finished_at,
            pairs_processed=run.pairs_processed,
            pairs_failed=run.pairs_failed,
            ai_provider=run.ai_provider,
            ai_model=run.ai_model,
            error_message=run.error_message,
        )
