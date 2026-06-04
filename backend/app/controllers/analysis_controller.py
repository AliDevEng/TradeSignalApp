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
from datetime import UTC, datetime, timedelta
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
    SignalType,
)
from app.services import ServiceError
from app.services.ai import (
    AIProvider,
    AnalysisContext,
    DualSignalDraft,
    PriorPerformance,
    PriorSignal,
    SignalDraft,
    TimeframeView,
    TokenUsage,
    estimate_cost_usd,
)
from app.services.indicators import IndicatorCalculator
from app.services.market_data import MarketDataProvider

logger = logging.getLogger(__name__)

# Upper bound on the run's ``error_message`` summary. The column is unbounded
# ``Text``, but a run over many pairs could otherwise accumulate a wall of
# stack-trace-adjacent text; a bounded summary keeps the ledger row scannable.
_MAX_ERROR_SUMMARY: Final[int] = 1000

# How many recent closed signals (per style) feed the model's "your track record"
# block. Bounded so the feedback reflects *recent* behaviour, not all of history.
_FEEDBACK_LOOKBACK: Final[int] = 20

# R figures in the feedback summary share the evaluator's 4-decimal scale.
_R_QUANTUM: Final[Decimal] = Decimal("0.0001")

# Relative magnitude of each timeframe, used to pick the lowest (scalp) and
# highest (swing) configured timeframe to frame each style's signal on.
_TIMEFRAME_MINUTES: Final[dict[str, int]] = {
    "1m": 1,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}


def _utcnow() -> datetime:
    """Timezone-aware UTC now. Injected via the constructor so tests can pin it."""
    return datetime.now(UTC)


def _to_prior(signal: Signal | None) -> PriorSignal | None:
    """Project a persisted ``Signal`` into the compact :class:`PriorSignal` the
    AI is shown, or ``None`` when the pair has no open signal of that style.

    Reads only already-loaded scalar columns, so it is safe against a row whose
    session has since closed (no lazy-load risk).
    """
    if signal is None:
        return None
    take_profits = tuple(
        tp
        for tp in (signal.take_profit, signal.take_profit_2, signal.take_profit_3)
        if tp is not None
    )
    return PriorSignal(
        direction=signal.direction.value,
        confidence=signal.confidence,
        entry=signal.entry_price,
        stop_loss=signal.stop_loss,
        take_profits=take_profits,
        generated_at=signal.generated_at.isoformat(),
    )


def _performance_of(signals: Sequence[Signal]) -> PriorPerformance | None:
    """Summarise a style's recent closed signals into the feedback the AI sees.

    Pure projection over already-loaded scalar columns (``confidence``,
    ``realized_r``) — no lazy-load risk. ``confidence_bias`` is the mean stated
    confidence minus the realised win-rate (positive ⇒ over-confident). Returns
    ``None`` when there is no closed history, so the prompt omits the block.
    """
    if not signals:
        return None
    closed = len(signals)
    wins = 0
    total_r = Decimal(0)
    total_confidence = 0.0
    for signal in signals:
        total_confidence += signal.confidence
        realized = signal.realized_r
        if realized is not None:
            total_r += realized
            if realized > 0:
                wins += 1
    win_rate = wins / closed
    return PriorPerformance(
        closed=closed,
        win_rate=win_rate,
        avg_r=(total_r / closed).quantize(_R_QUANTUM),
        confidence_bias=(total_confidence / closed) - win_rate,
    )


@dataclass(frozen=True, slots=True)
class _PairTarget:
    """The minimal, detached projection of a ``Pair`` the run needs.

    Only the primary key, symbol, and the pair's currently-open signals (one per
    style, fed back so the model can keep or adjust them) are carried forward out
    of the opening transaction, so nothing downstream touches a detached ORM
    instance (which would risk an implicit lazy-load against a closed session).
    """

    id: int
    symbol: str
    current_scalp: PriorSignal | None = None
    current_swing: PriorSignal | None = None
    # The pair's recent realised track record per style, fed back to the model
    # (Iteration 9). Snapshotted in the opening transaction alongside the priors.
    scalp_performance: PriorPerformance | None = None
    swing_performance: PriorPerformance | None = None


