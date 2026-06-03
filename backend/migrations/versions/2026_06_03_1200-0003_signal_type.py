"""signals: add signal_type (scalp/swing) dimension

The analysis pipeline now emits one signal of *each* style per pair per run:
a short-term ``scalp`` and a higher-timeframe ``swing``. This migration adds the
``signal_type`` native enum + column, widens the per-run uniqueness constraint to
include the style (so a run can legitimately store two rows per pair), and adds a
composite index serving the "current signal for pair X of style Y" read.

The new ``signal_type`` enum is created explicitly before the column references it
(mirroring ``0001``'s handling of the other native enums) so the operation order
is independent of SQLAlchemy's auto-create heuristics.

Existing rows are backfilled to ``swing`` before the column is made NOT NULL —
defensive (the dev database has no signal rows yet, but the migration must be
safe against a populated table).

Revision ID: 0003_signal_type
Revises: 0002_signal_take_profit_targets
Create Date: 2026-06-03 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003_signal_type"
down_revision: str | None = "0002_signal_take_profit_targets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Declared at module level so both upgrade() and downgrade() reuse it.
# ``create_type=False`` keeps SQLAlchemy from issuing an implicit CREATE TYPE
# while we build the column — we control that lifecycle explicitly.
_SIGNAL_TYPE = postgresql.ENUM(
    "scalp",
    "swing",
    name="signal_type",
    create_type=False,
)

_OLD_UNIQUE = "one_signal_per_run_per_pair"
_NEW_UNIQUE = "one_signal_per_run_per_pair_style"
_NEW_INDEX = "ix_signals_pair_id_signal_type_generated_at"


def upgrade() -> None:
    bind = op.get_bind()

    _SIGNAL_TYPE.create(bind, checkfirst=False)

    # Add nullable first so existing rows are accepted, backfill, then enforce.
    op.add_column(
        "signals",
        sa.Column("signal_type", _SIGNAL_TYPE, nullable=True),
    )
    op.execute("UPDATE signals SET signal_type = 'swing' WHERE signal_type IS NULL")
    op.alter_column("signals", "signal_type", nullable=False)

    # A run now emits one signal per pair *per style*.
    op.drop_constraint(_OLD_UNIQUE, "signals", type_="unique")
    op.create_unique_constraint(
        _NEW_UNIQUE,
        "signals",
        ["pair_id", "analysis_run_id", "signal_type"],
    )

    op.create_index(
        _NEW_INDEX,
        "signals",
        ["pair_id", "signal_type", "generated_at"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(_NEW_INDEX, table_name="signals")
    op.drop_constraint(_NEW_UNIQUE, "signals", type_="unique")
    op.create_unique_constraint(
        _OLD_UNIQUE,
        "signals",
        ["pair_id", "analysis_run_id"],
    )
    op.drop_column("signals", "signal_type")
    _SIGNAL_TYPE.drop(bind, checkfirst=False)
