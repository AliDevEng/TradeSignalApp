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
        # A single run produces at most one signal per pair. NULLs in
        # `analysis_run_id` (manual signals, or runs that have since
        # been deleted) are treated as distinct by Postgres, so this
        # does not block ad-hoc inserts.
        UniqueConstraint(
            "pair_id",
            "analysis_run_id",
            name="one_signal_per_run_per_pair",
        ),
        # Most-common access pattern: "latest signals for pair X" — the
        # composite index supports the equality + range scan in one go.
        Index("ix_signals_pair_id_generated_at", "pair_id", "generated_at"),
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
        SAEnum(SignalDirection, name="signal_direction", native_enum=True),
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
    take_profit: Mapped[Decimal | None] = mapped_column(
        Numeric(PRICE_PRECISION, PRICE_SCALE), nullable=True
    )

    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    indicators_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

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

    pair: Mapped[Pair] = relationship(back_populates="signals", lazy="joined")
    analysis_run: Mapped[AnalysisRun | None] = relationship(back_populates="signals")

    def __repr__(self) -> str:
        return f"<Signal {self.id} {self.direction.value}>"
