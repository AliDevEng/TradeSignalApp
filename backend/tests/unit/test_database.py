"""Unit tests for the `Database` adapter.

We exercise lifecycle and session-error semantics without a live Postgres:
`create_async_engine` only allocates a pool, and the async sessionmaker
doesn't open a connection until SQL actually runs. That's enough surface
to validate the adapter's contract — repository-level integration tests
(real PG via testcontainers) come in iteration 5.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.database import Database
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

DUMMY_URL = "postgresql+asyncpg://user:pw@localhost:5432/test"


# ── Construction & accessors ───────────────────────────────────────────────


def test_database_constructs_async_engine():
    db = Database(DUMMY_URL)
    assert isinstance(db.engine, AsyncEngine)


def test_database_constructs_async_session_factory():
    db = Database(DUMMY_URL)
    assert isinstance(db.session_factory, async_sessionmaker)


def test_database_engine_url_round_trips():
    db = Database(DUMMY_URL)
    # SQLAlchemy hides the password by default in str(URL); the host/db
    # tail proves we passed the value through unmangled.
    rendered = str(db.engine.url)
    assert "localhost:5432/test" in rendered
    assert "postgresql+asyncpg" in rendered


def test_database_accepts_pool_kwargs_without_error():
    """Sanity check that our kwargs match SQLAlchemy's API surface."""
    db = Database(
        DUMMY_URL,
        pool_size=5,
        max_overflow=15,
        pool_recycle_seconds=600,
        pool_pre_ping=False,
        echo=True,
    )
    assert isinstance(db.engine, AsyncEngine)


def test_session_factory_has_expire_on_commit_disabled():
    """Async sessions must keep loaded attributes alive after commit —
    otherwise the next attribute access triggers an implicit lazy load
    which deadlocks in async contexts.
    """
    db = Database(DUMMY_URL)
    sf = db.session_factory
    # async_sessionmaker stores its kwargs in `kw`
    assert sf.kw["expire_on_commit"] is False


# ── session() context manager ──────────────────────────────────────────────


def _patch_session_factory(database: Database, session_mock: MagicMock):
    """Replace the sessionmaker with one that yields the given mock."""
    factory = MagicMock()
    factory.return_value = session_mock
    return patch.object(database, "_session_factory", factory)


def _make_session_mock() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


async def test_session_yields_session_and_does_not_rollback_on_success():
    db = Database(DUMMY_URL)
    session = _make_session_mock()

    with _patch_session_factory(db, session):
        async with db.session() as s:
            assert s is session

    session.rollback.assert_not_awaited()
    session.__aexit__.assert_awaited_once()


async def test_session_rolls_back_on_exception():
    db = Database(DUMMY_URL)
    session = _make_session_mock()

    with _patch_session_factory(db, session):
        with pytest.raises(RuntimeError, match="boom"):
            async with db.session():
                raise RuntimeError("boom")

    session.rollback.assert_awaited_once()
    session.__aexit__.assert_awaited_once()


# ── healthcheck() ──────────────────────────────────────────────────────────


async def test_healthcheck_returns_false_on_connection_failure():
    """Pointing at an unreachable port must surface as `False`, not an
    exception that bubbles up to the route handler."""
    db = Database("postgresql+asyncpg://u:p@127.0.0.1:1/nope", pool_pre_ping=False)
    try:
        result = await db.healthcheck()
        assert result is False
    finally:
        await db.dispose()


async def test_healthcheck_returns_true_when_select_one_succeeds():
    """Stub the engine.connect path so we don't need a real DB.

    `AsyncEngine` is slotted, so we swap the whole `_engine` attribute
    rather than monkey-patching `connect` on the real engine.
    """
    db = Database(DUMMY_URL)

    conn = MagicMock()
    conn.execute = AsyncMock()
    conn_ctx = MagicMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn)
    conn_ctx.__aexit__ = AsyncMock(return_value=None)

    fake_engine = MagicMock()
    fake_engine.connect = MagicMock(return_value=conn_ctx)

    with patch.object(db, "_engine", fake_engine):
        assert await db.healthcheck() is True
    conn.execute.assert_awaited_once()


# ── dispose() ──────────────────────────────────────────────────────────────


async def test_dispose_is_idempotent():
    db = Database(DUMMY_URL)
    await db.dispose()
    # Second call must not raise — lifespan cleanup may run twice in some
    # error paths and we don't want to mask the original exception.
    await db.dispose()
