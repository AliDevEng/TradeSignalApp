"""Unit tests for :class:`AnalysisController` — the pipeline orchestrator.

The controller's value is its *orchestration*: split the run into three short
transactions, isolate per-pair failures, and resolve a terminal status from the
mix of outcomes. We test that without a live Postgres by replacing the three
repository classes (at the module boundary they are imported into) with
in-memory fakes backed by a shared ``Store``, and by injecting fake providers
and a fake ``Database`` whose ``session()`` is a no-op context manager.

This keeps the test honest about the contract that matters — *what gets
persisted, with which status, when a pair fails* — while staying fast and
DB-free. The "the SQL actually round-trips" guarantee lives in the repository
SQL tests and the integration suite.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from app.controllers import analysis_controller as ac
from app.controllers.analysis_controller import AnalysisController
from app.models import AnalysisRunStatus, AnalysisRunTrigger, SignalType
from app.services import ServiceError
from app.services.ai import DualSignalDraft, SignalDraft

from tests._factories import make_pair

_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


# ── In-memory persistence doubles ────────────────────────────────────────────


@dataclass
class Store:
    """Shared in-memory state the fake repositories read and mutate."""

    active_pairs: list = field(default_factory=list)
    runs: dict = field(default_factory=dict)
    signals: list = field(default_factory=list)
    # Per-pair currently-open signals fed back into the AI (pair_id -> {style: signal}).
    current_by_pair: dict = field(default_factory=dict)
    commits: int = 0
    fail_add_all: bool = False  # simulate a persistence blip during finalisation


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


class _FakeRunRepo:
    def __init__(self, session: _FakeSession) -> None:
        self._store = session.store

    def add(self, run):
        self._pending = run

    async def flush(self):
        run = self._pending
        if run.id is None:
            run.id = uuid.uuid4()
        self._store.runs[run.id] = run

    async def get(self, run_id):
        return self._store.runs.get(run_id)


class _FakeSignalRepo:
    def __init__(self, session: _FakeSession) -> None:
        self._store = session.store

    def add_all(self, signals):
        if self._store.fail_add_all:
            raise RuntimeError("DB blip while persisting signals")
        self._store.signals.extend(signals)

    async def current_for_pair(self, pair_id):
        seeded = self._store.current_by_pair.get(pair_id, {})
        return {style: seeded.get(style) for style in SignalType}


# ── Fake services ────────────────────────────────────────────────────────────


class _FakeSnapshot:
    def to_storage_dict(self):
        return {"rsi": 30.0}


class _FakeCalculator:
    def compute(self, candles):
        return _FakeSnapshot()


class _FakeMarketData:
    def __init__(self, fail_symbols: set[str] | None = None) -> None:
        self.fail_symbols = fail_symbols or set()

    async def fetch_candles(self, symbol, *, timeframe, count):
        if symbol in self.fail_symbols:
            raise ServiceError(f"market data unavailable for {symbol}")
        return []


class _FakeAI:
    provider_name = "groq"
    model = "llama-3.3-70b-versatile"

    def __init__(
        self,
        *,
        dual: DualSignalDraft | None = None,
        per_symbol: dict | None = None,
        fail_symbols: set[str] | None = None,
        crash_symbols: set[str] | None = None,
    ) -> None:
        self._dual = dual
        self._per_symbol = per_symbol or {}
        self._fail = fail_symbols or set()
        self._crash = crash_symbols or set()
        # Records every context analyse() was called with, so tests can assert
        # the keep/adjust prior signals were forwarded.
        self.contexts: list = []

    async def analyze(self, context):
        self.contexts.append(context)
        sym = context.symbol
        if sym in self._fail:
            raise ServiceError(f"AI failed for {sym}")
        if sym in self._crash:
            raise ValueError(f"unexpected boom for {sym}")
        if sym in self._per_symbol:
            return self._per_symbol[sym]
        return self._dual or _dual_draft()


def _draft(direction="buy", entry="1.10000000", tps=("1.12000000", "1.15000000"), confidence=0.72):
    return SignalDraft(
        direction=direction,
        confidence=confidence,
        entry=Decimal(entry),
        stop_loss=Decimal("1.09000000"),
        take_profits=[Decimal(t) for t in tps],
        rationale="bullish",
    )


def _dual_draft(scalp: SignalDraft | None = None, swing: SignalDraft | None = None):
    return DualSignalDraft(scalp=scalp or _draft(), swing=swing or _draft())


def _by_style(store: Store) -> dict:
    """Index the persisted signals by their style for per-style assertions."""
    return {s.signal_type: s for s in store.signals}


# ── Fixtures / builder ───────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _patch_repositories(monkeypatch):
    """Swap the repo classes the controller constructs for the in-memory fakes."""
    monkeypatch.setattr(ac, "PairRepository", _FakePairRepo)
    monkeypatch.setattr(ac, "AnalysisRunRepository", _FakeRunRepo)
    monkeypatch.setattr(ac, "SignalRepository", _FakeSignalRepo)


def _build(
    store: Store,
    *,
    market_data=None,
    ai=None,
    timeframes=None,
    scalp=None,
    swing=None,
) -> AnalysisController:
    # ``timeframes`` is the union fetched per run; the per-style frames default
    # to that whole set unless overridden, so scalp frames on its lowest member
    # and swing on its highest.
    tfs = timeframes or ["1h"]
    settings = SimpleNamespace(
        analysis_timeframe="1h",
        analysis_timeframes=tfs,
        scalp_timeframes=scalp or tfs,
        swing_timeframes=swing or tfs,
        analysis_candle_count=200,
        signal_scalp_ttl_minutes=240,
        signal_swing_ttl_minutes=4320,
    )
    return AnalysisController(
        database=_FakeDatabase(store),  # type: ignore[arg-type]
        market_data=market_data or _FakeMarketData(),  # type: ignore[arg-type]
        ai_provider=ai or _FakeAI(),  # type: ignore[arg-type]
        settings=settings,  # type: ignore[arg-type]
        calculator=_FakeCalculator(),  # type: ignore[arg-type]
        clock=lambda: _NOW,
    )


# ── Happy path ───────────────────────────────────────────────────────────────


async def test_all_pairs_succeed_marks_success_and_persists_two_signals_each():
    store = Store(active_pairs=[make_pair(id=1, symbol="EURUSD"), make_pair(id=2, symbol="GBPUSD")])
    ctrl = _build(store)

    run = await ctrl.run_analysis()

    assert run.status is AnalysisRunStatus.SUCCESS
    assert run.pairs_processed == 2
    assert run.pairs_failed == 0
    assert run.error_message is None
    # Two signals (scalp + swing) per processed pair.
    assert len(store.signals) == 4
    # Three-phase: exactly two transactions (open, finalise) — none across IO.
    assert ctrl._database.session_count == 2  # type: ignore[attr-defined]


async def test_success_emits_one_scalp_and_one_swing_per_pair():
    """Every successful pair yields exactly one scalp and one swing signal."""
    store = Store(active_pairs=[make_pair(id=1, symbol="EURUSD")])
    ctrl = _build(store)

    run = await ctrl.run_analysis()

    assert run.status is AnalysisRunStatus.SUCCESS
    styles = sorted(s.signal_type for s in store.signals)
    assert styles == [SignalType.SCALP, SignalType.SWING]
    # Each carries a style-specific expiry (scalp ages out before swing).
    by_style = _by_style(store)
    assert by_style[SignalType.SCALP].expires_at < by_style[SignalType.SWING].expires_at


async def test_no_active_pairs_is_a_clean_success_noop():
    store = Store(active_pairs=[])
    ctrl = _build(store)

    run = await ctrl.run_analysis()

    assert run.status is AnalysisRunStatus.SUCCESS
    assert run.pairs_processed == 0
    assert store.signals == []


# ── Partial / failure handling ───────────────────────────────────────────────


async def test_one_failed_pair_yields_partial_status():
    store = Store(active_pairs=[make_pair(id=1, symbol="EURUSD"), make_pair(id=2, symbol="GBPUSD")])
    ctrl = _build(store, ai=_FakeAI(fail_symbols={"GBPUSD"}))

    run = await ctrl.run_analysis()

    assert run.status is AnalysisRunStatus.PARTIAL
    assert run.pairs_processed == 1
    assert run.pairs_failed == 1
    # The one surviving pair still produces its scalp + swing.
    assert len(store.signals) == 2
    assert run.error_message is not None
    assert "GBPUSD" in run.error_message


async def test_all_pairs_failed_yields_failed_status():
    store = Store(active_pairs=[make_pair(id=1, symbol="EURUSD"), make_pair(id=2, symbol="GBPUSD")])
    ctrl = _build(store, ai=_FakeAI(fail_symbols={"EURUSD", "GBPUSD"}))

    run = await ctrl.run_analysis()

    assert run.status is AnalysisRunStatus.FAILED
    assert run.pairs_processed == 0
    assert run.pairs_failed == 2
    assert store.signals == []


async def test_market_data_failure_isolates_the_pair():
    store = Store(active_pairs=[make_pair(id=1, symbol="EURUSD"), make_pair(id=2, symbol="GBPUSD")])
    ctrl = _build(store, market_data=_FakeMarketData(fail_symbols={"EURUSD"}))

    run = await ctrl.run_analysis()

    assert run.status is AnalysisRunStatus.PARTIAL
    assert run.pairs_failed == 1


async def test_unexpected_exception_is_contained_as_a_pair_failure():
    """A non-ServiceError surprise must not discard the other pairs' signals."""
    store = Store(active_pairs=[make_pair(id=1, symbol="EURUSD"), make_pair(id=2, symbol="GBPUSD")])
    ctrl = _build(store, ai=_FakeAI(crash_symbols={"EURUSD"}))

    run = await ctrl.run_analysis()

    assert run.status is AnalysisRunStatus.PARTIAL
    assert run.pairs_failed == 1
    assert len(store.signals) == 2


