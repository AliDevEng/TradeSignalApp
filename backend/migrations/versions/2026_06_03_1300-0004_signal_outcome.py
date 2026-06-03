"""signals: add outcome tracking (outcome enum + excursion/R columns)

Iteration 7 turns the signal generator into something *measurable*: every signal
now records what price actually did after it was generated. This migration adds
the ``signal_outcome`` native enum + column (born ``open``), plus the
mark-to-result columns the outcome evaluator fills — ``closed_at``,
``realized_r``, ``mfe``/``mae`` (max favourable/adverse excursion, in R), and
``last_evaluated_at``.

The new enum is created explicitly before the column references it (mirroring
``0001``/``0003``) so operation order is independent of SQLAlchemy's auto-create
heuristics. ``outcome`` is added NOT NULL with ``server_default 'open'`` so any
existing rows are backfilled to ``open`` atomically by Postgres — the realised
columns are nullable (undefined until a signal closes).

Revision ID: 0004_signal_outcome
Revises: 0003_signal_type
Create Date: 2026-06-03 13:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004_signal_outcome"
down_revision: str | None = "0003_signal_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Declared at module level so both upgrade() and downgrade() reuse it.
# ``create_type=False`` keeps SQLAlchemy from issuing an implicit CREATE TYPE
# while we add the column — we control that lifecycle explicitly.
_SIGNAL_OUTCOME = postgresql.ENUM(
    "open",
    "hit_tp1",
    "hit_tp2",
    "hit_tp3",
    "hit_sl",
    "expired",
    "cancelled",
    name="signal_outcome",
    create_type=False,
)

_OUTCOME_INDEX = "ix_signals_outcome"


def upgrade() -> None:
    bind = op.get_bind()

    _SIGNAL_OUTCOME.create(bind, checkfirst=False)

    # NOT NULL with a server default: existing rows are backfilled to 'open'
    # by Postgres in the same statement, no separate UPDATE needed.
    op.add_column(
        "signals",
        sa.Column(
            "outcome",
            _SIGNAL_OUTCOME,
            nullable=False,
            server_default="open",
        ),
    )
    op.add_column(
        "signals",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("realized_r", sa.Numeric(precision=12, scale=4), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("mfe", sa.Numeric(precision=12, scale=4), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("mae", sa.Numeric(precision=12, scale=4), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(_OUTCOME_INDEX, "signals", ["outcome"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(_OUTCOME_INDEX, table_name="signals")
    op.drop_column("signals", "last_evaluated_at")
    op.drop_column("signals", "mae")
    op.drop_column("signals", "mfe")
    op.drop_column("signals", "realized_r")
    op.drop_column("signals", "closed_at")
    op.drop_column("signals", "outcome")
    _SIGNAL_OUTCOME.drop(bind, checkfirst=False)
