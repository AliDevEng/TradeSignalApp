"""The analysis controller — orchestrates one full pipeline run.

This is the *business* half of the analysis feature. Iteration 3 built the
ingredients (market data, indicators, AI) and the scheduler; this controller is
the conductor that strings them together and persists the result:

    for each active pair:
        fetch candles → compute indicators → ask the AI → draft a signal
    record the run ledger + the signals it produced, atomically

It is the piece the README's Iteration-3 notes describe as "the orchestration
that strings them together (and persists signals)" and the placeholder
``pipeline_not_configured`` was always meant to be replaced by.

Design decisions worth stating up front, because they are load-bearing:

* **The controller owns transaction boundaries; the services and repositories
  do not.** Repositories stage work on a session and never commit; the AI and
  market-data services never touch the database at all. That one-way contract
  is what lets this class decide what a unit of work is.

* **No transaction is ever held open across network IO.** A single run fans out
  across several pairs, each costing a market-data call plus an AI call (up to
  tens of seconds apiece). Holding a database transaction — and the pooled
  connection behind it — open for minutes while we wait on third parties would
  be a textbook way to exhaust the pool. So the run is split into three short
  database transactions (open the run → … network IO happens here, with no
  session … → persist signals + finalise the run) with the slow, side-effecting
  work in between owning no database resources.

* **Per-pair failures are isolated.** One pair's provider timeout or malformed
  response must not deprive the other pairs of their signals. Each pair is
  analysed defensively; an expected service failure marks that pair failed and
  the run continues. The run's terminal status (``SUCCESS`` / ``PARTIAL`` /
  ``FAILED``) then reflects the mix of outcomes, which is exactly the
  distinction the ``AnalysisRun`` model carved out ``PARTIAL`` to express.

* **The controller manages its own sessions via the ``Database`` adapter rather
  than borrowing a request-scoped one.** A run is a minutes-long background
  unit of work with no HTTP request behind it (the scheduler) — and even when a
  future endpoint triggers one manually, it will dispatch it as a background
  task rather than block a request for minutes. Taking ``Database`` (not an
  ``AsyncSession``) is what makes the controller equally usable from both.

Layering: this module may import services, repositories, models, schemas and
config; it must not import ``app.views`` or ``fastapi`` (see the table in
``backend/README.md``). It deliberately doesn't.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final

from app.config import Settings
from app.database import Database
from app.database.repository import (
    AnalysisRunRepository,
    PairRepository,
    SignalRepository,
)
from app.models import (
    AnalysisRun,
    AnalysisRunStatus,
    AnalysisRunTrigger,
    Signal,
    SignalDirection,
)
from app.services import ServiceError
from app.services.ai import AIProvider, AnalysisContext, SignalDraft
from app.services.indicators import IndicatorCalculator, IndicatorSnapshot
from app.services.market_data import MarketDataProvider

logger = logging.getLogger(__name__)

# Upper bound on the run's ``error_message`` summary. The column is unbounded
# ``Text``, but a run over many pairs could otherwise accumulate a wall of
# stack-trace-adjacent text; a bounded summary keeps the ledger row scannable.
_MAX_ERROR_SUMMARY: Final[int] = 1000


def _utcnow() -> datetime:
    """Timezone-aware UTC now. Injected via the constructor so tests can pin it."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class _PairTarget:
    """The minimal, detached projection of a ``Pair`` the run needs.

    Only the primary key and symbol are carried forward out of the opening
    transaction, so nothing downstream touches a detached ORM instance (which
    would risk an implicit lazy-load against a closed session).
    """

    id: int
    symbol: str


@dataclass(frozen=True, slots=True)
class _PairOutcome:
    """Result of analysing a single pair — success (draft + snapshot) or failure."""

    target: _PairTarget
    draft: SignalDraft | None = None
    snapshot: IndicatorSnapshot | None = None
    error: str | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None

    @property
    def emits_signal(self) -> bool:
        """A signal row is written only for an actionable, directional draft.

        ``neutral`` drafts (and, defensively, any directional draft the AI left
        without an entry — though :class:`BaseAIProvider` already rejects those)
        are *not* persisted: the ``signals`` table models actionable trades and
        enforces ``entry_price NOT NULL``. A "no trade this cycle" outcome is a
        successful analysis that simply produces no signal, not a failure.
        """
        return (
            self.draft is not None
            and self.draft.direction in ("buy", "sell")
            and self.draft.entry is not None
        )


