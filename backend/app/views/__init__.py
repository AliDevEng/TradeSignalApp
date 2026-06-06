"""API surface aggregation.

Each sub-router declares its own resource prefix (`/signals`, `/pairs`, ...).
This module bundles them under the v1 version prefix so `main.py` only has to
attach one router to the app — the only place that knows the version string.
"""

from fastapi import APIRouter

from app.views import analysis, calendar, health, pairs, performance, signals

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(health.router)
api_v1_router.include_router(signals.router)
api_v1_router.include_router(pairs.router)
api_v1_router.include_router(analysis.router)
api_v1_router.include_router(performance.router)
api_v1_router.include_router(calendar.router)

__all__ = ["api_v1_router"]