# ── Keep-or-adjust feedback ──────────────────────────────────────────────────


async def test_prior_signals_are_forwarded_to_the_ai_context():
    """The pair's currently-open scalp/swing are fed back so the AI can adjust."""
    pair = make_pair(id=1, symbol="EURUSD")
    prior_scalp = SimpleNamespace(
        direction=SimpleNamespace(value="sell"),
        confidence=0.5,
        entry_price=Decimal("1.20000000"),
        stop_loss=Decimal("1.21000000"),
        take_profit=Decimal("1.18000000"),
        take_profit_2=None,
        take_profit_3=None,
        generated_at=_NOW,
    )
    store = Store(
        active_pairs=[pair],
        current_by_pair={1: {SignalType.SCALP: prior_scalp, SignalType.SWING: None}},
    )
    ai = _FakeAI()
    ctrl = _build(store, ai=ai)

    await ctrl.run_analysis()

    (context,) = ai.contexts
    assert context.current_scalp is not None
    assert context.current_scalp.direction == "sell"
    assert context.current_scalp.entry == Decimal("1.20000000")
    assert context.current_swing is None


# ── Trigger tagging ──────────────────────────────────────────────────────────


async def test_run_manual_tags_the_run_as_manual():
    store = Store(active_pairs=[])
    ctrl = _build(store)

    run = await ctrl.run_manual()

    assert run.trigger is AnalysisRunTrigger.MANUAL