@dataclass(frozen=True, slots=True)
class _PairOutcome:
    """Result of analysing a single pair — success (dual draft + indicators) or failure.

    ``indicators`` is the multi-timeframe snapshot keyed by timeframe
    (``{"1h": {...}, "4h": {...}}``), persisted verbatim onto each signal so it
    stays explainable against the exact inputs that produced it. A successful
    outcome always carries a :class:`DualSignalDraft` — a scalp *and* a swing —
    so it always yields two signal rows.
    """

    target: _PairTarget
    dual: DualSignalDraft | None = None
    indicators: dict[str, object] | None = None
    error: str | None = None
    # Token usage for this pair's AI call (Iteration 9); ``None`` when the
    # provider didn't report it or the pair failed before/at the AI call.
    usage: TokenUsage | None = None

    @property
    def failed(self) -> bool:
        return self.error is not None

    @property
    def emits_signals(self) -> bool:
        """Whether this outcome contributes signal rows (one scalp + one swing).

        True for every non-failed outcome: the AI provider guarantees both drafts
        are directional with an entry (it raises otherwise, which lands here as a
        failed outcome), so a successful analysis always persists two signals.
        """
        return not self.failed and self.dual is not None and self.indicators is not None


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
        #
        # ``_timeframe`` is the primary (decision) timeframe a signal is framed
        # on; ``_timeframes`` is the full set fetched and fed to the AI for a
        # top-down, multi-timeframe read — the union of the two per-style frames.
        # Each timeframe costs at most one market-data call per pair per run (the
        # caching provider serves slow frames from memory between bars).
        self._timeframe = settings.analysis_timeframe
        self._scalp_timeframes = list(settings.scalp_timeframes)
        self._swing_timeframes = list(settings.swing_timeframes)
        self._timeframes = list(settings.analysis_timeframes)
        self._candle_count = settings.analysis_candle_count

        # The decision timeframe recorded on each style's signal row: the lowest
        # frame the scalp is shown, the highest frame the swing is shown — the
        # two horizons the dual signal represents.
        self._scalp_timeframe = min(
            self._scalp_timeframes, key=lambda tf: _TIMEFRAME_MINUTES.get(tf, 0)
        )
        self._swing_timeframe = max(
            self._swing_timeframes, key=lambda tf: _TIMEFRAME_MINUTES.get(tf, 0)
        )

        # Per-style signal lifetime — stamped onto ``expires_at`` so the
        # freshness badge and retention sweep have something to act on.
        self._scalp_ttl = timedelta(minutes=settings.signal_scalp_ttl_minutes)
        self._swing_ttl = timedelta(minutes=settings.signal_swing_ttl_minutes)

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
            "Analysis run %s started (trigger=%s, pairs=%d, primary_timeframe=%s, timeframes=%s)",
            run_id,
            trigger.value,
            len(targets),
            self._timeframe,
            ",".join(self._timeframes),
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

        # Two signals (scalp + swing) per non-failed pair.
        signals_generated = sum(len(SignalType) for o in outcomes if o.emits_signals)
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
            signal_repo = SignalRepository(session)

            # Snapshot each pair's currently-open signals (one per style) in this
            # same opening transaction — before any network IO — so the model can
            # keep or adjust them. ``current_for_pair`` reads the latest per style.
            targets: list[_PairTarget] = []
            for p in await pairs.list_active():
                current = await signal_repo.current_for_pair(p.id)
                # The pair's recent realised track record per style — fed back so
                # the model calibrates against its own results (Iteration 9).
                scalp_closed = await signal_repo.list_recent_closed(
                    pair_id=p.id, signal_type=SignalType.SCALP, limit=_FEEDBACK_LOOKBACK
                )
                swing_closed = await signal_repo.list_recent_closed(
                    pair_id=p.id, signal_type=SignalType.SWING, limit=_FEEDBACK_LOOKBACK
                )
                targets.append(
                    _PairTarget(
                        id=p.id,
                        symbol=p.symbol,
                        current_scalp=_to_prior(current[SignalType.SCALP]),
                        current_swing=_to_prior(current[SignalType.SWING]),
                        scalp_performance=_performance_of(scalp_closed),
                        swing_performance=_performance_of(swing_closed),
                    )
                )

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
            views: list[TimeframeView] = []
            indicators: dict[str, object] = {}
            # One market-data call + indicator pass per timeframe. Sequential by
            # design: a single pair's handful of calls stays well inside the
            # provider's per-minute budget, and any one failing fails just this
            # pair (the run continues for the others).
            for timeframe in self._timeframes:
                candles = await self._market_data.fetch_candles(
                    target.symbol,
                    timeframe=timeframe,
                    count=self._candle_count,
                )
                snapshot = self._calculator.compute(candles)
                views.append(
                    TimeframeView(
                        timeframe=timeframe,
                        indicators=snapshot,
                        recent_candles=list(candles),
                    )
                )
                indicators[timeframe] = snapshot.to_storage_dict()

            context = AnalysisContext(
                symbol=target.symbol,
                primary_timeframe=self._timeframe,
                views=tuple(views),
                current_scalp=target.current_scalp,
                current_swing=target.current_swing,
                scalp_timeframes=tuple(self._scalp_timeframes),
                swing_timeframes=tuple(self._swing_timeframes),
                scalp_performance=target.scalp_performance,
                swing_performance=target.swing_performance,
            )
            result = await self._ai.analyze(context)
        except ServiceError as exc:
            logger.warning("Pair %s failed analysis: %s", target.symbol, exc)
            return _PairOutcome(target=target, error=f"{type(exc).__name__}: {exc}")
        except Exception as exc:  # last-resort per-pair containment
            logger.exception("Pair %s raised an unexpected error during analysis", target.symbol)
            return _PairOutcome(target=target, error=f"{type(exc).__name__}: {exc}")

        return _PairOutcome(
            target=target, dual=result.dual, indicators=indicators, usage=result.usage
        )

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
            signal
            for outcome in outcomes
            if outcome.emits_signals
            for signal in self._build_signals(outcome, run_id=run_id, generated_at=generated_at)
        ]

        processed = sum(1 for o in outcomes if not o.failed)
        failed = sum(1 for o in outcomes if o.failed)

        # Roll the per-pair token usage up to the run and estimate its cost. The
        # controller only ever touches the provider-neutral ``TokenUsage`` and a
        # ``Decimal`` — no SDK type leaks into persistence.
        usage = self._sum_usage(outcomes)
        cost_usd = estimate_cost_usd(self._ai.model, usage)

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
            run.prompt_tokens = usage.prompt_tokens if usage else None
            run.completion_tokens = usage.completion_tokens if usage else None
            run.cost_usd = cost_usd

            await session.commit()

        return run

    @staticmethod
    def _sum_usage(outcomes: Sequence[_PairOutcome]) -> TokenUsage | None:
        """Sum token usage across the run's pairs, or ``None`` if none reported.

        A pair that failed (or whose provider didn't report usage) simply
        contributes nothing; if no pair reported usage the run's columns stay
        ``NULL`` rather than a misleading zero.
        """
        usages = [o.usage for o in outcomes if o.usage is not None]
        if not usages:
            return None
        return TokenUsage(
            prompt_tokens=sum((u.prompt_tokens or 0) for u in usages),
            completion_tokens=sum((u.completion_tokens or 0) for u in usages),
        )

    def _build_signals(
        self,
        outcome: _PairOutcome,
        *,
        run_id: uuid.UUID,
        generated_at: datetime,
    ) -> list[Signal]:
        """Map an outcome's :class:`DualSignalDraft` onto two ``Signal`` rows.

        One row per style (scalp + swing). ``emits_signals`` has already
        guaranteed both drafts are directional with an entry, so the asserts
        below are invariants, not user-facing validation. Each style gets the
        timeframe it is framed on and a style-specific ``expires_at``.
        """
        dual = outcome.dual
        indicators = outcome.indicators
        assert dual is not None  # invariant from emits_signals
        assert indicators is not None  # set on every successful outcome

        return [
            self._build_one_signal(
                outcome.target.id,
                dual.scalp,
                signal_type=SignalType.SCALP,
                timeframe=self._scalp_timeframe,
                expires_at=generated_at + self._scalp_ttl,
                run_id=run_id,
                generated_at=generated_at,
                indicators=indicators,
            ),
            self._build_one_signal(
                outcome.target.id,
                dual.swing,
                signal_type=SignalType.SWING,
                timeframe=self._swing_timeframe,
                expires_at=generated_at + self._swing_ttl,
                run_id=run_id,
                generated_at=generated_at,
                indicators=indicators,
            ),
        ]

    def _build_one_signal(
        self,
        pair_id: int,
        draft: SignalDraft,
        *,
        signal_type: SignalType,
        timeframe: str,
        expires_at: datetime,
        run_id: uuid.UUID,
        generated_at: datetime,
        indicators: dict[str, object],
    ) -> Signal:
        """Map one directional :class:`SignalDraft` onto a ``Signal`` ORM row.

        Note on take-profits: a ``SignalDraft`` carries up to three ordered
        levels (TP1..TP3). The ``signals`` schema stores the full ladder across
        ``take_profit`` (TP1), ``take_profit_2`` (TP2) and ``take_profit_3``
        (TP3); we map each level positionally and leave the columns NULL for any
        level the draft did not emit.
        """
        assert draft.entry is not None  # invariant from emits_signals

        tps = draft.take_profits
        take_profit: Decimal | None = tps[0] if len(tps) > 0 else None
        take_profit_2: Decimal | None = tps[1] if len(tps) > 1 else None
        take_profit_3: Decimal | None = tps[2] if len(tps) > 2 else None

        return Signal(
            pair_id=pair_id,
            analysis_run_id=run_id,
            direction=SignalDirection(draft.direction),
            signal_type=signal_type,
            confidence=draft.confidence,
            entry_price=draft.entry,
            stop_loss=draft.stop_loss,
            take_profit=take_profit,
            take_profit_2=take_profit_2,
            take_profit_3=take_profit_3,
            timeframe=timeframe,
            rationale=draft.rationale,
            indicators_snapshot=indicators,
            generated_at=generated_at,
            expires_at=expires_at,
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
