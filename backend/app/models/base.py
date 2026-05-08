"""Declarative base + shared mixins for SQLAlchemy ORM models.

Importing this module registers no tables on its own — `Base.metadata`
is the registry that concrete models populate. `app.models.__init__`
imports every model so that simply importing `app.models` is enough
for Alembic autogenerate to discover the full schema.

A naming convention is bound to the metadata so generated constraint /
index names are deterministic and portable. Without this, Alembic would
fall back to Postgres' implicit names, which differ between dialects
and break cross-database migrations or downgrades.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Project-wide declarative base.

    Models inherit from this directly. Cross-cutting columns are pulled
    in via mixins (see `TimestampMixin`) rather than baked into the base
    so that we can opt out per table when it doesn't make sense.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Adds `created_at` / `updated_at` driven by the database clock.

    Server-side defaults (`func.now()`) keep timestamps consistent across
    multiple workers and out-of-band writers (migrations, scheduled
    jobs, ad-hoc scripts) — every row gets the same canonical clock
    instead of whatever the local Python process happened to think
    "now" was.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
