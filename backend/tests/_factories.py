"""Builders for ORM instances used in controller/route tests.

Underscored so pytest does not collect it. These construct **transient** ORM
objects (never persisted) purely so a controller's ORM→wire mapping has
something realistic to read. Keeping the construction in one place stops every
test from re-listing the full column set and drifting when the schema evolves.

Transient instances are safe here precisely because the controllers under test
read only already-set attributes (and an eagerly-set ``pair``) — they never
trigger a lazy load, which is the bug the eager-loading design exists to avoid.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models import (
    AnalysisRun,
    AnalysisRunStatus,
    AnalysisRunTrigger,
    Pair,
    Signal,
    SignalDirection,
    SignalType,
)

_FIXED_NOW = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)


def make_pair(
    *,
    id: int = 1,
    symbol: str = "EURUSD",
    base_currency: str = "EUR",
    quote_currency: str = "USD",
    display_name: str | None = "Euro / US Dollar",
    is_active: bool = True,
) -> Pair:
    pair = Pair(
        symbol=symbol,
        base_currency=base_currency,
        quote_currency=quote_currency,
        display_name=display_name,
        is_active=is_active,
    )
    pair.id = id
    return pair


def make_signal(
    *,
    id: uuid.UUID | None = None,
    pair: Pair | None = None,
    pair_id: int | None = None,
    analysis_run_id: uuid.UUID | None = None,
    direction: SignalDirection = SignalDirection.BUY,
    signal_type: SignalType = SignalType.SWING,
    confidence: float = 0.75,
    entry_price: Decimal = Decimal("1.10000000"),
    stop_loss: Decimal | None = Decimal("1.09000000"),
    take_profit: Decimal | None = Decimal("1.12000000"),
    take_profit_2: Decimal | None = None,
    take_profit_3: Decimal | None = None,
    timeframe: str = "1h",
    rationale: str | None = "RSI oversold; bullish MACD cross.",
    indicators_snapshot: dict | None = None,
    generated_at: datetime = _FIXED_NOW,
    ai_provider: str | None = "groq",
    ai_model: str | None = "llama-3.3-70b-versatile",
) -> Signal:
    pair = pair if pair is not None else make_pair()
    signal = Signal(
        pair_id=pair_id if pair_id is not None else pair.id,
        analysis_run_id=analysis_run_id,
        direction=direction,
        signal_type=signal_type,
        confidence=confidence,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        take_profit_2=take_profit_2,
        take_profit_3=take_profit_3,
        timeframe=timeframe,
        rationale=rationale,
        indicators_snapshot=indicators_snapshot or {"rsi": 28.4},
        generated_at=generated_at,
        expires_at=None,
        ai_provider=ai_provider,
        ai_model=ai_model,
    )
    signal.id = id or uuid.uuid4()
    # Set the relationship directly so the mapping reads it without a lazy load.
    signal.pair = pair
    return signal


def make_run(
    *,
    id: uuid.UUID | None = None,
    status: AnalysisRunStatus = AnalysisRunStatus.SUCCESS,
    trigger: AnalysisRunTrigger = AnalysisRunTrigger.SCHEDULER,
    timeframe: str = "1h",
    candle_count: int = 200,
    started_at: datetime = _FIXED_NOW,
    finished_at: datetime | None = _FIXED_NOW,
    pairs_processed: int = 3,
    pairs_failed: int = 0,
    ai_provider: str | None = "groq",
    ai_model: str | None = "llama-3.3-70b-versatile",
    error_message: str | None = None,
) -> AnalysisRun:
    run = AnalysisRun(
        status=status,
        trigger=trigger,
        timeframe=timeframe,
        candle_count=candle_count,
        started_at=started_at,
        finished_at=finished_at,
        pairs_processed=pairs_processed,
        pairs_failed=pairs_failed,
        ai_provider=ai_provider,
        ai_model=ai_model,
        error_message=error_message,
    )
    run.id = id or uuid.uuid4()
    return run
