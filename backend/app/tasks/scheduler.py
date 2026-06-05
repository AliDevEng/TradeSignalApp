"""Thin adapter over APScheduler's ``AsyncIOScheduler``.

The rest of the app talks to :class:`Scheduler`, never to APScheduler
directly, for the same reason it talks to ``Database`` instead of
SQLAlchemy: a narrow, intention-revealing surface that we can swap or mock,
and one place to enforce our defaults (UTC, single-instance, misfire grace).

Why these job defaults matter for correctness:

- ``max_instances=1`` — an analysis cycle that overruns its interval must not
  start a second copy concurrently; that would double provider cost and risk
  duplicate signals.
- ``coalesce=True`` — if several fire times are missed (the process was
  paused), run the job *once* on resume, not once per missed slot.
- ``misfire_grace_time`` — past this lateness a missed run is dropped rather
  than fired against stale market data.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import (
    SchedulerAlreadyRunningError,
    SchedulerNotRunningError,
)
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class Scheduler:
    """Owns the process-wide job scheduler and its lifecycle."""

    def __init__(
        self,
        *,
        timezone: str = "UTC",
        misfire_grace_seconds: int = 60,
    ) -> None:
        self._timezone = timezone
        self._misfire_grace_seconds = misfire_grace_seconds
        self._scheduler = AsyncIOScheduler(timezone=timezone)

    def add_interval_job(
        self,
        func: Callable[..., Any],
        *,
        minutes: int,
        job_id: str,
        name: str | None = None,
        coalesce: bool = True,
        max_instances: int = 1,
    ) -> Job:
        """Register a coroutine to run every ``minutes`` minutes.

        ``replace_existing=True`` makes registration idempotent so a restart
        (or a re-run of startup wiring in a test) never raises
        ``ConflictingIdError`` for an already-known job id.
        """
        return self._scheduler.add_job(
            func,
            trigger=IntervalTrigger(minutes=minutes, timezone=self._timezone),
            id=job_id,
            name=name or job_id,
            coalesce=coalesce,
            max_instances=max_instances,
            misfire_grace_time=self._misfire_grace_seconds,
            replace_existing=True,
        )

    def start(self) -> None:
        """Start dispatching. Idempotent — a second call is a no-op.

        Must be called from within a running event loop (the FastAPI
        lifespan provides one); ``AsyncIOScheduler`` binds to the loop it
        starts on. Idempotency is enforced by catching APScheduler's own
        guard rather than reading ``running`` — for an async scheduler that
        flag lags the real state transition by a loop tick, so a guard built
        on it would be racy.
        """
        try:
            self._scheduler.start()
        except SchedulerAlreadyRunningError:
            return
        logger.info(
            "Scheduler started | tz=%s | jobs=%d",
            self._timezone,
            len(self._scheduler.get_jobs()),
        )

    def shutdown(self, *, wait: bool = False) -> None:
        """Stop dispatching. Idempotent and safe to call during a failed startup."""
        try:
            self._scheduler.shutdown(wait=wait)
        except SchedulerNotRunningError:
            return
        logger.info("Scheduler stopped")

    @property
    def running(self) -> bool:
        return self._scheduler.running

    @property
    def jobs(self) -> list[Job]:
        return self._scheduler.get_jobs()

    def get_job(self, job_id: str) -> Job | None:
        return self._scheduler.get_job(job_id)

    def next_run_at(self, job_id: str) -> datetime | None:
        """When ``job_id`` is next scheduled to fire, or ``None``.

        ``None`` covers every "no upcoming run" case uniformly: the job isn't
        registered, the scheduler hasn't started, or the job is paused. The
        returned datetime is timezone-aware (the scheduler's tz).
        """
        job = self.get_job(job_id)
        return getattr(job, "next_run_time", None) if job is not None else None
