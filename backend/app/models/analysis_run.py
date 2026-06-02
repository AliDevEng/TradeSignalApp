"""Records a single execution of the analysis pipeline.

Every scheduled (or manually triggered) run produces zero or more
`Signal` rows. Storing run metadata in its own table lets us answer
operational questions — "how long did the last run take?", "which
provider/model produced these signals?", "which runs failed?" —
without inflating the signal row or scraping logs.

Status and trigger are server-side enums so accidental free-text
writes are rejected at the database layer rather than the application
layer (where a stray string would silently leak through).
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.signal import Signal


class AnalysisRunStatus(enum.StrEnum):
    """Lifecycle states of a pipeline run.

    `partial` is distinct from `failed`: a run that produced signals for
    some pairs but failed on others should not be reported as a total
    failure, but also shouldn't be treated as fully successful for
    monitoring/alerting purposes.
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class AnalysisRunTrigger(enum.StrEnum):
    SCHEDULER = "scheduler"
    MANUAL = "manual"


class AnalysisRun(Base, TimestampMixin):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        CheckConstraint(
            "pairs_processed >= 0",
            name="pairs_processed_non_negative",
        ),
        CheckConstraint(
            "pairs_failed >= 0",
            name="pairs_failed_non_negative",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="finished_at_not_before_started_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    status: Mapped[AnalysisRunStatus] = mapped_column(
        SAEnum(
            AnalysisRunStatus,
            name="analysis_run_status",
            native_enum=True,
            # Persist the StrEnum *values* ("running"), not the member names
            # ("RUNNING"). The Postgres enum was created with the lowercase
            # values, so without this SQLAlchemy sends the uppercase name and
            # Postgres rejects it as an invalid enum input.
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=AnalysisRunStatus.PENDING,
        index=True,
    )
    trigger: Mapped[AnalysisRunTrigger] = mapped_column(
        SAEnum(
            AnalysisRunTrigger,
            name="analysis_run_trigger",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=AnalysisRunTrigger.SCHEDULER,
    )

    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)
    candle_count: Mapped[int] = mapped_column(Integer, nullable=False)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pairs_processed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    pairs_failed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Snapshotted so historical signals stay attributable to the
    # provider/model that generated them, even after config changes.
    ai_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    signals: Mapped[list[Signal]] = relationship(
        back_populates="analysis_run",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<AnalysisRun id={self.id} status={self.status.value}>"
