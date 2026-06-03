"""The outcome controller — re-checks open signals against fresh candles.

This is the measurement counterpart to :class:`AnalysisController`. Where that
one *produces* signals, this one *scores* them: each cycle it pulls the latest
candles for every active pair, runs the pure :class:`OutcomeEvaluator` over the
pair's still-open signals, and persists what price did (closed at a TP/SL,
expired, or still open with updated excursions).

It deliberately reuses the analysis controller's load-bearing disciplines:

* **The controller owns transaction boundaries.** Repositories stage; the
  evaluator is pure and IO-free; this class decides what a unit of work is.
* **No transaction is held open across network IO.** A snapshot of the active
  pairs is taken in one short transaction, the (slow) market-data fetch happens
  owning no session, and the open signals are loaded + updated + committed in a
  second short transaction.
* **Per-pair failures are isolated.** One pair's market-data outage must not stop
  the others' signals from being evaluated.
* **It manages its own sessions via the ``Database`` adapter**, because — like a
  run — an outcome sweep is a background unit of work with no HTTP request behind
  it. The thin :class:`~app.tasks.OutcomeJob` wraps this with error containment,
  exactly as ``AnalysisJob`` wraps the analysis controller.

Layering: imports services, repositories, models, config; never ``app.views`` or
``fastapi``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.config import Settings
from app.database import Database
from app.database.repository import PairRepository, SignalRepository
from app.models import Signal, SignalOutcome
from app.services import ServiceError
from app.services.market_data import Candle, MarketDataProvider
from app.services.outcome import EvaluationInput, OutcomeEvaluator

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Timezone-aware UTC now. Injected via the constructor so tests can pin it."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class _Target:
    """The minimal detached projection of an active pair the sweep needs."""

    id: int
    symbol: str


@dataclass(frozen=True, slots=True)
class OutcomeRunSummary:
    """What one sweep did — returned for callers that want it (the job ignores it)."""

    evaluated: int
    closed: int
    pairs_failed: int


class OutcomeController:
    """Evaluates and persists outcomes for every open signal, once per cycle."""

    def __init__(
        self,
        *,
        database: Database,
        market_data: MarketDataProvider,
        settings: Settings,
        evaluator: OutcomeEvaluator | None = None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._database = database
        self._market_data = market_data
        self._evaluator = evaluator or OutcomeEvaluator()
        self._clock = clock
        # Evaluate against the lowest configured timeframe — the finest-grained
        # fills, and a single fetch per pair. ``analysis_timeframes`` is the
        # ordered-unique union (low→high), so [0] is the lowest.
        self._timeframe = settings.analysis_timeframes[0]
        self._candle_count = settings.analysis_candle_count

    # ── Public API ────────────────────────────────────────────────────────

    async def run_scheduled(self) -> None:
        """Adapter matching the job's ``() -> Awaitable[None]`` contract."""
        await self.run_outcomes()

    async def run_outcomes(self) -> OutcomeRunSummary:
        """Run one full outcome sweep and return a small summary."""
        targets = await self._load_targets()
        if not targets:
            return OutcomeRunSummary(evaluated=0, closed=0, pairs_failed=0)

        candles_by_pair, fetch_failures = await self._fetch_candles(targets)
        summary = await self._evaluate_and_persist(targets, candles_by_pair, fetch_failures)

        logger.info(
            "Outcome sweep finished: evaluated=%d closed=%d pairs_failed=%d (timeframe=%s)",
            summary.evaluated,
            summary.closed,
            summary.pairs_failed,
            self._timeframe,
        )
        return summary

    # ── Phase 1: snapshot active pairs ──────────────────────────────────────

    async def _load_targets(self) -> list[_Target]:
        async with self._database.session() as session:
            pairs = PairRepository(session)
            return [_Target(id=p.id, symbol=p.symbol) for p in await pairs.list_active()]

    # ── Phase 2: fetch candles (no session, all network) ────────────────────

    async def _fetch_candles(
        self,
        targets: Sequence[_Target],
    ) -> tuple[dict[int, list[Candle]], set[int]]:
        """Fetch the latest candles per pair, isolating per-pair failures.

        Returns the candles keyed by pair id, plus the set of pair ids whose
        fetch failed (so the persist phase can count them without re-deriving).
        """
        candles_by_pair: dict[int, list[Candle]] = {}
        failures: set[int] = set()
        for target in targets:
            try:
                candles_by_pair[target.id] = list(
                    await self._market_data.fetch_candles(
                        target.symbol,
                        timeframe=self._timeframe,
                        count=self._candle_count,
                    )
                )
            except ServiceError as exc:
                logger.warning("Outcome fetch failed for %s: %s", target.symbol, exc)
                failures.add(target.id)
            except Exception:  # last-resort per-pair containment
                logger.exception("Outcome fetch raised unexpectedly for %s", target.symbol)
                failures.add(target.id)
        return candles_by_pair, failures

    # ── Phase 3: evaluate + persist (one transaction) ───────────────────────

    async def _evaluate_and_persist(
        self,
        targets: Sequence[_Target],
        candles_by_pair: dict[int, list[Candle]],
        fetch_failures: set[int],
    ) -> OutcomeRunSummary:
        now = self._clock()
        evaluated = 0
        closed = 0

        async with self._database.session() as session:
            signals_repo = SignalRepository(session)
            for target in targets:
                if target.id in fetch_failures:
                    continue
                candles = candles_by_pair.get(target.id, [])
                open_signals = await signals_repo.list_open(pair_id=target.id)
                for signal in open_signals:
                    self._apply(signals_repo, signal, candles, now=now)
                    evaluated += 1
                    if signal.outcome is not SignalOutcome.OPEN:
                        closed += 1
            await session.commit()

        return OutcomeRunSummary(
            evaluated=evaluated,
            closed=closed,
            pairs_failed=len(fetch_failures),
        )

    def _apply(
        self,
        repo: SignalRepository,
        signal: Signal,
        candles: Sequence[Candle],
        *,
        now: datetime,
    ) -> None:
        """Evaluate one open signal and stage its outcome update.

        Runs even when ``candles`` is empty (the evaluator simply finds no touch)
        so ``last_evaluated_at`` advances and excursions refresh every cycle.
        """
        result = self._evaluator.evaluate(
            EvaluationInput(
                direction=signal.direction.value,  # type: ignore[arg-type]
                entry=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profits=[
                    tp
                    for tp in (signal.take_profit, signal.take_profit_2, signal.take_profit_3)
                    if tp is not None
                ],
                generated_at=signal.generated_at,
                expires_at=signal.expires_at,
            ),
            candles,
            now=now,
        )
        repo.mark_outcome(
            signal,
            outcome=SignalOutcome(result.outcome),
            realized_r=result.realized_r,
            mfe=result.mfe,
            mae=result.mae,
            closed_at=result.closed_at,
            last_evaluated_at=now,
        )
