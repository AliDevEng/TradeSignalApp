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

from app.controllers import (
    AnalysisController,
    AnalysisRunController,
    PairController,
    PerformanceController,
    SignalController,
)
from app.database import Database
from app.database.repository import (
    AnalysisRunRepository,
    PairRepository,
    SignalRepository,
)
from app.services.ai import AIProvider
from app.services.market_data import MarketDataProvider
from app.tasks import Scheduler

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


# ── Request-scoped controllers ───────────────────────────────────────────────
#
# Read controllers are composed from the repository dependencies, so they share
# the request's session and transaction. (The write-side AnalysisController is
# different — it owns its own sessions and is constructed once in the lifespan;
# it is resolved off app state further down.)


def get_signal_controller(
    signals: SignalRepositoryDep,
    pairs: PairRepositoryDep,
) -> SignalController:
    return SignalController(signals=signals, pairs=pairs)


SignalControllerDep = Annotated[SignalController, Depends(get_signal_controller)]


def get_pair_controller(pairs: PairRepositoryDep) -> PairController:
    return PairController(pairs=pairs)


PairControllerDep = Annotated[PairController, Depends(get_pair_controller)]


def get_analysis_run_controller(runs: AnalysisRunRepositoryDep) -> AnalysisRunController:
    return AnalysisRunController(runs=runs)


AnalysisRunControllerDep = Annotated[AnalysisRunController, Depends(get_analysis_run_controller)]


def get_performance_controller(
    signals: SignalRepositoryDep,
    pairs: PairRepositoryDep,
) -> PerformanceController:
    return PerformanceController(signals=signals, pairs=pairs)


PerformanceControllerDep = Annotated[PerformanceController, Depends(get_performance_controller)]


# ── Iteration-3 services (resolved off app state) ────────────────────────────
#
# These are constructed once during the lifespan startup and live on
# `app.state`. The accessors fail fast with a clear message if resolved before
# startup (e.g. a handler hit on an app built without entering the lifespan)
# rather than surfacing a bare AttributeError deep in a stack trace.


def _require_state(request: Request, attr: str, label: str) -> object:
    value = getattr(request.app.state, attr, None)
    if value is None:
        raise RuntimeError(
            f"{label} is not initialised — it is created during application "
            "startup (lifespan). This dependency cannot be used outside a "
            "running app."
        )
    return value


def get_market_data_provider(request: Request) -> MarketDataProvider:
    return _require_state(request, "market_data_provider", "Market data provider")  # type: ignore[return-value]


MarketDataProviderDep = Annotated[MarketDataProvider, Depends(get_market_data_provider)]


def get_ai_provider(request: Request) -> AIProvider:
    return _require_state(request, "ai_provider", "AI provider")  # type: ignore[return-value]


AIProviderDep = Annotated[AIProvider, Depends(get_ai_provider)]


def get_scheduler(request: Request) -> Scheduler:
    return _require_state(request, "scheduler", "Scheduler")  # type: ignore[return-value]


SchedulerDep = Annotated[Scheduler, Depends(get_scheduler)]


def get_analysis_controller(request: Request) -> AnalysisController:
    return _require_state(request, "analysis_controller", "Analysis controller")  # type: ignore[return-value]


AnalysisControllerDep = Annotated[AnalysisController, Depends(get_analysis_controller)]
