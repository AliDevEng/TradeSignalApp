"""Unit tests for ORM model declarations.

These tests run against ``Base.metadata`` directly — no live database
is required. They lock in the column shape, constraints, and
relationships that downstream layers (repositories, controllers, the
Alembic migration that comes next in this iteration) depend on.

Round-tripping data through real Postgres lives in iteration 5's
integration suite; reproducing that here would require either a
running PG instance or a sqlite shim that can't model JSONB / UUID /
native enums faithfully.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from app.models import (
    AnalysisRun,
    AnalysisRunStatus,
    AnalysisRunTrigger,
    Base,
    Pair,
    Signal,
    SignalDirection,
)
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID

# ── Metadata wiring ────────────────────────────────────────────────────────


def test_all_tables_register_on_shared_metadata():
    table_names = set(Base.metadata.tables.keys())
    assert {"pairs", "signals", "analysis_runs"}.issubset(table_names)


def test_metadata_has_naming_convention():
    """Constraint names must be deterministic for migration portability."""
    convention = Base.metadata.naming_convention
    assert convention["fk"]
    assert convention["ck"]
    assert convention["ix"]
    assert convention["pk"]


# ── Pair ───────────────────────────────────────────────────────────────────


def test_pair_columns_have_expected_types():
    cols = Pair.__table__.c

    assert isinstance(cols["id"].type, Integer)
    assert cols["id"].primary_key

    assert isinstance(cols["symbol"].type, String)
    assert cols["symbol"].unique is True
    assert cols["symbol"].nullable is False

    assert isinstance(cols["base_currency"].type, String)
    assert cols["base_currency"].nullable is False
    assert isinstance(cols["quote_currency"].type, String)
    assert cols["quote_currency"].nullable is False

    assert isinstance(cols["display_name"].type, String)
    assert cols["display_name"].nullable is True

    assert isinstance(cols["is_active"].type, Boolean)
    assert cols["is_active"].nullable is False
    assert cols["is_active"].server_default is not None

    assert isinstance(cols["created_at"].type, DateTime)
    assert cols["created_at"].type.timezone is True
    assert cols["created_at"].nullable is False
    assert isinstance(cols["updated_at"].type, DateTime)
    assert cols["updated_at"].type.timezone is True


def test_pair_repr_shows_symbol():
    pair = Pair(symbol="XAUUSD", base_currency="XAU", quote_currency="USD")
    assert "XAUUSD" in repr(pair)


# ── AnalysisRun ────────────────────────────────────────────────────────────


def test_analysis_run_columns_have_expected_types():
    cols = AnalysisRun.__table__.c

    assert isinstance(cols["id"].type, UUID)
    assert cols["id"].primary_key
    assert cols["id"].default is not None  # uuid4 callable

    assert isinstance(cols["status"].type, SAEnum)
    assert cols["status"].type.name == "analysis_run_status"
    assert cols["status"].nullable is False

    assert isinstance(cols["trigger"].type, SAEnum)
    assert cols["trigger"].type.name == "analysis_run_trigger"
    assert cols["trigger"].nullable is False

    assert isinstance(cols["timeframe"].type, String)
    assert isinstance(cols["candle_count"].type, Integer)
    assert cols["candle_count"].nullable is False

    assert isinstance(cols["started_at"].type, DateTime)
    assert cols["started_at"].type.timezone is True
    assert cols["started_at"].nullable is False
    assert isinstance(cols["finished_at"].type, DateTime)
    assert cols["finished_at"].nullable is True

    assert isinstance(cols["pairs_processed"].type, Integer)
    assert cols["pairs_processed"].nullable is False
    assert isinstance(cols["pairs_failed"].type, Integer)
    assert cols["pairs_failed"].nullable is False

    assert isinstance(cols["error_message"].type, Text)
    assert cols["error_message"].nullable is True


def test_analysis_run_status_enum_members():
    assert {s.value for s in AnalysisRunStatus} == {
        "pending",
        "running",
        "success",
        "partial",
        "failed",
    }


def test_analysis_run_trigger_enum_members():
    assert {t.value for t in AnalysisRunTrigger} == {"scheduler", "manual"}


def test_analysis_run_check_constraints_present():
    constraint_names = {c.name for c in AnalysisRun.__table__.constraints if c.name}
    assert "ck_analysis_runs_pairs_processed_non_negative" in constraint_names
    assert "ck_analysis_runs_pairs_failed_non_negative" in constraint_names
    assert "ck_analysis_runs_finished_at_not_before_started_at" in constraint_names


# ── Signal ─────────────────────────────────────────────────────────────────


def test_signal_columns_have_expected_types():
    cols = Signal.__table__.c

    assert isinstance(cols["id"].type, UUID)
    assert cols["id"].primary_key
    assert cols["id"].default is not None

    assert isinstance(cols["pair_id"].type, Integer)
    assert cols["pair_id"].nullable is False

    assert isinstance(cols["analysis_run_id"].type, UUID)
    assert cols["analysis_run_id"].nullable is True

    assert isinstance(cols["direction"].type, SAEnum)
    assert cols["direction"].type.name == "signal_direction"

    assert isinstance(cols["confidence"].type, Numeric)
    assert cols["confidence"].nullable is False

    for price_col in (
        "entry_price",
        "stop_loss",
        "take_profit",
        "take_profit_2",
        "take_profit_3",
    ):
        assert isinstance(cols[price_col].type, Numeric), price_col
        assert cols[price_col].type.precision == 20
        assert cols[price_col].type.scale == 8

    assert cols["entry_price"].nullable is False
    assert cols["stop_loss"].nullable is True
    assert cols["take_profit"].nullable is True
    assert cols["take_profit_2"].nullable is True
    assert cols["take_profit_3"].nullable is True

    assert isinstance(cols["timeframe"].type, String)
    assert isinstance(cols["rationale"].type, Text)
    assert isinstance(cols["indicators_snapshot"].type, JSONB)

    assert isinstance(cols["generated_at"].type, DateTime)
    assert cols["generated_at"].type.timezone is True
    assert cols["generated_at"].nullable is False
    assert isinstance(cols["expires_at"].type, DateTime)
    assert cols["expires_at"].nullable is True


def test_signal_foreign_keys_have_correct_targets_and_actions():
    cols = Signal.__table__.c

    pair_fks = list(cols["pair_id"].foreign_keys)
    assert len(pair_fks) == 1
    assert pair_fks[0].column.table.name == "pairs"
    assert pair_fks[0].ondelete == "CASCADE"

    run_fks = list(cols["analysis_run_id"].foreign_keys)
    assert len(run_fks) == 1
    assert run_fks[0].column.table.name == "analysis_runs"
    assert run_fks[0].ondelete == "SET NULL"


def test_signal_check_constraints_present():
    constraint_names = {c.name for c in Signal.__table__.constraints if c.name}
    assert "ck_signals_confidence_in_unit_interval" in constraint_names
    assert "ck_signals_entry_price_positive" in constraint_names
    assert "ck_signals_stop_loss_positive_when_set" in constraint_names
    assert "ck_signals_take_profit_positive_when_set" in constraint_names
    assert "ck_signals_take_profit_2_positive_when_set" in constraint_names
    assert "ck_signals_take_profit_3_positive_when_set" in constraint_names


def test_signal_unique_constraint_per_run_per_pair_style():
    constraint = next(
        c for c in Signal.__table__.constraints if c.name == "one_signal_per_run_per_pair_style"
    )
    # A run emits one signal per pair *per style*, so the style is part of the key.
    assert {col.name for col in constraint.columns} == {
        "pair_id",
        "analysis_run_id",
        "signal_type",
    }


def test_signal_has_signal_type_column():
    assert "signal_type" in Signal.__table__.columns


def test_signal_composite_index_present():
    index_names = {ix.name for ix in Signal.__table__.indexes}
    assert "ix_signals_pair_id_generated_at" in index_names
    assert "ix_signals_pair_id_signal_type_generated_at" in index_names


def test_signal_direction_enum_members():
    assert {d.value for d in SignalDirection} == {"buy", "sell", "neutral"}


# ── Relationships ──────────────────────────────────────────────────────────


def test_pair_signals_relationship_declared():
    assert "signals" in Pair.__mapper__.relationships
    rel = Pair.__mapper__.relationships["signals"]
    assert rel.mapper.class_ is Signal
    assert rel.back_populates == "pair"


def test_signal_pair_relationship_declared():
    assert "pair" in Signal.__mapper__.relationships
    rel = Signal.__mapper__.relationships["pair"]
    assert rel.mapper.class_ is Pair
    assert rel.back_populates == "signals"


def test_signal_analysis_run_relationship_declared():
    assert "analysis_run" in Signal.__mapper__.relationships
    rel = Signal.__mapper__.relationships["analysis_run"]
    assert rel.mapper.class_ is AnalysisRun
    assert rel.back_populates == "signals"


def test_analysis_run_signals_relationship_declared():
    assert "signals" in AnalysisRun.__mapper__.relationships
    rel = AnalysisRun.__mapper__.relationships["signals"]
    assert rel.mapper.class_ is Signal
    assert rel.back_populates == "analysis_run"


# ── Construction sanity ────────────────────────────────────────────────────


def test_models_can_be_instantiated_with_keyword_args():
    """Smoke test: make sure no mapped_column option blocks construction.

    A declarative bug (e.g. forgetting `mapped_column` on a `Mapped[…]`
    annotation) would surface here as a TypeError.
    """
    pair = Pair(
        symbol="EURUSD",
        base_currency="EUR",
        quote_currency="USD",
        display_name="Euro / US Dollar",
        is_active=True,
    )
    assert pair.symbol == "EURUSD"

    run = AnalysisRun(
        timeframe="1h",
        candle_count=200,
        started_at=__import__("datetime").datetime.now(),
        status=AnalysisRunStatus.RUNNING,
        trigger=AnalysisRunTrigger.MANUAL,
    )
    assert run.status is AnalysisRunStatus.RUNNING

    signal = Signal(
        id=uuid.uuid4(),
        pair_id=1,
        direction=SignalDirection.BUY,
        confidence=0.82,
        entry_price=Decimal("1.07532"),
        stop_loss=Decimal("1.07000"),
        take_profit=Decimal("1.08500"),
        timeframe="1h",
        generated_at=__import__("datetime").datetime.now(),
    )
    assert signal.direction is SignalDirection.BUY
    assert signal.confidence == 0.82
