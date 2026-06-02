"""signals: add take_profit_2 / take_profit_3 (TP2/TP3)

The AI layer emits up to three ordered take-profit targets (TP1..TP3),
but the initial schema persisted only TP1 in ``signals.take_profit``.
This migration adds the two secondary targets as nullable price columns
so the full target ladder can be stored and later reworked.

Purely additive and non-breaking: existing rows get NULL for the new
columns, and code that only reads/writes ``take_profit`` keeps working
until the persistence layer is updated to populate TP2/TP3.

Revision ID: 0002_signal_take_profit_targets
Revises: 0001_initial_schema
Create Date: 2026-06-02 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_signal_take_profit_targets"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "signals",
        sa.Column("take_profit_2", sa.Numeric(precision=20, scale=8), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("take_profit_3", sa.Numeric(precision=20, scale=8), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_signals_take_profit_2_positive_when_set"),
        "signals",
        "take_profit_2 IS NULL OR take_profit_2 > 0",
    )
    op.create_check_constraint(
        op.f("ck_signals_take_profit_3_positive_when_set"),
        "signals",
        "take_profit_3 IS NULL OR take_profit_3 > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_signals_take_profit_3_positive_when_set"),
        "signals",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_signals_take_profit_2_positive_when_set"),
        "signals",
        type_="check",
    )
    op.drop_column("signals", "take_profit_3")
    op.drop_column("signals", "take_profit_2")
