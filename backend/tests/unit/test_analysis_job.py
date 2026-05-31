"""Unit tests for the scheduled analysis job wrapper."""

from __future__ import annotations

from app.tasks import AnalysisJob, pipeline_not_configured


async def test_run_invokes_pipeline_once():
    calls = {"n": 0}

    async def pipeline() -> None:
        calls["n"] += 1

    await AnalysisJob(pipeline).run()
    assert calls["n"] == 1


async def test_run_swallows_pipeline_exceptions():
    """A crashing cycle must not propagate — that would kill the schedule."""

    async def boom() -> None:
        raise RuntimeError("pipeline blew up")

    # The contract is "never raises"; reaching the assert proves it held.
    await AnalysisJob(boom).run()


async def test_placeholder_pipeline_is_a_safe_noop():
    await pipeline_not_configured()
