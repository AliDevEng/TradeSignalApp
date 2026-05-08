"""Cross-cutting FastAPI dependencies.

Kept separate from `schemas/` so the schemas layer stays transport-agnostic.
This is also the only file in the project allowed to bridge `database/`
into FastAPI's dependency-injection system — everything else just
consumes `DatabaseDep` / `DBSessionDep`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Database
from app.database.repository import (
    AnalysisRunRepository,
    PairRepository,
    SignalRepository,
)

# ── Pagination ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Pagination:
    page: int
    per_page: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


def pagination_params(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> Pagination:
    return Pagination(page=page, per_page=per_page)


PaginationDep = Annotated[Pagination, Depends(pagination_params)]


# ── Database ───────────────────────────────────────────────────────────────


def get_database(request: Request) -> Database:
    """Pull the singleton `Database` off `app.state`.

    `create_app()` constructs the instance once and stashes it on app state,
    so handlers and other dependencies can resolve it without importing
    module-level globals (which makes test isolation hard).
    """
    return request.app.state.database


DatabaseDep = Annotated[Database, Depends(get_database)]


async def get_db_session(database: DatabaseDep) -> AsyncIterator[AsyncSession]:
    """Yield a per-request `AsyncSession` with rollback-on-exception semantics.

    The session is closed automatically on request completion. Commits are
    explicit — controllers decide when a unit of work is complete. This
    keeps transaction boundaries visible at the call site instead of
    hiding them behind an implicit "commit on 2xx" middleware.
    """
    async with database.session() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# ── Repositories ───────────────────────────────────────────────────────────
#
# Repositories are session-scoped: one instance per request, sharing the
# request's session so multiple repos can stage work that commits
# together. The factory functions are deliberately tiny — there's no
# state worth caching, and FastAPI re-resolves them per call anyway.


def get_pair_repository(session: DBSessionDep) -> PairRepository:
    return PairRepository(session)


PairRepositoryDep = Annotated[PairRepository, Depends(get_pair_repository)]


def get_signal_repository(session: DBSessionDep) -> SignalRepository:
    return SignalRepository(session)


SignalRepositoryDep = Annotated[SignalRepository, Depends(get_signal_repository)]


def get_analysis_run_repository(session: DBSessionDep) -> AnalysisRunRepository:
    return AnalysisRunRepository(session)


AnalysisRunRepositoryDep = Annotated[AnalysisRunRepository, Depends(get_analysis_run_repository)]
