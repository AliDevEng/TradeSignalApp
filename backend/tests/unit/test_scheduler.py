"""Unit tests for the Scheduler adapter.

``AsyncIOScheduler`` binds to the running event loop on ``start``, so these
tests are async (pytest-asyncio supplies the loop). Jobs use a 15-minute
interval, so none actually fire during the test — we only assert registration
and lifecycle, not execution timing.
"""

from __future__ import annotations

import asyncio

from app.tasks import Scheduler


async def _noop() -> None:
    return None


async def test_add_interval_job_registers_with_safe_defaults():
    scheduler = Scheduler(misfire_grace_seconds=42)
    job = scheduler.add_interval_job(_noop, minutes=15, job_id="analysis", name="Analysis")

    assert scheduler.get_job("analysis") is job
    assert [j.id for j in scheduler.jobs] == ["analysis"]
    # Operationally critical defaults — see the docstring on Scheduler.
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.misfire_grace_time == 42


async def test_register_is_idempotent_on_job_id():
    """``replace_existing`` collapses a re-registered id once the scheduler is
    running (before start, jobs are merely pending and not yet de-duplicated)."""
    scheduler = Scheduler()
    scheduler.add_interval_job(_noop, minutes=15, job_id="dup")
    scheduler.start()
    scheduler.add_interval_job(_noop, minutes=30, job_id="dup")  # replaces
    assert len(scheduler.jobs) == 1
    scheduler.shutdown(wait=False)


async def test_start_then_shutdown_toggles_running_and_is_idempotent():
    scheduler = Scheduler()
    scheduler.add_interval_job(_noop, minutes=15, job_id="j")

    assert scheduler.running is False
    scheduler.start()
    assert scheduler.running is True
    scheduler.start()  # second call is a no-op, must not raise
    assert scheduler.running is True

    scheduler.shutdown(wait=False)
    # AsyncIOScheduler completes shutdown on the next loop tick, so yield once
    # before observing the flag.
    await asyncio.sleep(0)
    assert scheduler.running is False
    scheduler.shutdown(wait=False)  # idempotent — no SchedulerNotRunningError
    assert scheduler.running is False


async def test_get_job_returns_none_for_unknown_id():
    scheduler = Scheduler()
    assert scheduler.get_job("nope") is None