async def test_run_scheduled_tags_the_run_as_scheduler():
    store = Store(active_pairs=[])
    ctrl = _build(store)

    # run_scheduled returns None (adapter for the job); inspect the stored run.
    await ctrl.run_scheduled()

    (run,) = store.runs.values()
    assert run.trigger is AnalysisRunTrigger.SCHEDULER


# ── Persistence failure path ─────────────────────────────────────────────────


async def test_finalisation_failure_marks_run_failed_and_reraises():
    store = Store(active_pairs=[make_pair(id=1, symbol="EURUSD")], fail_add_all=True)
    ctrl = _build(store)

    with pytest.raises(RuntimeError, match="DB blip"):
        await ctrl.run_analysis()

    # Best-effort recovery: the stuck RUNNING row is stamped FAILED, not left
    # dangling — in its own fresh session after the original failed.
    (run,) = store.runs.values()
    assert run.status is AnalysisRunStatus.FAILED
    assert run.error_message == "result persistence failed"


# ── Signal mapping detail ────────────────────────────────────────────────────


async def test_full_take_profit_ladder_is_persisted():
    """All emitted TP levels map positionally onto take_profit/_2/_3 (per style)."""
    store = Store(active_pairs=[make_pair(id=1, symbol="EURUSD")])
    swing = _draft(tps=("1.12000000", "1.15000000", "1.18000000"))
    ctrl = _build(store, ai=_FakeAI(dual=_dual_draft(swing=swing)))

    await ctrl.run_analysis()

    signal = _by_style(store)[SignalType.SWING]
    assert signal.take_profit == Decimal("1.12000000")
    assert signal.take_profit_2 == Decimal("1.15000000")
    assert signal.take_profit_3 == Decimal("1.18000000")


