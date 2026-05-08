"""Test doubles for infrastructure that would otherwise require live services.

Underscored to mark as test-internal; pytest does not collect modules with a
leading underscore. Imported via `from tests._stubs import ...`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession


class FakeDatabase:
    """Stand-in for `app.database.Database` that never opens a real connection.

    `healthcheck()` is configurable so tests can simulate a degraded/down DB.
    `session()` raises by default — tests that need a real session should
    override the `get_db_session` dependency at the FastAPI level instead of
    going through this stub.
    """

    def __init__(self, *, healthy: bool = True) -> None:
        self.healthy = healthy
        self.dispose_calls = 0

    async def healthcheck(self) -> bool:
        return self.healthy

    async def dispose(self) -> None:
        self.dispose_calls += 1

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        raise RuntimeError(
            "FakeDatabase.session() is not implemented — override the "
            "`get_db_session` dependency in your test instead."
        )
        yield  # unreachable; required to keep this an async generator


def install_fake_database(app: FastAPI, *, healthy: bool = True) -> FakeDatabase:
    """Replace the real Database on `app.state` with a `FakeDatabase`.

    The real engine constructed by `create_app()` is left to be garbage
    collected — it never opened a connection, so there's nothing to clean up.
    """
    fake = FakeDatabase(healthy=healthy)
    app.state.database = fake
    return fake
