"""Unit tests for the repository layer.

These tests use a mocked ``AsyncSession`` rather than a live Postgres.
We exercise three things:

1. The shape of the SQL each method emits — compiled with
   ``literal_binds`` so filter values, ordering, and limits are
   visible in the rendered string. This catches regressions that
   pure-Python attribute checks would miss (e.g. an ``order_by``
   accidentally swapped, a ``WHERE`` clause dropped on refactor).
2. The interaction with the session — that ``add`` calls
   ``session.add``, that ``delete_where`` issues a single statement,
   that ``flush`` is forwarded.
3. Argument validation — the few invariants we care about (positive
   ``limit``, non-empty ``delete_where`` predicate).

Round-trip "the query actually returns the right rows from PG"
coverage lives in iteration 5's integration suite.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.database.repository import (
    AnalysisRunRepository,
    BaseRepository,
    PairRepository,
    SignalRepository,
)
from app.models import AnalysisRun, AnalysisRunStatus, Pair, Signal, SignalType
from sqlalchemy import Select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

# ── Helpers ────────────────────────────────────────────────────────────────

# Always compile against the PG dialect: the schema uses PG-specific
# constructs (UUID, JSONB, native enums, ON CONFLICT) and the generic
# dialect can't render them.
_PG_DIALECT = postgresql.dialect()


def _compile(stmt: Any) -> str:
    """Render a SQLAlchemy statement with bound values inlined.

    Inlining lets the assertions check filter values directly instead of
    matching anonymous bind-parameter placeholders.
    """
    return str(stmt.compile(dialect=_PG_DIALECT, compile_kwargs={"literal_binds": True}))


def _make_session() -> MagicMock:
    """An ``AsyncSession``-shaped mock with the methods repos call.

    ``spec=AsyncSession`` keeps the attribute surface honest — a typo
    in a repository (e.g. ``self._session.exec(...)``) trips
    AttributeError instead of silently no-op'ing.
    """
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.delete = AsyncMock()
    session.get = AsyncMock()
    session.flush = AsyncMock()
    return session


def _result_with_scalars(rows: list[Any]) -> MagicMock:
    """Build a Result-like double whose ``.scalars().all()`` yields ``rows``.

    Also wires ``first`` for repos that take only the head row, and
    ``scalar_one`` for ``COUNT(*)`` paths.
    """
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = rows
    scalars.first.return_value = rows[0] if rows else None
    result.scalars.return_value = scalars
    result.first.return_value = rows[0] if rows else None
    result.scalar_one.return_value = len(rows)
    return result


# ── BaseRepository — a concrete subclass to exercise the generic surface ──


class _PairRepoForBaseTests(BaseRepository[Pair]):
    """Subclass exists only so we can poke ``BaseRepository`` directly
    without leaking model-specific assumptions into the base tests."""

    model = Pair


async def test_get_delegates_to_session_get():
    session = _make_session()
    session.get.return_value = "sentinel"
    repo = _PairRepoForBaseTests(session)

    result = await repo.get(7)

    assert result == "sentinel"
    session.get.assert_awaited_once()
    args, _kwargs = session.get.call_args
    assert args[0] is Pair
    assert args[1] == 7


def test_add_stages_instance_and_returns_it():
    session = _make_session()
    repo = _PairRepoForBaseTests(session)
    pair = Pair(symbol="EURUSD", base_currency="EUR", quote_currency="USD")

    returned = repo.add(pair)

    assert returned is pair
    session.add.assert_called_once_with(pair)


def test_add_all_materialises_iterator():
    session = _make_session()
    repo = _PairRepoForBaseTests(session)

    def _gen():
        yield Pair(symbol="A", base_currency="A", quote_currency="B")
        yield Pair(symbol="B", base_currency="A", quote_currency="B")

    out = repo.add_all(_gen())

    assert len(out) == 2
    session.add_all.assert_called_once()
    # add_all must receive a list, not a generator — generators are
    # exhausted after one pass and SQLAlchemy iterates internally.
    (passed,), _ = session.add_all.call_args
    assert isinstance(passed, list)
    assert len(passed) == 2


async def test_delete_forwards_to_session():
    session = _make_session()
    repo = _PairRepoForBaseTests(session)
    pair = Pair(symbol="X", base_currency="X", quote_currency="Y")

    await repo.delete(pair)

    session.delete.assert_awaited_once_with(pair)


async def test_list_applies_where_order_offset_limit():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = _PairRepoForBaseTests(session)

    await repo.list(
        where=[Pair.is_active.is_(True)],
        order_by=[Pair.symbol],
        offset=20,
        limit=10,
    )

    stmt = session.execute.call_args.args[0]
    sql = _compile(stmt).lower()
    assert "from pairs" in sql
    assert "is_active is true" in sql
    assert "order by pairs.symbol" in sql
    assert "limit 10" in sql
    assert "offset 20" in sql


async def test_count_uses_count_star_over_select_from():
    session = _make_session()
    result = MagicMock()
    result.scalar_one.return_value = 42
    session.execute.return_value = result
    repo = _PairRepoForBaseTests(session)

    n = await repo.count(where=[Pair.is_active.is_(True)])

    assert n == 42
    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "count(*)" in sql
    assert "from pairs" in sql
    assert "is_active is true" in sql


async def test_exists_renders_select_one_limit_one():
    session = _make_session()
    result = MagicMock()
    result.first.return_value = (1,)
    session.execute.return_value = result
    repo = _PairRepoForBaseTests(session)

    found = await repo.exists(Pair.symbol == "EURUSD")

    assert found is True
    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "limit 1" in sql
    assert "eurusd" in sql


async def test_exists_returns_false_when_no_row():
    session = _make_session()
    result = MagicMock()
    result.first.return_value = None
    session.execute.return_value = result
    repo = _PairRepoForBaseTests(session)

    assert await repo.exists(Pair.symbol == "NOPE") is False


async def test_delete_where_requires_predicate():
    session = _make_session()
    repo = _PairRepoForBaseTests(session)

    with pytest.raises(ValueError, match="predicate"):
        await repo.delete_where()


async def test_delete_where_emits_single_delete_statement():
    session = _make_session()
    result = MagicMock()
    result.rowcount = 7
    session.execute.return_value = result
    repo = _PairRepoForBaseTests(session)

    deleted = await repo.delete_where(Pair.is_active.is_(False))

    assert deleted == 7
    sql = _compile(session.execute.call_args.args[0]).lower()
    assert sql.startswith("delete from pairs")
    assert "is_active is false" in sql


async def test_delete_where_normalises_negative_rowcount_to_zero():
    """Some drivers / statements report ``-1`` instead of a real
    rowcount. The repo must hide that quirk from callers."""
    session = _make_session()
    result = MagicMock()
    result.rowcount = -1
    session.execute.return_value = result
    repo = _PairRepoForBaseTests(session)

    assert await repo.delete_where(Pair.is_active.is_(False)) == 0


async def test_flush_forwards_to_session():
    session = _make_session()
    repo = _PairRepoForBaseTests(session)

    await repo.flush()

    session.flush.assert_awaited_once()


# ── PairRepository ────────────────────────────────────────────────────────


async def test_pair_get_by_symbol_uppercases_input():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = PairRepository(session)

    await repo.get_by_symbol("eurusd")

    sql = _compile(session.execute.call_args.args[0])
    # Original lower-case input must not bleed into the query.
    assert "eurusd" not in sql
    assert "'EURUSD'" in sql


async def test_pair_list_active_filters_and_orders_by_symbol():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = PairRepository(session)

    await repo.list_active()

    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "is_active is true" in sql
    assert "order by pairs.symbol" in sql


async def test_pair_list_all_orders_by_symbol():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = PairRepository(session)

    await repo.list_all()

    sql = _compile(session.execute.call_args.args[0]).lower()
    # No WHERE clause — `list_all` returns active and inactive alike.
    assert "where" not in sql
    assert "order by pairs.symbol" in sql


async def test_pair_upsert_uses_on_conflict_do_update():
    session = _make_session()
    repo = PairRepository(session)

    await repo.upsert_by_symbol(
        symbol="eurusd",
        base_currency="eur",
        quote_currency="usd",
        display_name="Euro / US Dollar",
    )

    session.execute.assert_awaited_once()
    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "insert into pairs" in sql
    assert "on conflict (symbol) do update" in sql
    # Bootstrap must NOT silently re-enable a pair an operator has
    # disabled — `is_active` is excluded from the conflict update.
    assert "set is_active" not in sql.replace("\n", " ")
    # Currency codes must propagate refreshed values from `excluded`.
    assert "base_currency = excluded.base_currency" in sql
    assert "quote_currency = excluded.quote_currency" in sql
    # Symbol/currency strings must be uppercased on insert.
    assert "'EURUSD'" in _compile(session.execute.call_args.args[0])
    assert "'EUR'" in _compile(session.execute.call_args.args[0])
    assert "'USD'" in _compile(session.execute.call_args.args[0])


# ── SignalRepository ──────────────────────────────────────────────────────


async def test_signal_latest_for_pair_orders_by_generated_at_desc():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = SignalRepository(session)

    await repo.latest_for_pair(pair_id=42, limit=5)

    stmt: Select[Any] = session.execute.call_args.args[0]
    sql = _compile(stmt).lower()
    assert "from signals" in sql
    assert "pair_id = 42" in sql
    assert "order by signals.generated_at desc" in sql
    assert "limit 5" in sql


async def test_signal_latest_for_pair_rejects_non_positive_limit():
    session = _make_session()
    repo = SignalRepository(session)

    with pytest.raises(ValueError, match="positive"):
        await repo.latest_for_pair(pair_id=1, limit=0)


async def test_signal_list_paginated_applies_filters_and_pagination():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = SignalRepository(session)
    run_id = uuid.uuid4()

    await repo.list_paginated(
        offset=40,
        limit=20,
        pair_id=7,
        analysis_run_id=run_id,
    )

    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "pair_id = 7" in sql
    assert f"analysis_run_id = '{run_id}'" in sql
    assert "order by signals.generated_at desc" in sql
    assert "limit 20" in sql
    assert "offset 40" in sql


async def test_signal_list_paginated_applies_signal_type_filter():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = SignalRepository(session)

    await repo.list_paginated(offset=0, limit=20, signal_type=SignalType.SCALP)

    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "signal_type = 'scalp'" in sql


async def test_signal_latest_for_pair_applies_signal_type_filter():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = SignalRepository(session)

    await repo.latest_for_pair(pair_id=9, limit=1, signal_type=SignalType.SWING)

    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "pair_id = 9" in sql
    assert "signal_type = 'swing'" in sql


async def test_signal_current_for_pair_returns_one_per_style():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = SignalRepository(session)

    current = await repo.current_for_pair(pair_id=3)

    # Every style is keyed, even when no signal exists for it.
    assert set(current) == set(SignalType)
    assert all(v is None for v in current.values())


async def test_signal_list_paginated_attaches_loader_option_when_requested():
    """``eager_load_pair=True`` must attach a loader option so the
    follow-up IN-load happens. Without it the response model would
    trigger lazy IO on attribute access — fatal in async contexts.
    """
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = SignalRepository(session)

    await repo.list_paginated(offset=0, limit=10, eager_load_pair=False)
    stmt_without = session.execute.call_args.args[0]
    options_without = stmt_without._with_options  # type: ignore[attr-defined]

    session.execute.reset_mock()
    session.execute.return_value = _result_with_scalars([])

    await repo.list_paginated(offset=0, limit=10, eager_load_pair=True)
    stmt_with = session.execute.call_args.args[0]
    options_with = stmt_with._with_options  # type: ignore[attr-defined]

    assert len(options_with) == len(options_without) + 1


async def test_signal_count_filtered_emits_count_star():
    session = _make_session()
    result = MagicMock()
    result.scalar_one.return_value = 13
    session.execute.return_value = result
    repo = SignalRepository(session)

    n = await repo.count_filtered(pair_id=3)

    assert n == 13
    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "count(*)" in sql
    assert "from signals" in sql
    assert "pair_id = 3" in sql


async def test_signal_list_for_run_orders_by_pair_id():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = SignalRepository(session)
    run_id = uuid.uuid4()

    await repo.list_for_run(run_id)

    sql = _compile(session.execute.call_args.args[0]).lower()
    assert f"analysis_run_id = '{run_id}'" in sql
    assert "order by signals.pair_id" in sql


async def test_signal_delete_expired_filters_on_expires_at():
    session = _make_session()
    result = MagicMock()
    result.rowcount = 4
    session.execute.return_value = result
    repo = SignalRepository(session)
    now = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)

    deleted = await repo.delete_expired(now=now)

    assert deleted == 4
    sql = _compile(session.execute.call_args.args[0]).lower()
    assert sql.startswith("delete from signals")
    assert "expires_at is not null" in sql
    assert "expires_at <" in sql


# ── AnalysisRunRepository ─────────────────────────────────────────────────


async def test_analysis_run_list_recent_orders_desc_with_limit():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = AnalysisRunRepository(session)

    await repo.list_recent(limit=15)

    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "from analysis_runs" in sql
    assert "order by analysis_runs.started_at desc" in sql
    assert "limit 15" in sql


async def test_analysis_run_list_recent_rejects_non_positive_limit():
    session = _make_session()
    repo = AnalysisRunRepository(session)

    with pytest.raises(ValueError, match="positive"):
        await repo.list_recent(limit=0)


async def test_analysis_run_list_paginated_applies_status_filter():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = AnalysisRunRepository(session)

    await repo.list_paginated(
        offset=10,
        limit=5,
        status=AnalysisRunStatus.FAILED,
    )

    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "status = 'failed'" in sql
    assert "limit 5" in sql
    assert "offset 10" in sql


async def test_analysis_run_count_filtered_with_status():
    session = _make_session()
    result = MagicMock()
    result.scalar_one.return_value = 3
    session.execute.return_value = result
    repo = AnalysisRunRepository(session)

    n = await repo.count_filtered(status=AnalysisRunStatus.SUCCESS)

    assert n == 3
    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "count(*)" in sql
    assert "status = 'success'" in sql


async def test_analysis_run_get_latest_successful_filters_and_limits_one():
    session = _make_session()
    session.execute.return_value = _result_with_scalars([])
    repo = AnalysisRunRepository(session)

    await repo.get_latest_successful()

    sql = _compile(session.execute.call_args.args[0]).lower()
    assert "status = 'success'" in sql
    assert "order by analysis_runs.started_at desc" in sql
    assert "limit 1" in sql


# ── Smoke: model class wired correctly on every repo ──────────────────────


@pytest.mark.parametrize(
    ("repo_cls", "expected_model"),
    [
        (PairRepository, Pair),
        (SignalRepository, Signal),
        (AnalysisRunRepository, AnalysisRun),
    ],
)
def test_repository_model_attribute_set(repo_cls, expected_model):
    """The base methods rely on ``cls.model`` being set; this is the
    cheapest possible regression test against forgetting it on a
    future repository."""
    assert repo_cls.model is expected_model
