"""Analysis router — the run ledger (observability) + manual trigger.

Reads back the ``analysis_runs`` operators care about ("recent runs", run
detail, the signals a run produced) and exposes a manual trigger for the
pipeline. Reads go through the request-scoped
:class:`~app.controllers.analysis_run_controller.AnalysisRunController`; the
trigger uses the long-lived :class:`~app.controllers.analysis_controller.AnalysisController`
resolved off app state.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Query, status

from app.config import SettingsDep
from app.dependencies import (
    AnalysisControllerDep,
    AnalysisRunControllerDep,
    PaginationDep,
    SchedulerDep,
    SignalControllerDep,
)
from app.schemas.analysis import (
    AnalysisRunAccepted,
    AnalysisRunResponse,
    AnalysisRunStatusLiteral,
    PipelineStatusResponse,
)
from app.schemas.common import APIResponse, PaginatedResponse, PaginationMeta
from app.schemas.signal import SignalResponse
from app.tasks import ANALYSIS_JOB_ID

router = APIRouter(prefix="/analysis", tags=["Analysis"])

#: Run statuses that mean a cycle is actively in flight (vs. a terminal status).
_IN_FLIGHT_STATUSES = frozenset({"pending", "running"})


@router.get(
    "/runs",
    response_model=PaginatedResponse[AnalysisRunResponse],
    summary="List analysis runs (paginated, filterable by status)",
)
async def list_runs(
    controller: AnalysisRunControllerDep,
    pagination: PaginationDep,
    run_status: AnalysisRunStatusLiteral | None = Query(
        default=None,
        alias="status",
        description="Filter by run status (pending/running/success/partial/failed).",
    ),
) -> PaginatedResponse[AnalysisRunResponse]:
    page = await controller.list_runs(
        offset=pagination.offset,
        limit=pagination.limit,
        status=run_status,
    )
    return PaginatedResponse(
        data=page.items,
        pagination=PaginationMeta(
            total=page.total,
            page=pagination.page,
            per_page=pagination.per_page,
        ),
    )


@router.get(
    "/status",
    response_model=APIResponse[PipelineStatusResponse],
    summary="Live pipeline status + next scheduled run (for the 'next signal' UI)",
)
async def pipeline_status(
    controller: AnalysisRunControllerDep,
    scheduler: SchedulerDep,
    settings: SettingsDep,
) -> APIResponse[PipelineStatusResponse]:
    """Snapshot the pipeline so the UI can show progress and a countdown.

    ``state`` is derived rather than stored: the scheduler being switched off
    wins ("disabled"); otherwise a non-terminal latest run means a cycle is
    "running"; else we're "idle" between runs. ``next_run_at`` comes straight
    from the scheduler — the authoritative next fire time, which also stays
    correct across restarts, misfires, and manual triggers.
    """
    latest = await controller.get_latest()

    if not settings.scheduler_enabled:
        state = "disabled"
    elif latest is not None and latest.status in _IN_FLIGHT_STATUSES:
        state = "running"
    else:
        state = "idle"

    return APIResponse(
        data=PipelineStatusResponse(
            state=state,
            interval_minutes=settings.analysis_interval_minutes,
            next_run_at=scheduler.next_run_at(ANALYSIS_JOB_ID),
            last_run=latest,
        )
    )


@router.get(
    "/runs/{run_id}",
    response_model=APIResponse[AnalysisRunResponse],
    summary="Get a single analysis run by id",
)
async def get_run(
    run_id: uuid.UUID,
    controller: AnalysisRunControllerDep,
) -> APIResponse[AnalysisRunResponse]:
    run = await controller.get_run(run_id)
    return APIResponse(data=run)


@router.get(
    "/runs/{run_id}/signals",
    response_model=APIResponse[list[SignalResponse]],
    summary="Signals produced by an analysis run",
)
async def list_run_signals(
    run_id: uuid.UUID,
    controller: SignalControllerDep,
) -> APIResponse[list[SignalResponse]]:
    signals = await controller.list_for_run(run_id)
    return APIResponse(data=signals)


@router.post(
    "/runs",
    response_model=APIResponse[AnalysisRunAccepted],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger an analysis run manually",
)
async def trigger_run(
    controller: AnalysisControllerDep,
    background: BackgroundTasks,
) -> APIResponse[AnalysisRunAccepted]:
    """Kick off a pipeline run out-of-band from the schedule.

    The run is dispatched as a background task and the endpoint returns 202
    immediately — a full cycle spans every active pair's market-data and AI
    calls and would otherwise hold the request open for minutes. The client
    observes the result by polling ``GET /analysis/runs``.

    Note: this intentionally bypasses the scheduler's single-instance guard, so
    a manual trigger can overlap a scheduled cycle. That is acceptable for an
    operator-initiated action — each run is its own ledger row and the
    ``(pair_id, analysis_run_id)`` uniqueness constraint still prevents duplicate
    signals *within* a run.
    """
    background.add_task(controller.run_manual)
    return APIResponse(data=AnalysisRunAccepted())
