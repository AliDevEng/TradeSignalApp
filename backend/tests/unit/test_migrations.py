"""Unit tests for the Alembic configuration and the initial migration.

The migration is exercised in *offline* (``--sql``) mode so the tests do
not need a live Postgres. Offline mode runs the same env.py code path
(URL resolution, target_metadata wiring, transaction begin) that online
mode uses, so a passing offline run is a strong signal that the online
path is at least syntactically wired correctly. End-to-end "apply
against a real PG and round-trip data" coverage lives in iteration 5.

The tests intentionally inspect the rendered SQL rather than the
in-Python migration objects: the SQL is the contract that hits the
database, and asserting on it catches regressions that would slip past
a pure metadata diff (e.g. a stray DEFAULT, an enum created in the
wrong order).
"""

from __future__ import annotations

import contextlib
import io
import re
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"
MIGRATIONS_DIR = BACKEND_ROOT / "migrations"
VERSIONS_DIR = MIGRATIONS_DIR / "versions"


@pytest.fixture
def alembic_config() -> Config:
    """A Config bound to the project's alembic.ini.

    `script_location` in the .ini is relative (`migrations`), so we set
    the main option to an absolute path to make the fixture independent
    of the test runner's CWD.
    """
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    return cfg


# ── Layout ─────────────────────────────────────────────────────────────────


def test_alembic_ini_exists_at_backend_root():
    assert ALEMBIC_INI.is_file(), "alembic.ini must live at the backend root"


def test_env_py_exists():
    assert (MIGRATIONS_DIR / "env.py").is_file()


def test_script_template_exists():
    assert (MIGRATIONS_DIR / "script.py.mako").is_file()


def test_versions_directory_present():
    assert VERSIONS_DIR.is_dir()


# ── Script directory & revision graph ──────────────────────────────────────


def test_script_directory_loads(alembic_config: Config):
    script = ScriptDirectory.from_config(alembic_config)
    assert script.dir == str(MIGRATIONS_DIR)


def test_exactly_one_head_revision(alembic_config: Config):
    """Multiple heads = unmerged branches, which break `upgrade head`."""
    script = ScriptDirectory.from_config(alembic_config)
    heads = script.get_heads()
    assert len(heads) == 1, f"expected single head, got {heads}"


def test_initial_revision_has_no_down_revision(alembic_config: Config):
    script = ScriptDirectory.from_config(alembic_config)
    bases = script.get_bases()
    assert len(bases) == 1
    base = script.get_revision(bases[0])
    assert base is not None
    assert base.down_revision is None
    assert base.revision == "0001_initial_schema"


# ── Offline SQL rendering ──────────────────────────────────────────────────


@pytest.fixture
def initial_migration_sql(alembic_config: Config) -> str:
    """Render `alembic upgrade head` as SQL without touching a database."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        command.upgrade(alembic_config, "head", sql=True)
    return buffer.getvalue()


def test_offline_upgrade_emits_create_for_every_table(initial_migration_sql: str):
    sql = initial_migration_sql
    assert re.search(r"CREATE TABLE\s+pairs\b", sql, re.IGNORECASE)
    assert re.search(r"CREATE TABLE\s+analysis_runs\b", sql, re.IGNORECASE)
    assert re.search(r"CREATE TABLE\s+signals\b", sql, re.IGNORECASE)


def test_offline_upgrade_creates_native_enums_before_tables(initial_migration_sql: str):
    """Enum CREATE TYPE must precede the table that uses it; otherwise
    Postgres rejects the column type reference."""
    sql = initial_migration_sql

    status_pos = sql.find("CREATE TYPE analysis_run_status")
    trigger_pos = sql.find("CREATE TYPE analysis_run_trigger")
    direction_pos = sql.find("CREATE TYPE signal_direction")
    runs_pos = sql.find("CREATE TABLE analysis_runs")
    signals_pos = sql.find("CREATE TABLE signals")

    assert status_pos != -1
    assert trigger_pos != -1
    assert direction_pos != -1
    assert runs_pos != -1
    assert signals_pos != -1

    assert status_pos < runs_pos
    assert trigger_pos < runs_pos
    assert direction_pos < signals_pos


def test_offline_upgrade_includes_named_check_constraints(initial_migration_sql: str):
    sql = initial_migration_sql
    expected = [
        "ck_signals_confidence_in_unit_interval",
        "ck_signals_entry_price_positive",
        "ck_signals_stop_loss_positive_when_set",
        "ck_signals_take_profit_positive_when_set",
        "ck_analysis_runs_pairs_processed_non_negative",
        "ck_analysis_runs_pairs_failed_non_negative",
        "ck_analysis_runs_finished_at_not_before_started_at",
    ]
    for name in expected:
        assert name in sql, f"missing constraint {name!r} in migration SQL"


def test_offline_upgrade_includes_named_foreign_keys(initial_migration_sql: str):
    sql = initial_migration_sql
    assert "fk_signals_pair_id_pairs" in sql
    assert "fk_signals_analysis_run_id_analysis_runs" in sql
    # Match cascade semantics declared in the model.
    assert re.search(
        r"fk_signals_pair_id_pairs[\s\S]*?ON DELETE CASCADE",
        sql,
        re.IGNORECASE,
    )
    assert re.search(
        r"fk_signals_analysis_run_id_analysis_runs[\s\S]*?ON DELETE SET NULL",
        sql,
        re.IGNORECASE,
    )


def test_offline_upgrade_creates_composite_index(initial_migration_sql: str):
    sql = initial_migration_sql
    assert "ix_signals_pair_id_generated_at" in sql
    # Composite index covers (pair_id, generated_at) in that order.
    assert re.search(
        r"ix_signals_pair_id_generated_at[\s\S]*?\(\s*pair_id\s*,\s*generated_at\s*\)",
        sql,
        re.IGNORECASE,
    )


def test_offline_upgrade_uses_numeric_for_money_columns(initial_migration_sql: str):
    """Floats are forbidden for prices — the migration must pin NUMERIC(20,8)."""
    sql = initial_migration_sql
    for column in ("entry_price", "stop_loss", "take_profit"):
        assert re.search(
            rf"{column}\s+NUMERIC\(20,\s*8\)",
            sql,
            re.IGNORECASE,
        ), f"{column} must be NUMERIC(20, 8)"


def test_offline_upgrade_includes_unique_one_signal_per_run_per_pair(
    initial_migration_sql: str,
):
    assert "one_signal_per_run_per_pair" in initial_migration_sql


# ── 0003: signal_type (scalp/swing) ────────────────────────────────────────


def test_offline_upgrade_creates_signal_type_enum_before_use(initial_migration_sql: str):
    """The signal_type enum must be CREATE TYPE'd before the column references it."""
    sql = initial_migration_sql
    enum_pos = sql.find("CREATE TYPE signal_type")
    column_pos = sql.find("ADD COLUMN signal_type")
    assert enum_pos != -1, "signal_type enum must be created"
    assert column_pos != -1, "signal_type column must be added"
    assert enum_pos < column_pos


