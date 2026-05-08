"""Alembic environment.

Bridges Alembic's sync-only command surface to our async SQLAlchemy stack.
The application and migrations share a single source of truth for both the
database URL (``app.config.Settings``) and the schema definition
(``app.models.Base.metadata``) — drifting them apart is the most common
class of migration bug, and consolidating them here makes that impossible.

Notes:
- ``compare_type`` / ``compare_server_default`` are enabled so autogenerate
  catches column-type changes and server-side default drift, which the
  default config silently ignores.
- Online mode runs through an async engine because the application URL is
  ``postgresql+asyncpg://…``; using ``run_sync`` lets Alembic's sync
  migration ops run against a real connection without us maintaining a
  parallel sync URL.
- A ``NullPool`` is used for online migrations: a migration is a one-shot
  process, so connection pooling adds zero value and gets in the way of a
  clean shutdown.
"""

from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, async_engine_from_config

# Make the `app` package importable when alembic is invoked from the
# backend root (the usual path) regardless of how `prepend_sys_path` is
# resolved by the caller's CWD.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

from app.config import get_settings  # noqa: E402  (sys.path mutation above)
from app.models import Base  # noqa: E402  — importing registers every model

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve the URL from Settings rather than alembic.ini so a typo in
# `.env` is caught by Pydantic validation, not by a confusing connect
# error halfway through a migration. ``%`` is escaped because
# ConfigParser interprets it as interpolation syntax.
_settings = get_settings()
_database_url = _settings.database_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", _database_url)

target_metadata = Base.metadata


def _configure_context(connection: Connection | None = None, *, url: str | None = None) -> None:
    """Single place to set Alembic's runtime options.

    Keeping the offline and online code paths funneling through here
    guarantees both modes apply the same comparison rules — diverging
    them historically caused autogenerate to produce different output
    depending on whether ``--sql`` was passed.
    """
    context.configure(
        connection=connection,
        url=url,
        target_metadata=target_metadata,
        literal_binds=url is not None,
        dialect_opts={"paramstyle": "named"} if url is not None else {},
        compare_type=True,
        compare_server_default=True,
        include_schemas=False,
        # Render server-side defaults as the same SQL the model declared
        # so generated migrations match what create_all would produce.
        render_as_batch=False,
    )


def run_migrations_offline() -> None:
    """Emit SQL to stdout/buffer without touching a database."""
    _configure_context(url=_settings.database_url)
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    _configure_context(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    section = config.get_section(config.config_ini_section, {})
    connectable: AsyncEngine = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )
    try:
        async with connectable.connect() as connection:
            await connection.run_sync(_do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Apply migrations against the real database via an async engine."""
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
