"""The signal controller — read-side business logic for signals.

Where the :class:`~app.controllers.analysis_controller.AnalysisController` is a
*command* orchestrator (it produces signals as a background unit of work), this
is a *query* service: it serves the read endpoints the frontend paginates over.
The two differ in construction on purpose:

* The analysis controller takes the ``Database`` adapter and opens its own
  sessions, because a run is a minutes-long background job with no request
  behind it.
* This controller is **request-scoped**: it takes already-constructed,
  session-sharing repositories (wired in ``app.dependencies``) and borrows the
  request's transaction. A read is short and lives entirely inside one HTTP
  request, so owning session lifecycle here would be the wrong call.

The controller's job is the translation the view layer must not do itself:
resolve inputs (a pair *symbol* → its id), drive the repositories, and map the
ORM ``Signal`` onto the wire :class:`SignalResponse` — crucially, **while the
session is still open**, so reading the eagerly-loaded ``pair`` never triggers a
lazy load against a closed session. Returning detached ORM rows for the view to
map would invite exactly that bug.

Layering: this module imports repositories, models, schemas and sibling
controller types; it must not import ``app.views`` or ``fastapi``.
"""

from __future__ import annotations

import uuid

from app.controllers.exceptions import ResourceNotFoundError
from app.controllers.results import Page
from app.database.repository import PairRepository, SignalRepository
from app.models import Signal, SignalOutcome, SignalType
from app.schemas.signal import SignalResponse


class SignalController:
    """Serves paginated and single-resource reads over the ``signals`` table."""

    def __init__(self, *, signals: SignalRepository, pairs: PairRepository) -> None:
        self._signals = signals
        self._pairs = pairs

    # ── Queries ──────────────────────────────────────────────────────────────

    async def list_signals(
        self,
        *,
        offset: int,
        limit: int,
        pair_symbol: str | None = None,
        analysis_run_id: uuid.UUID | None = None,
        signal_type: str | None = None,
        outcome: str | None = None,
    ) -> Page[SignalResponse]:
        """A page of signals, newest first, filtered by pair, run, style, outcome.

        ``offset``/``limit`` are passed through from the view's pagination
        dependency; the view reassembles page/per_page into the response meta.
        ``signal_type``/``outcome`` arrive as validated wire literals and are
        converted to the ORM enums here, at the boundary, so the view never
        imports a model enum. Filtering by a ``pair_symbol`` that doesn't exist
        raises :class:`ResourceNotFoundError` rather than silently returning an
        empty page — a filter that names a concrete resource should fail honestly
        if that resource is unknown.
        """
        pair_id = await self._resolve_pair_id(pair_symbol)
        style = SignalType(signal_type) if signal_type is not None else None
        result = SignalOutcome(outcome) if outcome is not None else None

        total = await self._signals.count_filtered(
            pair_id=pair_id,
            analysis_run_id=analysis_run_id,
            signal_type=style,
            outcome=result,
        )
        # Short-circuit the row fetch when the count is zero: nothing to load,
        # and it keeps an empty page from issuing a guaranteed-empty SELECT.
        if total == 0:
            return Page(items=[], total=0)

        rows = await self._signals.list_paginated(
            offset=offset,
            limit=limit,
            pair_id=pair_id,
            analysis_run_id=analysis_run_id,
            signal_type=style,
            outcome=result,
            eager_load_pair=True,
        )
        return Page(items=[self._to_response(row) for row in rows], total=total)

    async def get_signal(self, signal_id: uuid.UUID) -> SignalResponse:
        """A single signal by id, or :class:`ResourceNotFoundError` if absent."""
        signal = await self._signals.get(signal_id)
        if signal is None:
            raise ResourceNotFoundError("signal", signal_id)
        return self._to_response(signal)

    async def list_latest_for_pair(
        self,
        symbol: str,
        *,
        limit: int = 10,
        signal_type: str | None = None,
    ) -> list[SignalResponse]:
        """The most-recent signals for one pair, newest first, optionally by style.

        Backs the pair-detail view. The pair is resolved first (and its symbol
        reused for the response), so an unknown symbol fails fast as a 404
        rather than returning a misleading empty list.
        """
        pair = await self._pairs.get_by_symbol(symbol)
        if pair is None:
            raise ResourceNotFoundError("pair", symbol)
        style = SignalType(signal_type) if signal_type is not None else None
        rows = await self._signals.latest_for_pair(pair.id, limit=limit, signal_type=style)
        return [self._to_response(row, pair_symbol=pair.symbol) for row in rows]

    async def list_for_run(self, analysis_run_id: uuid.UUID) -> list[SignalResponse]:
        """Every signal produced by a single analysis run, ordered by pair."""
        rows = await self._signals.list_for_run(analysis_run_id)
        return [self._to_response(row) for row in rows]

    # ── Mapping ──────────────────────────────────────────────────────────────

    async def _resolve_pair_id(self, symbol: str | None) -> int | None:
        if symbol is None:
            return None
        pair = await self._pairs.get_by_symbol(symbol)
        if pair is None:
            raise ResourceNotFoundError("pair", symbol)
        return pair.id

    @staticmethod
    def _to_response(signal: Signal, *, pair_symbol: str | None = None) -> SignalResponse:
        """Map an ORM ``Signal`` onto the wire schema.

        Must be called while the originating session is open: ``signal.pair`` is
        eagerly loaded (the relationship is ``lazy="joined"``), so reading the
        symbol here is free, but it would raise on a detached instance. Callers
        that already hold the pair (e.g. :meth:`list_latest_for_pair`) pass
        ``pair_symbol`` to skip the attribute hop entirely.
        """
        symbol = pair_symbol if pair_symbol is not None else _pair_symbol_of(signal)
        return SignalResponse(
            id=signal.id,
            pair_id=signal.pair_id,
            pair_symbol=symbol,
            analysis_run_id=signal.analysis_run_id,
            direction=signal.direction.value,
            signal_type=signal.signal_type.value,
            confidence=signal.confidence,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            take_profit_2=signal.take_profit_2,
            take_profit_3=signal.take_profit_3,
            timeframe=signal.timeframe,
            rationale=signal.rationale,
            indicators_snapshot=signal.indicators_snapshot,
            generated_at=signal.generated_at,
            expires_at=signal.expires_at,
            ai_provider=signal.ai_provider,
            ai_model=signal.ai_model,
            outcome=signal.outcome.value,
            realized_r=signal.realized_r,
            closed_at=signal.closed_at,
        )


def _pair_symbol_of(signal: Signal) -> str | None:
    """Read the loaded pair's symbol defensively (``None`` if it isn't set)."""
    pair = signal.pair
    return pair.symbol if pair is not None else None