def test_offline_upgrade_widens_unique_constraint_to_include_style(initial_migration_sql: str):
    """0003 swaps the per-run/pair unique key for one that includes the style."""
    sql = initial_migration_sql
    assert "one_signal_per_run_per_pair_style" in sql
    # The old 2-column constraint is dropped and replaced.
    assert re.search(r"DROP CONSTRAINT\s+one_signal_per_run_per_pair\b", sql, re.IGNORECASE)


def test_offline_upgrade_adds_signal_type_index(initial_migration_sql: str):
    assert "ix_signals_pair_id_signal_type_generated_at" in initial_migration_sql


# ── 0004: signal_outcome tracking ──────────────────────────────────────────


def test_offline_upgrade_creates_signal_outcome_enum_before_use(initial_migration_sql: str):
    sql = initial_migration_sql
    enum_pos = sql.find("CREATE TYPE signal_outcome")
    column_pos = sql.find("ADD COLUMN outcome")
    assert enum_pos != -1, "signal_outcome enum must be created"
    assert column_pos != -1, "outcome column must be added"
    assert enum_pos < column_pos


def test_offline_upgrade_adds_outcome_columns(initial_migration_sql: str):
    sql = initial_migration_sql
    for column in ("outcome", "closed_at", "realized_r", "mfe", "mae", "last_evaluated_at"):
        assert re.search(rf"ADD COLUMN {column}\b", sql, re.IGNORECASE), (
            f"migration must add the {column!r} column"
        )


def test_offline_upgrade_outcome_defaults_to_open(initial_migration_sql: str):
    """The outcome column is NOT NULL with a server default so existing rows
    backfill to 'open' atomically."""
    sql = initial_migration_sql
    assert re.search(
        r"ADD COLUMN outcome[\s\S]*?DEFAULT\s+'open'",
        sql,
        re.IGNORECASE,
    )


def test_offline_upgrade_uses_numeric_for_realized_r(initial_migration_sql: str):
    assert re.search(r"realized_r\s+NUMERIC\(12,\s*4\)", initial_migration_sql, re.IGNORECASE)


def test_offline_upgrade_adds_outcome_index(initial_migration_sql: str):
    assert "ix_signals_outcome" in initial_migration_sql


# ── 0005: analysis_run AI usage / cost ─────────────────────────────────────


def test_offline_upgrade_adds_usage_columns(initial_migration_sql: str):
    sql = initial_migration_sql
    for column in ("prompt_tokens", "completion_tokens", "cost_usd"):
        assert re.search(rf"ADD COLUMN {column}\b", sql, re.IGNORECASE), (
            f"migration must add the {column!r} column"
        )


def test_offline_upgrade_uses_numeric_for_cost_usd(initial_migration_sql: str):
    """Money is never Float — cost_usd must be NUMERIC(12, 6)."""
    assert re.search(r"cost_usd\s+NUMERIC\(12,\s*6\)", initial_migration_sql, re.IGNORECASE)


def test_offline_upgrade_adds_non_negative_usage_checks(initial_migration_sql: str):
    sql = initial_migration_sql
    for name in (
        "ck_analysis_runs_prompt_tokens_non_negative",
        "ck_analysis_runs_completion_tokens_non_negative",
        "ck_analysis_runs_cost_usd_non_negative",
    ):
        assert name in sql, f"missing constraint {name!r} in migration SQL"


# ── env.py wiring ──────────────────────────────────────────────────────────


def test_env_py_uses_app_models_metadata():
    """env.py must point ``target_metadata`` at the same Base.metadata
    the application uses, otherwise autogenerate produces phantom diffs."""
    text = (MIGRATIONS_DIR / "env.py").read_text(encoding="utf-8")
    assert "from app.models import Base" in text
    assert "target_metadata = Base.metadata" in text


def test_env_py_loads_url_from_settings():
    """The DB URL must come from Settings, not a hard-coded .ini value."""
    text = (MIGRATIONS_DIR / "env.py").read_text(encoding="utf-8")
    assert "from app.config import get_settings" in text
    assert "set_main_option" in text


def test_env_py_runs_async_engine_online():
    """Online migrations must go through an async engine to match the
    application's `postgresql+asyncpg://` URL."""
    text = (MIGRATIONS_DIR / "env.py").read_text(encoding="utf-8")
    assert "async_engine_from_config" in text
    assert "run_sync" in text
