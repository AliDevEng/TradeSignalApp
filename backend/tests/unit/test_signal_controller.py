"""Unit tests for :class:`SignalController` — the read-side query service.

The controller is exercised against ``AsyncMock`` repositories rather than a
live database: its job is orchestration (resolve a symbol → id, drive the repos,
map ORM → wire), and that logic is fully observable through the calls it makes
and the schemas it returns. Round-trip "the SQL returns the right rows" coverage
belongs to the repository SQL tests and the integration suite.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from app.controllers.exceptions import ResourceNotFoundError
from app.controllers.signal_controller import SignalController
from app.schemas.signal import SignalResponse

from tests._factories import make_pair, make_signal


def _controller(*, signals: AsyncMock | None = None, pairs: AsyncMock | None = None):
    signals = signals or AsyncMock()
    pairs = pairs or AsyncMock()
    return SignalController(signals=signals, pairs=pairs), signals, pairs


# ── list_signals ─────────────────────────────────────────────────────────────


async def test_list_signals_returns_page_with_total_and_mapped_items():
    ctrl, signals, _ = _controller()
    signals.count_filtered.return_value = 2
    signals.list_paginated.return_value = [make_signal(), make_signal()]

    page = await ctrl.list_signals(offset=0, limit=20)

    assert page.total == 2
    assert len(page.items) == 2
    assert all(isinstance(item, SignalResponse) for item in page.items)


async def test_list_signals_short_circuits_when_count_zero():
    """An empty result must not issue a guaranteed-empty SELECT for rows."""
    ctrl, signals, _ = _controller()
    signals.count_filtered.return_value = 0

    page = await ctrl.list_signals(offset=0, limit=20)

    assert page.total == 0
    assert page.items == []
    signals.list_paginated.assert_not_awaited()


async def test_list_signals_resolves_pair_symbol_to_id():
    pair = make_pair(id=7, symbol="GBPUSD")
    ctrl, signals, pairs = _controller()
    pairs.get_by_symbol.return_value = pair
    signals.count_filtered.return_value = 0

    await ctrl.list_signals(offset=0, limit=20, pair_symbol="GBPUSD")

    pairs.get_by_symbol.assert_awaited_once_with("GBPUSD")
    assert signals.count_filtered.await_args.kwargs["pair_id"] == 7


async def test_list_signals_unknown_pair_filter_raises_not_found():
    ctrl, _, pairs = _controller()
    pairs.get_by_symbol.return_value = None

    with pytest.raises(ResourceNotFoundError) as exc:
        await ctrl.list_signals(offset=0, limit=20, pair_symbol="NOPE")
    assert exc.value.resource == "pair"
    assert exc.value.identifier == "NOPE"


async def test_list_signals_passes_run_filter_through():
    run_id = uuid.uuid4()
    ctrl, signals, _ = _controller()
    signals.count_filtered.return_value = 0

    await ctrl.list_signals(offset=0, limit=20, analysis_run_id=run_id)

    assert signals.count_filtered.await_args.kwargs["analysis_run_id"] == run_id


# ── get_signal ───────────────────────────────────────────────────────────────


async def test_get_signal_returns_mapped_response():
    signal = make_signal()
    ctrl, signals, _ = _controller()
    signals.get.return_value = signal

    result = await ctrl.get_signal(signal.id)

    assert isinstance(result, SignalResponse)
    assert result.id == signal.id
    assert result.pair_symbol == signal.pair.symbol
    assert result.direction == signal.direction.value


async def test_get_signal_missing_raises_not_found():
    ctrl, signals, _ = _controller()
    signals.get.return_value = None
    missing = uuid.uuid4()

    with pytest.raises(ResourceNotFoundError) as exc:
        await ctrl.get_signal(missing)
    assert exc.value.resource == "signal"
    assert exc.value.identifier == str(missing)


# ── list_latest_for_pair ─────────────────────────────────────────────────────


async def test_list_latest_for_pair_returns_mapped_signals():
    pair = make_pair(id=3, symbol="XAUUSD")
    ctrl, signals, pairs = _controller()
    pairs.get_by_symbol.return_value = pair
    signals.latest_for_pair.return_value = [make_signal(pair=pair), make_signal(pair=pair)]

    result = await ctrl.list_latest_for_pair("XAUUSD", limit=5)

    assert len(result) == 2
    assert all(r.pair_symbol == "XAUUSD" for r in result)
    signals.latest_for_pair.assert_awaited_once_with(3, limit=5)


async def test_list_latest_for_pair_unknown_symbol_raises_not_found():
    ctrl, _, pairs = _controller()
    pairs.get_by_symbol.return_value = None

    with pytest.raises(ResourceNotFoundError):
        await ctrl.list_latest_for_pair("NOPE")


# ── list_for_run ─────────────────────────────────────────────────────────────


async def test_list_for_run_maps_every_signal():
    run_id = uuid.uuid4()
    ctrl, signals, _ = _controller()
    signals.list_for_run.return_value = [make_signal(analysis_run_id=run_id)]

    result = await ctrl.list_for_run(run_id)

    assert len(result) == 1
    signals.list_for_run.assert_awaited_once_with(run_id)


# ── mapping fidelity ─────────────────────────────────────────────────────────


async def test_mapping_preserves_decimal_money_fields():
    """Money must stay ``Decimal`` end-to-end (no float coercion in mapping)."""
    from decimal import Decimal

    signal = make_signal(entry_price=Decimal("1.23456789"))
    ctrl, signals, _ = _controller()
    signals.get.return_value = signal

    result = await ctrl.get_signal(signal.id)

    assert result.entry_price == Decimal("1.23456789")
    assert isinstance(result.entry_price, Decimal)
