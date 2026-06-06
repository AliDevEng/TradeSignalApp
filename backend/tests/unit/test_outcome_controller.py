"""Unit tests for :class:`OutcomeController` — the outcome sweep orchestrator.

As with the analysis controller, the value here is *orchestration*: snapshot the
active pairs, fetch candles owning no session, then load open signals and persist
their outcomes in one transaction — isolating per-pair fetch failures. We test
that with in-memory repository fakes (swapped at the controller's import
boundary) and injected fake providers, so it stays fast and DB-free.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.controllers import outcome_controller as oc
from app.controllers.outcome_controller import OutcomeController
from app.models import SignalOutcome
from app.services import ServiceError
from app.services.market_data.base import Candle

from tests._factories import make_pair, make_signal

_NOW = datetime(2026, 6, 2, 12, 0, tzinfo=UTC)
_GEN = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


# ── In-memory persistence doubles ────────────────────────────────────────────


@dataclass
class Store:
    active_pairs: list = field(default_factory=list)
    open_signals: dict = field(default_factory=dict)  # pair_id -> list[Signal]
    commits: int = 0


class _FakeSession:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def commit(self) -> None:
        self.store.commits += 1


class _FakeDatabase:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.session_count = 0

    @asynccontextmanager
    async def session(self):
        self.session_count += 1
        yield _FakeSession(self.store)


class _FakePairRepo:
    def __init__(self, session: _FakeSession) -> None:
        self._store = session.store

    async def list_active(self):
        return self._store.active_pairs


class _FakeSignalRepo:
    def __init__(self, session: _FakeSession) -> None:
        self._store = session.store

    async def list_open(self, *, pair_id=None):
        if pair_id is None:
            return [s for signals in self._store.open_signals.values() for s in signals]
        return list(self._store.open_signals.get(pair_id, []))

    def mark_outcome(
        self, signal, *, outcome, realized_r, mfe, mae, closed_at, last_evaluated_at
    ) -> None:
        signal.outcome = outcome
        signal.realized_r = realized_r
        signal.mfe = mfe
        signal.mae = mae
        signal.closed_at = closed_at
        signal.last_evaluated_at = last_evaluated_at


class _FakeMarketData:
    def __init__(self, *, candles=None, fail_symbols=None) -> None:
        self._candles = candles or []
        self.fail_symbols = fail_symbols or set()
        self.calls: list[tuple[str, str, int]] = []

    async def fetch_candles(self, symbol, *, timeframe, count):
        self.calls.append((symbol, timeframe, count))
        if symbol in self.fail_symbols:
            raise ServiceError(f"market data unavailable for {symbol}")
        return list(self._candles)


def _candle(minute: int, *, o, h, low, c) -> Candle:
    return Candle(
        timestamp=_GEN + timedelta(minutes=minute),
        open=Decimal(str(o)),
        high=Decimal(str(h)),
        low=Decimal(str(low)),
        close=Decimal(str(c)),
    )


@pytest.fixture(autouse=True)
def _patch_repositories(monkeypatch):
    monkeypatch.setattr(oc, "PairRepository", _FakePairRepo)
    monkeypatch.setattr(oc, "SignalRepository", _FakeSignalRepo)


def _build(store: Store, *, market_data=None, event_bus=None) -> OutcomeController:
    settings = type(
        "S",
        (),
        {"analysis_timeframes": ["5m", "1h"], "analysis_candle_count": 200},
    )()
    return OutcomeController(
        database=_FakeDatabase(store),  # type: ignore[arg-type]
        market_data=market_data or _FakeMarketData(),  # type: ignore[arg-type]
        settings=settings,  # type: ignore[arg-type]
        event_bus=event_bus,
        clock=lambda: _NOW,
    )


class _CapturingBus:
    """A minimal EventPublisher that records every published event."""

    def __init__(self) -> None:
        self.events: list = []

    def publish(self, event_type, data):
        from app.services.events import Event

        event = Event(id=len(self.events) + 1, type=event_type, at=_NOW, data=data)
        self.events.append(event)
        return event


# ── Tests ─────────────────────────────────────────────────────────────────────


async def test_no_active_pairs_is_a_clean_noop():
    ctrl = _build(Store())
    summary = await ctrl.run_outcomes()
    assert summary.evaluated == 0
    assert summary.closed == 0
    assert summary.pairs_failed == 0


async def test_open_signal_closed_when_tp_hit():
    pair = make_pair(id=1, symbol="XAUUSD")
    signal = make_signal(
        pair=pair,
        pair_id=1,
        entry_price=Decimal("100"),
        stop_loss=Decimal("98"),
        take_profit=Decimal("104"),
        generated_at=_GEN,
    )
    store = Store(active_pairs=[pair], open_signals={1: [signal]})
    md = _FakeMarketData(candles=[_candle(5, o=100, h=105, low=99, c=104)])
    ctrl = _build(store, market_data=md)

    summary = await ctrl.run_outcomes()

    assert summary.evaluated == 1
    assert summary.closed == 1
    assert signal.outcome is SignalOutcome.HIT_TP1
    assert signal.realized_r == Decimal("2.0000")
    assert signal.last_evaluated_at == _NOW
    assert store.commits == 1
    # Evaluated against the lowest timeframe, one fetch for the pair.
    assert md.calls == [("XAUUSD", "5m", 200)]


async def test_open_signal_stays_open_when_untouched():
    pair = make_pair(id=1, symbol="XAUUSD")
    signal = make_signal(
        pair=pair,
        pair_id=1,
        entry_price=Decimal("100"),
        stop_loss=Decimal("98"),
        take_profit=Decimal("110"),
        generated_at=_GEN,
    )
    store = Store(active_pairs=[pair], open_signals={1: [signal]})
    md = _FakeMarketData(candles=[_candle(5, o=100, h=103, low=99.5, c=101)])
    ctrl = _build(store, market_data=md)

    summary = await ctrl.run_outcomes()

    assert summary.evaluated == 1
    assert summary.closed == 0
    assert signal.outcome is SignalOutcome.OPEN
    # Excursions still refresh while open.
    assert signal.mfe == Decimal("1.5000")  # (103-100)/2
    assert signal.last_evaluated_at == _NOW


async def test_fetch_failure_isolates_pair_and_counts_it():
    good = make_pair(id=1, symbol="XAUUSD")
    bad = make_pair(id=2, symbol="EURUSD")
    good_signal = make_signal(
        pair=good,
        pair_id=1,
        entry_price=Decimal("100"),
        stop_loss=Decimal("98"),
        take_profit=Decimal("104"),
        generated_at=_GEN,
    )
    bad_signal = make_signal(pair=bad, pair_id=2, generated_at=_GEN)
    store = Store(
        active_pairs=[good, bad],
        open_signals={1: [good_signal], 2: [bad_signal]},
    )
    md = _FakeMarketData(
        candles=[_candle(5, o=100, h=105, low=99, c=104)],
        fail_symbols={"EURUSD"},
    )
    ctrl = _build(store, market_data=md)

    summary = await ctrl.run_outcomes()

    assert summary.pairs_failed == 1
    assert summary.evaluated == 1  # only the good pair's signal
    assert summary.closed == 1
    assert good_signal.outcome is SignalOutcome.HIT_TP1
    assert bad_signal.outcome is SignalOutcome.OPEN  # untouched by the failed pair


async def test_publishes_signal_closed_only_for_newly_closed():
    pair = make_pair(id=1, symbol="XAUUSD")
    closing = make_signal(
        pair=pair,
        pair_id=1,
        entry_price=Decimal("100"),
        stop_loss=Decimal("98"),
        take_profit=Decimal("104"),
        generated_at=_GEN,
    )
    staying_open = make_signal(
        pair=pair,
        pair_id=1,
        entry_price=Decimal("100"),
        stop_loss=Decimal("98"),
        take_profit=Decimal("130"),
        generated_at=_GEN,
    )
    store = Store(active_pairs=[pair], open_signals={1: [closing, staying_open]})
    md = _FakeMarketData(candles=[_candle(5, o=100, h=105, low=99, c=104)])
    bus = _CapturingBus()
    ctrl = _build(store, market_data=md, event_bus=bus)

    await ctrl.run_outcomes()

    closed_events = [e for e in bus.events if e.type == "signal.closed"]
    assert len(closed_events) == 1  # only the one that actually closed
    payload = closed_events[0].data
    assert payload["pair"] == "XAUUSD"
    assert payload["outcome"] == "hit_tp1"
    assert payload["signal_id"] == str(closing.id)
    assert payload["realized_r"] == "2.0000"


async def test_no_session_held_across_fetch():
    # Two short transactions: snapshot pairs, then persist — fetch in between.
    pair = make_pair(id=1, symbol="XAUUSD")
    store = Store(active_pairs=[pair], open_signals={1: []})
    ctrl = _build(store)
    await ctrl.run_outcomes()
    assert ctrl._database.session_count == 2  # type: ignore[attr-defined]
