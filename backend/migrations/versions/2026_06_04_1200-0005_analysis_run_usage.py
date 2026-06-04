"""analysis_runs: add AI token usage + estimated cost columns

Iteration 9 makes the model boundary observable: each run now records the token
usage of its AI calls and an estimated USD cost. This migration adds three
nullable columns to ``analysis_runs`` — ``prompt_tokens``, ``completion_tokens``
(both ``Integer``) and ``cost_usd`` (``Numeric(12, 6)`` — money is never Float,
6 dp captures sub-cent per-token costs) — each guarded by a non-negative CHECK.

All three are nullable: a provider may not report usage, and an unpriced model
leaves cost undefined rather than fabricated. Existing rows simply carry NULLs.

Revision ID: 0005_analysis_run_usage
Revises: 0004_signal_outcome
Create Date: 2026-06-04 12:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_analysis_run_usage"
down_revision: str | None = "0004_signal_outcome"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "analysis_runs",
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "analysis_runs",
        sa.Column("cost_usd", sa.Numeric(precision=12, scale=6), nullable=True),
    )

    # Bare constraint names — the metadata naming convention bound on
    # ``Base.metadata`` adds the ``ck_analysis_runs_`` prefix, so passing the
    # already-prefixed name here would double it (and overflow PG's 63-char id
    # limit). These match the ``name=`` on the model's CheckConstraints.
    op.create_check_constraint(
        "prompt_tokens_non_negative",
        "analysis_runs",
        "prompt_tokens IS NULL OR prompt_tokens >= 0",
    )
    op.create_check_constraint(
        "completion_tokens_non_negative",
        "analysis_runs",
        "completion_tokens IS NULL OR completion_tokens >= 0",
    )
    op.create_check_constraint(
        "cost_usd_non_negative",
        "analysis_runs",
        "cost_usd IS NULL OR cost_usd >= 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_analysis_runs_cost_usd_non_negative", "analysis_runs", type_="check")
    op.drop_constraint(
        "ck_analysis_runs_completion_tokens_non_negative", "analysis_runs", type_="check"
    )
    op.drop_constraint(
        "ck_analysis_runs_prompt_tokens_non_negative", "analysis_runs", type_="check"
    )
    op.drop_column("analysis_runs", "cost_usd")
    op.drop_column("analysis_runs", "completion_tokens")
    op.drop_column("analysis_runs", "prompt_tokens")
