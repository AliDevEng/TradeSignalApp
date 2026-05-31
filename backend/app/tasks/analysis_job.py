"""The scheduled analysis job — a resilient wrapper around the pipeline.

This is the *scheduling* half of the analysis feature (Iteration 3). The
*business* half — fetch candles → compute indicators → ask the AI → persist
signals and the ``AnalysisRun`` ledger — is the analysis controller, which
lands in Iteration 4. To keep that boundary clean, the job depends only on a
``pipeline`` callable; it does not know what the pipeline does.

What the job *does* own is the operational contract every scheduled task
needs and is easy to get wrong:

- **Error containment.** An unhandled exception in one cycle must never kill
  the scheduler thread and silence all future runs. The job logs and
  swallows, so the next interval still fires. (Per-pair failures and
  recording the run as failed are the pipeline's concern; this is the
  last-resort guard.)
- **Observability.** Start, duration, and outcome are logged so a stuck or
  slow cycle is visible without attaching a debugger.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from time import perf_counter

logger = logging.getLogger(__name__)

# The pipeline the job drives. Iteration 4 supplies the real implementation
# (the analysis controller bound to a DB session + the services); until then
# `pipeline_not_configured` stands in.
AnalysisPipeline = Callable[[], Awaitable[None]]


async def pipeline_not_configured() -> None:
    """Placeholder pipeline used until the Iteration-4 controller is wired.

    Deliberately a no-op that announces itself: the scheduler is proven to
    fire on cadence in Iteration 3, and the log line makes it obvious that no
    signals are being produced yet — far better than a silent no-op that
    could be mistaken for "running but finding nothing".
    """
    logger.warning(
        "Analysis pipeline not configured — the Iteration 4 controller will "
        "replace this placeholder. No signals generated this cycle."
    )


class AnalysisJob:
    """Adapts an :data:`AnalysisPipeline` into a scheduler-safe coroutine."""

    def __init__(self, pipeline: AnalysisPipeline, *, name: str = "scheduled-analysis") -> None:
        self._pipeline = pipeline
        self._name = name

    async def run(self) -> None:
        """Entry point registered with the scheduler. Never raises."""
        started = perf_counter()
        logger.info("Analysis cycle '%s' starting", self._name)
        try:
            await self._pipeline()
        except Exception:
            # Swallow on purpose: re-raising would propagate into APScheduler's
            # executor and, worse, a bug could stop the whole schedule. We log
            # with the traceback so nothing is lost.
            elapsed = perf_counter() - started
            logger.exception("Analysis cycle '%s' failed after %.2fs", self._name, elapsed)
        else:
            elapsed = perf_counter() - started
            logger.info("Analysis cycle '%s' completed in %.2fs", self._name, elapsed)
