"""Unit tests for the scheduled outcome job wrapper."""

from __future__ import annotations

from app.tasks import OutcomeJob


async def test_run_invokes_pipeline_once():
    calls = {"n": 0}

    async def pipeline() -> None:
        calls["n"] += 1

    await OutcomeJob(pipeline).run()
    assert calls["n"] == 1


async def test_run_swallows_pipeline_exceptions():
    """A crashing sweep must not propagate — that would kill the schedule."""

    async def boom() -> None:
        raise RuntimeError("sweep blew up")

    # The contract is "never raises"; reaching the assert proves it held.
    await OutcomeJob(boom).run()
