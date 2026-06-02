"""Integration tests for the v1 API routes (signals / pairs / analysis).

These drive the real ASGI app through the response-envelope and error-handler
machinery, but stub the controllers via ``app.dependency_overrides`` so no
database is touched. What's under test here is exactly the view layer's job:
HTTP translation (path/query validation, status codes, pagination meta), the
shared success/error envelope, and the central mapping of a controller's
``ResourceNotFoundError`` onto a 404 — not the business logic, which the
controller unit tests already cover.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from app.controllers.analysis_run_controller import AnalysisRunController
from app.controllers.exceptions import ResourceNotFoundError
from app.controllers.pair_controller import PairController
from app.controllers.results import Page
from app.controllers.signal_controller import SignalController
from app.dependencies import (
    get_analysis_controller,
    get_analysis_run_controller,
    get_pair_controller,
    get_signal_controller,
)
from httpx import ASGITransport, AsyncClient

from tests._factories import make_pair, make_run, make_signal

# Wire-schema samples, built by reusing each controller's own ORM→wire mapper so
# the expected shape can't drift from production mapping.
SIGNAL = SignalController._to_response(make_signal())
PAIR = PairController._to_response(make_pair())
RUN = AnalysisRunController._to_response(make_run())


@pytest.fixture
def signals_ctrl(app) -> AsyncMock:
    mock = AsyncMock(spec=SignalController)
    app.dependency_overrides[get_signal_controller] = lambda: mock
    return mock


@pytest.fixture
def pairs_ctrl(app) -> AsyncMock:
    mock = AsyncMock(spec=PairController)
    app.dependency_overrides[get_pair_controller] = lambda: mock
    return mock


@pytest.fixture
def runs_ctrl(app) -> AsyncMock:
    mock = AsyncMock(spec=AnalysisRunController)
    app.dependency_overrides[get_analysis_run_controller] = lambda: mock
    return mock


@pytest.fixture
def analysis_ctrl(app) -> AsyncMock:
    mock = AsyncMock()
    app.dependency_overrides[get_analysis_controller] = lambda: mock
    return mock


# ── GET /signals ─────────────────────────────────────────────────────────────


async def test_list_signals_wraps_page_in_paginated_envelope(client, signals_ctrl):
    signals_ctrl.list_signals.return_value = Page(items=[SIGNAL], total=1)

    resp = await client.get("/api/v1/signals")
    body = resp.json()

    assert resp.status_code == 200
    assert body["success"] is True
    assert len(body["data"]) == 1
    assert body["pagination"] == {"total": 1, "page": 1, "per_page": 20, "pages": 1}


async def test_list_signals_forwards_pagination_and_filters(client, signals_ctrl):
    signals_ctrl.list_signals.return_value = Page(items=[], total=0)
    run_id = uuid.uuid4()

    await client.get(f"/api/v1/signals?page=2&per_page=5&pair=EURUSD&run_id={run_id}")

    kwargs = signals_ctrl.list_signals.await_args.kwargs
    assert kwargs == {
        "offset": 5,
        "limit": 5,
        "pair_symbol": "EURUSD",
        "analysis_run_id": run_id,
    }


async def test_list_signals_rejects_invalid_pagination(client, signals_ctrl):
    resp = await client.get("/api/v1/signals?page=0")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_list_signals_per_page_over_cap_is_rejected(client, signals_ctrl):
    resp = await client.get("/api/v1/signals?per_page=101")
    assert resp.status_code == 422


async def test_db_unreachable_maps_to_503_not_500(client, signals_ctrl):
    """A connection-level DB failure must surface as a retryable 503, never a
    500 'looks like a bug' — the regression this iteration's fix closes."""
    from app.database import DatabaseConnectionError

    signals_ctrl.list_signals.side_effect = DatabaseConnectionError(
        "connection was closed in the middle of operation"
    )

    resp = await client.get("/api/v1/signals")
    body = resp.json()

    assert resp.status_code == 503
    assert body["success"] is False
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    # The raw driver/connection text must not leak to the client.
    assert "connection was closed" not in body["error"]["message"]


async def test_list_signals_unknown_pair_filter_maps_to_404(client, signals_ctrl):
    signals_ctrl.list_signals.side_effect = ResourceNotFoundError("pair", "NOPE")

    resp = await client.get("/api/v1/signals?pair=NOPE")
    body = resp.json()

    assert resp.status_code == 404
    assert body["success"] is False
    assert body["error"]["code"] == "NOT_FOUND"


# ── GET /signals/{id} ────────────────────────────────────────────────────────


async def test_get_signal_returns_single_envelope(client, signals_ctrl):
    signals_ctrl.get_signal.return_value = SIGNAL

    resp = await client.get(f"/api/v1/signals/{SIGNAL.id}")
    body = resp.json()

    assert resp.status_code == 200
    assert body["success"] is True
    assert body["data"]["id"] == str(SIGNAL.id)
    # Money serialises as a JSON string, per the "never float for prices" rule.
    assert body["data"]["entry_price"] == str(SIGNAL.entry_price)