async def test_missing_take_profit_levels_are_null():
    """A draft with fewer than three targets leaves the higher levels NULL."""
    store = Store(active_pairs=[make_pair(id=1, symbol="EURUSD")])
    scalp = _draft(tps=("1.12000000",))
    ctrl = _build(store, ai=_FakeAI(dual=_dual_draft(scalp=scalp)))

    await ctrl.run_analysis()

    signal = _by_style(store)[SignalType.SCALP]
    assert signal.take_profit == Decimal("1.12000000")
    assert signal.take_profit_2 is None
    assert signal.take_profit_3 is None


async def test_signals_carry_provenance_and_style_specific_timeframe():
    store = Store(active_pairs=[make_pair(id=5, symbol="XAUUSD")])
    # Distinct low/high timeframes so scalp frames on 5m and swing on 1d.
    ctrl = _build(store, timeframes=["5m", "1h", "1d"])

    await ctrl.run_analysis()

    by_style = _by_style(store)
    for signal in store.signals:
        assert signal.pair_id == 5
        assert signal.ai_provider == "groq"
        # Indicators are keyed by timeframe (one entry per analysed timeframe).
        assert signal.indicators_snapshot == {
            "5m": {"rsi": 30.0},
            "1h": {"rsi": 30.0},
            "1d": {"rsi": 30.0},
        }
    assert by_style[SignalType.SCALP].timeframe == "5m"
    assert by_style[SignalType.SWING].timeframe == "1d"


# ── Pure helpers ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("total", "processed", "expected"),
    [
        (0, 0, AnalysisRunStatus.SUCCESS),
        (3, 3, AnalysisRunStatus.SUCCESS),
        (3, 1, AnalysisRunStatus.PARTIAL),
        (3, 0, AnalysisRunStatus.FAILED),
    ],
)
def test_resolve_status_maps_outcome_mix(total, processed, expected):
    assert AnalysisController._resolve_status(total=total, processed=processed) is expected


def test_summarise_errors_returns_none_when_no_failures():
    outcomes = [ac._PairOutcome(target=ac._PairTarget(id=1, symbol="EURUSD"))]
    assert AnalysisController._summarise_errors(outcomes) is None


def test_summarise_errors_is_truncated_when_oversized():
    outcomes = [
        ac._PairOutcome(target=ac._PairTarget(id=i, symbol=f"SYM{i}"), error="x" * 500)
        for i in range(10)
    ]
    summary = AnalysisController._summarise_errors(outcomes)
    assert summary is not None
    assert len(summary) <= ac._MAX_ERROR_SUMMARY
    assert summary.endswith("…")
