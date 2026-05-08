"""Generic async repository primitives.

A repository is the single bridge between a controller (which owns a
unit of work) and SQLAlchemy. Centralising query construction here
keeps controllers free of `select(...)`/session call sites — when the
schema changes, the blast radius is one file per model instead of
every consumer that happened to issue an ad-hoc query.

Transaction boundaries are deliberately *not* the repository's
concern. Repositories never commit and never roll back; they only stage
work on the session. This is what lets a single controller batch
multiple repository calls into one atomic unit of work — `add` to the
pair repo, `add_all` to the signal repo, `commit` once. If repos
auto-committed, that pattern would silently fragment into multiple
transactions.

The base class deliberately exposes a *narrow* surface (`get`, `add`,
`delete`, `list`, `count`, `exists`). Anything beyond that belongs in a
concrete subclass where the query intent is named — `get_by_symbol`,
`latest_for_pair`, etc. — instead of leaking through generic kwargs.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, ClassVar

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnExpressionArgument

from app.models.base import Base


class BaseRepository[ModelT: Base]:
    """Async, session-scoped repository for a single ORM model.

    Subclasses set ``model = SomeModel`` so generic methods can resolve
    the target table without each subclass duplicating the same boring
    `select(self.model)` boilerplate.
    """

    # Set on each concrete subclass. Declared as ClassVar so type
    # checkers don't treat it as an instance attribute that the
    # generic `__init__` is supposed to assign.
    model: ClassVar[type[Base]]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        """Underlying session — exposed for advanced use (e.g. composing
        repositories in a controller that needs to call ``flush`` once)."""
        return self._session

    # ── Read ────────────────────────────────────────────────────────────────

    async def get(self, pk: Any) -> ModelT | None:
        """Look up by primary key. Returns ``None`` if no row matches.

        Wraps ``Session.get`` so the type-narrowing happens here once
        instead of at every call site.
        """
        return await self._session.get(self.model, pk)  # type: ignore[return-value]

    async def list(
        self,
        *,
        where: Sequence[ColumnExpressionArgument[bool]] | None = None,
        order_by: Sequence[Any] | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> Sequence[ModelT]:
        """Generic paginated list. Subclasses override when the query
        is non-trivial (joins, derived columns, custom orderings)."""
        stmt = select(self.model)
        if where:
            stmt = stmt.where(*where)
        if order_by:
            stmt = stmt.order_by(*order_by)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        *,
        where: Sequence[ColumnExpressionArgument[bool]] | None = None,
    ) -> int:
        """Row count for a filter — used to drive `PaginationMeta.total`.

        Uses ``COUNT(*)`` over ``select_from(model)`` rather than
        ``func.count(model.id)`` so the same helper works for tables
        with composite primary keys.
        """
        stmt = select(func.count()).select_from(self.model)
        if where:
            stmt = stmt.where(*where)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def exists(self, *where: ColumnExpressionArgument[bool]) -> bool:
        """Cheap existence probe: ``SELECT 1 ... LIMIT 1``.

        Avoids the round trip of fetching whole rows when callers only
        need a yes/no answer (e.g. uniqueness checks before insert).
        """
        stmt = select(1).select_from(self.model)
        if where:
            stmt = stmt.where(*where)
        stmt = stmt.limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    # ── Write ───────────────────────────────────────────────────────────────

    def add(self, instance: ModelT) -> ModelT:
        """Stage a new row. Returns the same instance for fluent chaining.

        Synchronous because ``Session.add`` is synchronous in SQLAlchemy —
        no IO happens until flush.
        """
        self._session.add(instance)
        return instance

    def add_all(self, instances: Iterable[ModelT]) -> list[ModelT]:
        """Bulk-stage rows. Returns the materialised list so callers can
        re-use it without consuming the iterator twice."""
        materialised = list(instances)
        self._session.add_all(materialised)
        return materialised

    async def delete(self, instance: ModelT) -> None:
        """Mark an attached instance for deletion.

        For bulk deletes by predicate (e.g. expiry sweeps) call
        :meth:`delete_where` instead — it issues a single DELETE rather
        than loading every row into memory first.
        """
        await self._session.delete(instance)

    async def delete_where(
        self,
        *where: ColumnExpressionArgument[bool],
    ) -> int:
        """Issue a single ``DELETE ... WHERE`` statement.

        Returns the number of rows the database reports as deleted.
        Drivers that don't expose ``rowcount`` reliably (asyncpg
        does) will report ``-1``; we normalise that to ``0`` so callers
        never have to handle a sentinel.
        """
        if not where:
            raise ValueError("delete_where requires at least one predicate")
        stmt = sa_delete(self.model).where(*where)
        result = await self._session.execute(stmt)
        rowcount = result.rowcount
        return rowcount if rowcount and rowcount > 0 else 0

    async def flush(self) -> None:
        """Force a flush — useful when the caller needs DB-assigned IDs
        before commit (e.g. a freshly-inserted ``AnalysisRun.id`` referenced
        by ``Signal.analysis_run_id`` in the same transaction)."""
        await self._session.flush()