async def test_get_signal_missing_maps_to_404(client, signals_ctrl):
    missing = uuid.uuid4()
    signals_ctrl.get_signal.side_effect = ResourceNotFoundError("signal", missing)

    resp = await client.get(f"/api/v1/signals/{missing}")
    assert resp.status_code == 404


async def test_get_signal_invalid_uuid_is_422(client, signals_ctrl):
    resp = await client.get("/api/v1/signals/not-a-uuid")
    assert resp.status_code == 422


# ── GET /pairs ───────────────────────────────────────────────────────────────


async def test_list_pairs_returns_unpaginated_list(client, pairs_ctrl):
    pairs_ctrl.list_pairs.return_value = [PAIR]

    resp = await client.get("/api/v1/pairs")
    body = resp.json()

    assert resp.status_code == 200
    assert body["success"] is True
    assert body["data"][0]["symbol"] == PAIR.symbol
    assert "pagination" not in body or body.get("pagination") is None
    pairs_ctrl.list_pairs.assert_awaited_once_with(include_inactive=False)


async def test_list_pairs_include_inactive_flag_is_forwarded(client, pairs_ctrl):
    pairs_ctrl.list_pairs.return_value = []
    await client.get("/api/v1/pairs?include_inactive=true")
    pairs_ctrl.list_pairs.assert_awaited_once_with(include_inactive=True)


async def test_get_pair_found(client, pairs_ctrl):
    pairs_ctrl.get_pair.return_value = PAIR
    resp = await client.get("/api/v1/pairs/EURUSD")
    assert resp.status_code == 200
    assert resp.json()["data"]["symbol"] == PAIR.symbol


async def test_get_pair_missing_maps_to_404(client, pairs_ctrl):
    pairs_ctrl.get_pair.side_effect = ResourceNotFoundError("pair", "NOPE")
    resp = await client.get("/api/v1/pairs/NOPE")
    assert resp.status_code == 404


# ── GET /pairs/{symbol}/signals ──────────────────────────────────────────────


async def test_list_pair_signals_uses_signal_controller(client, signals_ctrl):
    signals_ctrl.list_latest_for_pair.return_value = [SIGNAL]

    resp = await client.get("/api/v1/pairs/EURUSD/signals?limit=5")
    body = resp.json()

    assert resp.status_code == 200
    assert len(body["data"]) == 1
    signals_ctrl.list_latest_for_pair.assert_awaited_once_with("EURUSD", limit=5)


async def test_list_pair_signals_limit_validation(client, signals_ctrl):
    resp = await client.get("/api/v1/pairs/EURUSD/signals?limit=0")
    assert resp.status_code == 422


# ── GET /analysis/runs ───────────────────────────────────────────────────────


async def test_list_runs_paginated_envelope(client, runs_ctrl):
    runs_ctrl.list_runs.return_value = Page(items=[RUN], total=1)

    resp = await client.get("/api/v1/analysis/runs")
    body = resp.json()

    assert resp.status_code == 200
    assert body["data"][0]["id"] == str(RUN.id)
    assert body["pagination"]["total"] == 1


async def test_list_runs_status_filter_is_forwarded(client, runs_ctrl):
    runs_ctrl.list_runs.return_value = Page(items=[], total=0)
    await client.get("/api/v1/analysis/runs?status=failed")
    assert runs_ctrl.list_runs.await_args.kwargs["status"] == "failed"


async def test_list_runs_rejects_unknown_status(client, runs_ctrl):
    resp = await client.get("/api/v1/analysis/runs?status=bogus")
    assert resp.status_code == 422


async def test_get_run_found(client, runs_ctrl):
    runs_ctrl.get_run.return_value = RUN
    resp = await client.get(f"/api/v1/analysis/runs/{RUN.id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == RUN.status


async def test_get_run_missing_maps_to_404(client, runs_ctrl):
    missing = uuid.uuid4()
    runs_ctrl.get_run.side_effect = ResourceNotFoundError("analysis run", missing)
    resp = await client.get(f"/api/v1/analysis/runs/{missing}")
    assert resp.status_code == 404


async def test_list_run_signals(client, signals_ctrl):
    signals_ctrl.list_for_run.return_value = [SIGNAL]
    run_id = uuid.uuid4()

    resp = await client.get(f"/api/v1/analysis/runs/{run_id}/signals")

    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1
    signals_ctrl.list_for_run.assert_awaited_once_with(run_id)


# ── POST /analysis/runs ──────────────────────────────────────────────────────


async def test_trigger_run_returns_202_and_dispatches_background_task(app, analysis_ctrl):
    # A fresh client so the background task runs to completion on context exit.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/analysis/runs")
        body = resp.json()

    assert resp.status_code == 202
    assert body["success"] is True
    assert body["data"]["status"] == "accepted"
    # The pipeline is dispatched out-of-band, not awaited inline.
    analysis_ctrl.run_manual.assert_awaited_once()
