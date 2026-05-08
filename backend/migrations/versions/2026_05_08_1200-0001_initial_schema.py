"""initial schema: pairs, analysis_runs, signals

Establishes the data layer declared in ``app.models``: the trading-pair
lookup, the per-run pipeline ledger, and the AI-generated signals that
hang off of both. The native Postgres enums (``analysis_run_status``,
``analysis_run_trigger``, ``signal_direction``) are created explicitly
before any column references them so the operation order is independent
of SQLAlchemy's auto-create heuristics — those heuristics break the
moment a second column starts referencing the same enum, which is only
a matter of time.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-08 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ── Native enum types ─────────────────────────────────────────────────────
# Declared at module level so both upgrade() and downgrade() can reuse the
# same definition. ``create_type=False`` prevents SQLAlchemy from issuing
# an implicit CREATE TYPE while building tables — we control that
# lifecycle explicitly below.

_ANALYSIS_RUN_STATUS = postgresql.ENUM(
    "pending",
    "running",
    "success",
    "partial",
    "failed",
    name="analysis_run_status",
    create_type=False,
)
_ANALYSIS_RUN_TRIGGER = postgresql.ENUM(
    "scheduler",
    "manual",
    name="analysis_run_trigger",
    create_type=False,
)
_SIGNAL_DIRECTION = postgresql.ENUM(
    "buy",
    "sell",
    "neutral",
    name="signal_direction",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # ── pairs ─────────────────────────────────────────────────────────────
    op.create_table(
        "pairs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("base_currency", sa.String(length=8), nullable=False),
        sa.Column("quote_currency", sa.String(length=8), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pairs")),
        sa.UniqueConstraint("symbol", name=op.f("uq_pairs_symbol")),
    )
    op.create_index(op.f("ix_pairs_symbol"), "pairs", ["symbol"], unique=False)

    # ── analysis_runs ─────────────────────────────────────────────────────
    _ANALYSIS_RUN_STATUS.create(bind, checkfirst=False)
    _ANALYSIS_RUN_TRIGGER.create(bind, checkfirst=False)

    op.create_table(
        "analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", _ANALYSIS_RUN_STATUS, nullable=False),
        sa.Column("trigger", _ANALYSIS_RUN_TRIGGER, nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("candle_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "pairs_processed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "pairs_failed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("ai_provider", sa.String(length=32), nullable=True),
        sa.Column("ai_model", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_runs")),
        sa.CheckConstraint(
            "pairs_processed >= 0",
            name=op.f("ck_analysis_runs_pairs_processed_non_negative"),
        ),
        sa.CheckConstraint(
            "pairs_failed >= 0",
            name=op.f("ck_analysis_runs_pairs_failed_non_negative"),
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name=op.f("ck_analysis_runs_finished_at_not_before_started_at"),
        ),
    )
    op.create_index(
        op.f("ix_analysis_runs_status"),
        "analysis_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_runs_started_at"),
        "analysis_runs",
        ["started_at"],
        unique=False,
    )

    # ── signals ───────────────────────────────────────────────────────────
    _SIGNAL_DIRECTION.create(bind, checkfirst=False)

    op.create_table(
        "signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pair_id", sa.Integer(), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("direction", _SIGNAL_DIRECTION, nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("entry_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("stop_loss", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("take_profit", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "indicators_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_provider", sa.String(length=32), nullable=True),
        sa.Column("ai_model", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signals")),
        sa.ForeignKeyConstraint(
            ["pair_id"],
            ["pairs.id"],
            name=op.f("fk_signals_pair_id_pairs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_signals_analysis_run_id_analysis_runs"),
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_signals_confidence_in_unit_interval"),
        ),
        sa.CheckConstraint(
            "entry_price > 0",
            name=op.f("ck_signals_entry_price_positive"),
        ),
        sa.CheckConstraint(
            "stop_loss IS NULL OR stop_loss > 0",
            name=op.f("ck_signals_stop_loss_positive_when_set"),
        ),
        sa.CheckConstraint(
            "take_profit IS NULL OR take_profit > 0",
            name=op.f("ck_signals_take_profit_positive_when_set"),
        ),
        sa.UniqueConstraint(
            "pair_id",
            "analysis_run_id",
            name="one_signal_per_run_per_pair",
        ),
    )
    op.create_index(op.f("ix_signals_pair_id"), "signals", ["pair_id"], unique=False)
    op.create_index(
        op.f("ix_signals_analysis_run_id"),
        "signals",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signals_generated_at"),
        "signals",
        ["generated_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_signals_expires_at"),
        "signals",
        ["expires_at"],
        unique=False,
    )
    # Composite index supports the dominant access pattern: "latest
    # signals for pair X". Custom name is preserved verbatim from the
    # model declaration so an autogenerate diff produces no changes.
    op.create_index(
        "ix_signals_pair_id_generated_at",
        "signals",
        ["pair_id", "generated_at"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()

    # signals first — it FK-references both other tables.
    op.drop_index("ix_signals_pair_id_generated_at", table_name="signals")
    op.drop_index(op.f("ix_signals_expires_at"), table_name="signals")
    op.drop_index(op.f("ix_signals_generated_at"), table_name="signals")
    op.drop_index(op.f("ix_signals_analysis_run_id"), table_name="signals")
    op.drop_index(op.f("ix_signals_pair_id"), table_name="signals")
    op.drop_table("signals")
    _SIGNAL_DIRECTION.drop(bind, checkfirst=False)

    op.drop_index(op.f("ix_analysis_runs_started_at"), table_name="analysis_runs")
    op.drop_index(op.f("ix_analysis_runs_status"), table_name="analysis_runs")
    op.drop_table("analysis_runs")
    _ANALYSIS_RUN_TRIGGER.drop(bind, checkfirst=False)
    _ANALYSIS_RUN_STATUS.drop(bind, checkfirst=False)

    op.drop_index(op.f("ix_pairs_symbol"), table_name="pairs")
    op.drop_table("pairs")
