"""Trading pair lookup table.

A `Pair` is a small, enumerable record (one row per FX/commodity symbol)
that signals reference. Symbols are normalised to upper-case at the
config layer (`app.config._require_pairs`); uniqueness is also enforced
at the database level so duplicates can't slip in via direct SQL or
data migrations.

`is_active` exists so we can stop trading a pair without losing
historical signals tied to it. A hard delete would force us to either
cascade-delete that history or break foreign-key integrity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.signal import Signal


class Pair(Base, TimestampMixin):
    __tablename__ = "pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(8), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    signals: Mapped[list[Signal]] = relationship(
        back_populates="pair",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Pair {self.symbol}>"
