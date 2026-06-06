"""signals: add quality-gate columns (should_trade, quality_score, quality_snapshot)

The pipeline now separates a directional *bias* from an *actionable* trade: every
run still emits a scalp and a swing bias, but a deterministic gate decides whether
each is worth acting on. This migration records that verdict on ``signals``:

* ``should_trade`` (``Boolean NOT NULL DEFAULT true``) — the gate's actionable
  flag. ``NOT NULL`` with a server default so existing rows backfill atomically as
  actionable (their pre-gate behaviour) and the column is immediately filterable.
* ``quality_score`` (``Numeric(5, 4)``, nullable) — the blended quality in [0, 1],
  guarded by a unit-interval CHECK. Nullable: a row generated before the gate, or
  one the gate could not score, carries NULL rather than a fabricated zero.
* ``quality_snapshot`` (``JSONB``, nullable) — the explainable breakdown
  (reward:risk, reasons, the model's self-reported risks).

Revision ID: 0006_signal_quality
Revises: 0005_analysis_run_usage
Create Date: 2026-06-06 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "0006_signal_quality"
down_revision: str | None = "0005_analysis_run_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "signals",
        sa.Column(
            "should_trade",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "signals",
        sa.Column("quality_score", sa.Numeric(precision=5, scale=4), nullable=True),
    )
    op.add_column(
        "signals",
        sa.Column("quality_snapshot", JSONB(), nullable=True),
    )

    # Bare constraint name — the metadata naming convention bound on
    # ``Base.metadata`` adds the ``ck_signals_`` prefix; passing the already-
    # prefixed name would double it. Matches the model's CheckConstraint name.
    op.create_check_constraint(
        "quality_score_in_unit_interval",
        "signals",
        "quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1)",
    )

    # Serves the "actionable signals only" browse filter the frontend adds.
    op.create_index("ix_signals_should_trade", "signals", ["should_trade"])


def downgrade() -> None:
    op.drop_index("ix_signals_should_trade", table_name="signals")
    op.drop_constraint(
        "ck_signals_quality_score_in_unit_interval", "signals", type_="check"
    )
    op.drop_column("signals", "quality_snapshot")
    op.drop_column("signals", "quality_score")
    op.drop_column("signals", "should_trade")
