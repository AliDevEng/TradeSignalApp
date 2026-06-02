"""Unit tests for :class:`AnalysisRunController` — the run-ledger read service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from app.controllers.analysis_run_controller import AnalysisRunController
from app.controllers.exceptions import ResourceNotFoundError
from app.models import AnalysisRunStatus
from app.schemas.analysis import AnalysisRunResponse

from tests._factories import make_run


def _controller(runs: AsyncMock | None = None):
    runs = runs or AsyncMock()
    return AnalysisRunController(runs=runs), runs


async def test_list_runs_returns_page_with_mapped_items():
    ctrl, runs = _controller()
    runs.count_filtered.return_value = 2
    runs.list_paginated.return_value = [make_run(), make_run()]

    page = await ctrl.list_runs(offset=0, limit=20)

    assert page.total == 2
    assert all(isinstance(r, AnalysisRunResponse) for r in page.items)


async def test_list_runs_short_circuits_when_count_zero():
    ctrl, runs = _controller()
    runs.count_filtered.return_value = 0

    page = await ctrl.list_runs(offset=0, limit=20)

    assert page.items == []
    runs.list_paginated.assert_not_awaited()


async def test_list_runs_converts_status_literal_to_enum_at_boundary():
    """The view passes a validated string; the controller owns the enum cast."""
    ctrl, runs = _controller()
    runs.count_filtered.return_value = 0

    await ctrl.list_runs(offset=0, limit=20, status="failed")

    assert runs.count_filtered.await_args.kwargs["status"] is AnalysisRunStatus.FAILED


async def test_list_runs_no_status_filter_passes_none():
    ctrl, runs = _controller()
    runs.count_filtered.return_value = 0

    await ctrl.list_runs(offset=0, limit=20)

    assert runs.count_filtered.await_args.kwargs["status"] is None


async def test_get_run_returns_mapped_response():
    run = make_run(status=AnalysisRunStatus.PARTIAL, pairs_failed=1)
    ctrl, runs = _controller()
    runs.get.return_value = run

    result = await ctrl.get_run(run.id)

    assert isinstance(result, AnalysisRunResponse)
    assert result.status == "partial"
    assert result.pairs_failed == 1


async def test_get_run_missing_raises_not_found():
    ctrl, runs = _controller()
    runs.get.return_value = None
    missing = uuid.uuid4()

    with pytest.raises(ResourceNotFoundError) as exc:
        await ctrl.get_run(missing)
    assert exc.value.resource == "analysis run"
    assert exc.value.identifier == str(missing)
