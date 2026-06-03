"""The scheduled outcome job — a resilient wrapper around the outcome sweep.

Mirrors :class:`~app.tasks.analysis_job.AnalysisJob` exactly: it owns the
operational contract (error containment + observability) and knows nothing about
what the sweep does. The *business* half — fetch candles → evaluate open signals
→ persist outcomes — is the :class:`~app.controllers.OutcomeController`.

The two jobs are kept as separate small classes rather than one generic wrapper
because they log under distinct names and run on distinct cadences; collapsing
them would trade a few lines of duplication for a muddier operational story in
the logs.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from time import perf_counter

logger = logging.getLogger(__name__)

# The sweep the job drives — the outcome controller's ``run_scheduled`` in
# production. Typed structurally so the job stays decoupled from the controller.
OutcomePipeline = Callable[[], Awaitable[None]]


class OutcomeJob:
    """Adapts an :data:`OutcomePipeline` into a scheduler-safe coroutine."""

    def __init__(self, pipeline: OutcomePipeline, *, name: str = "scheduled-outcomes") -> None:
        self._pipeline = pipeline
        self._name = name

    async def run(self) -> None:
        """Entry point registered with the scheduler. Never raises.

        An unhandled error in one sweep must not propagate into APScheduler's
        executor and silence all future runs, so it is logged with its traceback
        and swallowed — the next interval still fires.
        """
        started = perf_counter()
        logger.info("Outcome cycle '%s' starting", self._name)
        try:
            await self._pipeline()
        except Exception:
            elapsed = perf_counter() - started
            logger.exception("Outcome cycle '%s' failed after %.2fs", self._name, elapsed)
        else:
            elapsed = perf_counter() - started
            logger.info("Outcome cycle '%s' completed in %.2fs", self._name, elapsed)
