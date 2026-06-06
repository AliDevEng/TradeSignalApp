"""AI-generated trade signal — terminal output of the analysis pipeline.

A `Signal` is the payload the frontend ultimately surfaces to the user:
direction, confidence, entry/SL/TP, and the rationale that produced it.
Money values use `Numeric` (not `Float`) — float arithmetic is
unsuitable for prices because rounding errors compound across pip-level
operations.

`indicators_snapshot` keeps the raw indicator values that fed the AI
prompt at signal-generation time. Storing them lets us back-test models
against historical inputs without re-fetching market data.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.analysis_run import AnalysisRun
    from app.models.pair import Pair


# 20 total digits / 8 fractional covers the precision range we care about:
# - 5-decimal FX (EURUSD)
# - 3-decimal JPY pairs
# - 8-decimal crypto, if we extend later
# Wider than strictly needed today, but cheap insurance against schema
# churn when we add new instrument classes.
PRICE_PRECISION = 20
PRICE_SCALE = 8


class SignalDirection(enum.StrEnum):
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"


class SignalType(enum.StrEnum):
    """Trade horizon a signal is framed on.

    A single analysis run emits one signal of *each* type per pair: a short-term
    ``SCALP`` (framed on the lower timeframes, tight stop, near targets) and a
    higher-timeframe ``SWING`` (wider stop, extended targets). The two are
    distinct rows so each carries its own direction, levels and confidence.
    """

    SCALP = "scalp"
    SWING = "swing"


class SignalOutcome(enum.StrEnum):
    """What actually happened to a signal once price had its say.

    A signal is born ``OPEN`` and stays there until the outcome evaluator finds
    that price touched a level or the signal aged out:

    * ``HIT_TP1``/``HIT_TP2``/``HIT_TP3`` — price reached that take-profit rung.
    * ``HIT_SL`` — price hit the stop-loss (a -1R loss).
    * ``EXPIRED`` — ``expires_at`` lapsed before any level was touched; the
      result is marked-to-market at the last candle.
    * ``CANCELLED`` — invalidated administratively (kept for completeness; the
      evaluator never assigns it).

    The terminal states are what the performance/calibration API (Iteration 8)
    aggregates into a track record, so the vocabulary is fixed at the DB layer.
    """

    OPEN = "open"
    HIT_TP1 = "hit_tp1"
    HIT_TP2 = "hit_tp2"
    HIT_TP3 = "hit_tp3"
    HIT_SL = "hit_sl"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Signal(Base, TimestampMixin):
    __tablename__ = "signals"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="confidence_in_unit_interval",
        ),
        CheckConstraint(
            "entry_price > 0",
            name="entry_price_positive",
        ),
        CheckConstraint(
            "stop_loss IS NULL OR stop_loss > 0",
            name="stop_loss_positive_when_set",
        ),
        CheckConstraint(
            "take_profit IS NULL OR take_profit > 0",
            name="take_profit_positive_when_set",
        ),
        CheckConstraint(
            "take_profit_2 IS NULL OR take_profit_2 > 0",
            name="take_profit_2_positive_when_set",
        ),
        CheckConstraint(
            "take_profit_3 IS NULL OR take_profit_3 > 0",
            name="take_profit_3_positive_when_set",
        ),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1)",
            name="quality_score_in_unit_interval",
        ),
        # A single run produces at most one signal per pair *per style*
        # (one scalp + one swing). NULLs in `analysis_run_id` (manual
        # signals, or runs that have since been deleted) are treated as
        # distinct by Postgres, so this does not block ad-hoc inserts.
        UniqueConstraint(
            "pair_id",
            "analysis_run_id",
            "signal_type",
            name="one_signal_per_run_per_pair_style",
        ),
        # Most-common access pattern: "latest signals for pair X" — the
        # composite index supports the equality + range scan in one go.
        Index("ix_signals_pair_id_generated_at", "pair_id", "generated_at"),
        # Serves "current signal for pair X of style Y" — the latest-per-style
        # read the controller and read API perform every run.
        Index(
            "ix_signals_pair_id_signal_type_generated_at",
            "pair_id",
            "signal_type",
            "generated_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    pair_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("pairs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable because (a) manual one-off signals don't belong to a run,
    # and (b) we use ON DELETE SET NULL so signals survive a run row
    # being purged (retention policy on analysis_runs is shorter than
    # on signals).
    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    direction: Mapped[SignalDirection] = mapped_column(
        SAEnum(
            SignalDirection,
            name="signal_direction",
            native_enum=True,
            # Persist the StrEnum values ("buy"), not the member names ("BUY"),
            # to match the lowercase Postgres enum created by the migration.
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    signal_type: Mapped[SignalType] = mapped_column(
        SAEnum(
            SignalType,
            name="signal_type",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(
        Numeric(5, 4, asdecimal=False),
        nullable=False,
    )

    entry_price: Mapped[Decimal] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=False
    )
    stop_loss: Mapped[Decimal | None] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True
    )
    # `take_profit` is TP1, the primary target. `take_profit_2`/`_3` are the
    # secondary scale-out targets the AI emits (ordered TP1..TP3). All three
    # are nullable: a signal may carry fewer than three targets, and the
    # persistence layer fills only the ones the AI returned.
    take_profit: Mapped[Decimal | None] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True
    )
    take_profit_2: Mapped[Decimal | None] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True
    )
    take_profit_3: Mapped[Decimal | None] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True
    )

    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    indicators_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # ── Quality gate (bias vs. actionable trade) ──────────────────────────────
    # Every run emits a directional bias per style, but only some are worth
    # acting on. ``should_trade`` is the deterministic gate's verdict (a bias
    # with ``False`` is "watch, don't trade"); ``quality_score`` ∈ [0,1] is its
    # blended quality; ``quality_snapshot`` keeps the explainable breakdown
    # (reward:risk, the reasons, the model's self-reported risks). Defaulted so
    # pre-gate rows backfill as actionable rather than NULL.
    should_trade: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default="true", index=True
    )
    quality_score: Mapped[float | None] = mapped_column(
        Numeric(5, 4, asdecimal=False), nullable=True
    )
    quality_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    # Provenance — pinned to the model that produced the signal so the
    # value of `confidence` stays interpretable across model upgrades.
    ai_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Outcome tracking (Iteration 7) ────────────────────────────────────
    # Filled by the outcome evaluator/job: what price did after the signal was
    # generated. `outcome` starts OPEN and transitions once (terminal); the
    # excursion/R fields let the performance API build a track record without
    # re-deriving anything from candles.
    outcome: Mapped[SignalOutcome] = mapped_column(
        SAEnum(
            SignalOutcome,
            name="signal_outcome",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SignalOutcome.OPEN,
        server_default=SignalOutcome.OPEN.value,
        index=True,
    )
    # When the signal reached a terminal outcome (NULL while OPEN).
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Realised result in R multiples (profit/loss ÷ initial risk). NULL while
    # OPEN, or when the signal carried no stop (risk undefined). Signed: a stop
    # hit is -1, a winning TP is positive.
    realized_r: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    # Max favourable / adverse excursion in R over the signal's life so far —
    # updated every evaluation, even while OPEN. NULL when risk is undefined.
    mfe: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    mae: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    # Last time the evaluator looked at this signal — lets the job skip nothing
    # and makes "is tracking alive?" observable.
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pair: Mapped[Pair] = relationship(back_populates="signals", lazy="joined")
    analysis_run: Mapped[AnalysisRun | None] = relationship(back_populates="signals")

    def __repr__(self) -> str:
        return f"<Signal {self.id} {self.direction.value}>"