class AnalysisController:
    """Runs the end-to-end analysis pipeline and persists its outcome.

    Constructed once with its long-lived collaborators (all of which outlive any
    single request) and reused for every run. Stateless between runs: each call
    to :meth:`run_analysis` is a self-contained unit of work.
    """

    def __init__(
        self,
        *,
        database: Database,
        market_data: MarketDataProvider,
        ai_provider: AIProvider,
        settings: Settings,
        calculator: IndicatorCalculator | None = None,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._database = database
        self._market_data = market_data
        self._ai = ai_provider
        # The calculator is pure and configuration-free; default-construct it but
        # allow injection so tests can substitute a deterministic stub.
        self._calculator = calculator or IndicatorCalculator()
        self._clock = clock

        # Snapshot the analysis parameters once. They are recorded on the run
        # ledger for traceability, so a later config change can't retroactively
        # rewrite what a historical run actually executed.
        self._timeframe = settings.analysis_timeframe
        self._candle_count = settings.analysis_candle_count

    # ── Public API ───────────────────────────────────────────────────────────

    async def run_scheduled(self) -> None:
        """Adapter matching ``tasks.AnalysisPipeline`` (``() -> Awaitable[None]``).

        This is the callable the scheduled :class:`~app.tasks.AnalysisJob` drives.
        It discards the return value because the job only needs the side effects
        (persisted run + signals); the structured result is for callers that
        trigger a run directly (e.g. a manual-trigger endpoint).
        """
        await self.run_analysis(trigger=AnalysisRunTrigger.SCHEDULER)

    async def run_manual(self) -> AnalysisRun:
        """Run the pipeline once, tagged as operator-triggered.

        Exists so the manual-trigger endpoint can dispatch a run without
        importing the ORM trigger enum (keeping the view free of model imports).
        Returns the persisted ledger row for callers that want it; the endpoint
        dispatches this as a background task and ignores the return.
        """
        return await self.run_analysis(trigger=AnalysisRunTrigger.MANUAL)

    async def run_analysis(
        self,
        *,
        trigger: AnalysisRunTrigger = AnalysisRunTrigger.SCHEDULER,
    ) -> AnalysisRun:
        """Execute one full pipeline cycle and return the persisted run ledger.

        The returned :class:`AnalysisRun` is detached (its session is closed) but
        safe to read — the session factory uses ``expire_on_commit=False`` — so a
        caller can map it to a response schema without further IO.

        Errors that prevent the run from even starting (e.g. the database is
        unreachable when opening the run) propagate to the caller: there is no
        ledger row to mark failed, and the scheduled job's wrapper already logs
        and contains such failures. Per-pair failures, by contrast, are isolated
        and reflected in the run's status rather than raised.
        """
        started_at = self._clock()
        run_id, targets = await self._open_run(trigger, started_at)
        logger.info(
            "Analysis run %s started (trigger=%s, pairs=%d, timeframe=%s)",
            run_id,
            trigger.value,
            len(targets),
            self._timeframe,
        )

        # The slow part: network IO across providers, owning no DB connection.
        outcomes = [await self._analyze_pair(target) for target in targets]

        try:
            run = await self._finalize_run(run_id, outcomes)
        except Exception:
            # The compute work succeeded but persistence failed (a DB blip on the
            # final commit). Best-effort: stamp the ledger row FAILED in a fresh
            # session so it isn't left stuck in RUNNING, then re-raise — losing
            # the signals is already an incident the caller must see.
            logger.exception("Analysis run %s failed to persist results", run_id)
            await self._try_mark_failed(run_id, "result persistence failed")
            raise

        signals_generated = sum(1 for o in outcomes if o.emits_signal)
        logger.info(
            "Analysis run %s finished: status=%s processed=%d failed=%d signals=%d",
            run.id,
            run.status.value,
            run.pairs_processed,
            run.pairs_failed,
            signals_generated,
        )
        return run

    # ── Phase 1: open the run ledger ─────────────────────────────────────────

    async def _open_run(
        self,
        trigger: AnalysisRunTrigger,
        started_at: datetime,
    ) -> tuple[uuid.UUID, list[_PairTarget]]:
        """Snapshot the active pairs and persist a ``RUNNING`` ledger row.

        Committed in its own short transaction so an in-flight run is immediately
        observable, and so a process crash mid-cycle leaves a detectable
        ``RUNNING`` row rather than no trace at all. Returns the run id and the
        detached pair targets the cycle will iterate.
        """
        async with self._database.session() as session:
            pairs = PairRepository(session)
            runs = AnalysisRunRepository(session)

            targets = [_PairTarget(id=p.id, symbol=p.symbol) for p in await pairs.list_active()]

            run = AnalysisRun(
                status=AnalysisRunStatus.RUNNING,
                trigger=trigger,
                timeframe=self._timeframe,
                candle_count=self._candle_count,
                started_at=started_at,
                ai_provider=self._ai.provider_name,
                ai_model=self._ai.model,
            )
            runs.add(run)
            await runs.flush()  # populate the client-side default id before commit
            run_id = run.id
            await session.commit()

        return run_id, targets

    # ── Phase 2: analyse one pair (no database, all network) ─────────────────

    async def _analyze_pair(self, target: _PairTarget) -> _PairOutcome:
        """Fetch → compute → reason for a single pair, isolating its failures.

        Returns an outcome rather than raising: an expected service failure
        (provider down, insufficient candles, unparseable AI reply — every one a
        :class:`ServiceError`) fails just this pair. An *unexpected* exception is
        also contained here (one pair's surprise must not discard the other
        pairs' good signals) but logged with a traceback so genuine bugs stay
        loud rather than masquerading as a routine partial failure.
        """
        try:
            candles = await self._market_data.fetch_candles(
                target.symbol,
                timeframe=self._timeframe,
                count=self._candle_count,
            )
            snapshot = self._calculator.compute(candles)
            context = AnalysisContext(
                symbol=target.symbol,
                timeframe=self._timeframe,
                indicators=snapshot,
                recent_candles=list(candles),
            )
            draft = await self._ai.analyze(context)
        except ServiceError as exc:
            logger.warning("Pair %s failed analysis: %s", target.symbol, exc)
            return _PairOutcome(target=target, error=f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # last-resort per-pair containment
            logger.exception("Pair %s raised an unexpected error during analysis", target.symbol)
            return _PairOutcome(target=target, error=f"{type(exc).__name__}: {exc}")

        return _PairOutcome(target=target, draft=draft, snapshot=snapshot)

    # ── Phase 3: persist signals + finalise the ledger (one transaction) ─────

    async def _finalize_run(
        self,
        run_id: uuid.UUID,
        outcomes: Sequence[_PairOutcome],
    ) -> AnalysisRun:
        """Atomically write the run's signals and stamp its terminal status.

        Signals and the ledger update share one transaction so a run's reported
        counts can never disagree with the signal rows actually committed.
        """
        generated_at = self._clock()
        signals = [
            self._build_signal(outcome, run_id=run_id, generated_at=generated_at)
            for outcome in outcomes
            if outcome.emits_signal
        ]

        processed = sum(1 for o in outcomes if not o.failed)
        failed = sum(1 for o in outcomes if o.failed)

        async with self._database.session() as session:
            runs = AnalysisRunRepository(session)
            signal_repo = SignalRepository(session)

            run = await runs.get(run_id)
            if run is None:  # pragma: no cover - the row was committed in phase 1
                raise RuntimeError(f"Analysis run {run_id} vanished before finalisation")

            if signals:
                signal_repo.add_all(signals)

            run.status = self._resolve_status(total=len(outcomes), processed=processed)
            run.pairs_processed = processed
            run.pairs_failed = failed
            run.finished_at = self._clock()
            run.error_message = self._summarise_errors(outcomes)

            await session.commit()

        return run

    def _build_signal(
        self,
        outcome: _PairOutcome,
        *,
        run_id: uuid.UUID,
        generated_at: datetime,
    ) -> Signal:
        """Map a directional :class:`SignalDraft` onto the ``Signal`` ORM model.

        ``emits_signal`` has already guaranteed a directional draft with an entry,
        so the asserts below are invariants, not user-facing validation.

        Note on take-profits: a ``SignalDraft`` carries up to three ordered
        levels (TP1..TP3). The ``signals`` schema stores the full ladder across
        ``take_profit`` (TP1), ``take_profit_2`` (TP2) and ``take_profit_3``
        (TP3); we map each level positionally and leave the columns NULL for any
        level the draft did not emit.
        """
        draft = outcome.draft
        snapshot = outcome.snapshot
        assert draft is not None and draft.entry is not None  # invariant from emits_signal
        assert snapshot is not None  # set on every successful outcome

        tps = draft.take_profits
        take_profit: Decimal | None = tps[0] if len(tps) > 0 else None
        take_profit_2: Decimal | None = tps[1] if len(tps) > 1 else None
        take_profit_3: Decimal | None = tps[2] if len(tps) > 2 else None

        return Signal(
            pair_id=outcome.target.id,
            analysis_run_id=run_id,
            direction=SignalDirection(draft.direction),
            confidence=draft.confidence,
            entry_price=draft.entry,
            stop_loss=draft.stop_loss,
            take_profit=take_profit,
            take_profit_2=take_profit_2,
            take_profit_3=take_profit_3,
            timeframe=self._timeframe,
            rationale=draft.rationale,
            indicators_snapshot=snapshot.to_storage_dict(),
            generated_at=generated_at,
            # No expiry policy is defined yet; leaving this NULL means the
            # retention sweep (``SignalRepository.delete_expired``) simply skips
            # these rows rather than us inventing a lifetime here.
            expires_at=None,
            ai_provider=self._ai.provider_name,
            ai_model=self._ai.model,
        )

    @staticmethod
    def _resolve_status(*, total: int, processed: int) -> AnalysisRunStatus:
        """Map (total, processed) onto a terminal run status.

        * nothing to do (no active pairs)          → ``SUCCESS`` (a clean no-op)
        * every pair analysed                       → ``SUCCESS``
        * some analysed, some failed                → ``PARTIAL``
        * pairs existed but none analysed           → ``FAILED``
        """
        if total == 0 or processed == total:
            return AnalysisRunStatus.SUCCESS
        if processed == 0:
            return AnalysisRunStatus.FAILED
        return AnalysisRunStatus.PARTIAL

    @staticmethod
    def _summarise_errors(outcomes: Sequence[_PairOutcome]) -> str | None:
        """Compact, scannable summary of per-pair failures for the ledger row."""
        failures = [f"{o.target.symbol}: {o.error}" for o in outcomes if o.failed]
        if not failures:
            return None
        summary = "; ".join(failures)
        if len(summary) > _MAX_ERROR_SUMMARY:
            summary = summary[: _MAX_ERROR_SUMMARY - 1] + "…"
        return summary

    async def _try_mark_failed(self, run_id: uuid.UUID, message: str) -> None:
        """Best-effort transition of a stuck run to ``FAILED``; never raises.

        Invoked only when finalisation itself failed, so the database may well
        still be unhealthy — this must not mask the original error with a
        secondary one.
        """
        try:
            async with self._database.session() as session:
                runs = AnalysisRunRepository(session)
                run = await runs.get(run_id)
                if run is None:
                    return
                run.status = AnalysisRunStatus.FAILED
                run.finished_at = self._clock()
                run.error_message = message
                await session.commit()
        except Exception:  # a secondary failure must not mask the original error
            logger.exception("Could not mark analysis run %s as failed", run_id)
