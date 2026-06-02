"""Async SQLAlchemy engine + session lifecycle.

A single `Database` instance owns the engine and session factory for the
entire application. It is constructed once by `create_app()` and disposed
during the FastAPI lifespan shutdown. Keeping this module free of FastAPI
imports lets background jobs, scripts, and tests reuse the same code path
without spinning up the web framework.

`expire_on_commit=False` is mandatory for async sessions: the default
behaviour expires loaded attributes after commit and re-fetches them on
access, which triggers implicit IO that breaks in async contexts.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """The database could not be reached (connect refused, dropped mid-query, …).

    A framework-agnostic marker so the HTTP layer can map "can't talk to the
    database" onto a retryable 503 **without importing the driver**. It exists
    because the raw failure shape is driver-specific: asyncpg can raise its own
    ``PostgresConnectionError`` *unwrapped* (e.g. when a pooled connection dies
    mid-operation), which is neither a SQLAlchemy ``OperationalError`` nor even a
    ``DBAPIError`` — so a handler keyed on those alone would miss it and the
    request would surface as a misleading 500. The :class:`Database` adapter is
    the one place that owns the driver, so it is the right place to normalise.
    """


# Connection-level failures we translate to :class:`DatabaseConnectionError`.
# SQLAlchemy's ``OperationalError``/``InterfaceError`` are driver-agnostic and
# cover the *wrapped* cases for any backend; asyncpg's own connection-error bases
# are added (best-effort) to catch the *unwrapped* escapes specific to it. A
# missing asyncpg import (e.g. a future driver swap) degrades gracefully to the
# SQLAlchemy-only set rather than breaking construction.
_CONNECTION_ERROR_TYPES: tuple[type[BaseException], ...] = (OperationalError, InterfaceError)
try:  # pragma: no cover - import guard for an optional driver
    from asyncpg import InterfaceError as _AsyncpgInterfaceError
    from asyncpg import PostgresConnectionError as _AsyncpgConnectionError

    _CONNECTION_ERROR_TYPES += (_AsyncpgConnectionError, _AsyncpgInterfaceError)
except ImportError:  # pragma: no cover
    pass


class Database:
    """Adapter around the async SQLAlchemy engine + session factory.

    Construction is sync because `create_async_engine` is sync — it only
    allocates a connection pool, it does not open connections. The first
    real connection is established lazily on first execute. `dispose()`
    is async because it drains pooled connections.
    """

    def __init__(
        self,
        url: str,
        *,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_recycle_seconds: int = 1800,
        pool_pre_ping: bool = True,
        echo: bool = False,
    ) -> None:
        self._engine: AsyncEngine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle_seconds,
            pool_pre_ping=pool_pre_ping,
            echo=echo,
        )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a session, rolling back on exception, always closing.

        Commit is the caller's responsibility — controllers/services know
        when a unit of work is complete; this context manager only
        guarantees cleanup. Used both by the FastAPI request dependency
        and by background jobs / one-off scripts.

        Connection-level failures (the database is unreachable, or a pooled
        connection died mid-operation) are normalised to
        :class:`DatabaseConnectionError` so callers — and the HTTP error layer —
        get one stable, retryable signal instead of a driver-specific exception
        that may slip past a SQLAlchemy-keyed handler. Query/programming errors
        are left untouched: they are bugs, not transient outages.
        """
        try:
            async with self._session_factory() as session:
                try:
                    yield session
                except Exception:
                    await self._safe_rollback(session)
                    raise
        except _CONNECTION_ERROR_TYPES as exc:
            raise DatabaseConnectionError(str(exc)) from exc

    @staticmethod
    async def _safe_rollback(session: AsyncSession) -> None:
        """Roll back without letting a rollback failure mask the original error.

        When the connection is already dead the rollback itself can raise; that
        secondary failure must not replace the real cause the caller needs to
        see, so it is logged and swallowed.
        """
        try:
            await session.rollback()
        except Exception:
            logger.warning("Rollback failed after a session error", exc_info=True)

    async def healthcheck(self) -> bool:
        """Round-trip a `SELECT 1` to confirm the pool can reach the database."""
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            logger.exception("Database healthcheck failed")
            return False
        return True

    async def dispose(self) -> None:
        """Close all pooled connections. Idempotent — safe to call twice."""
        await self._engine.dispose()
