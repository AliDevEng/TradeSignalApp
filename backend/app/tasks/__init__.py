"""Background task package: the scheduler adapter and the analysis job.

Exposes the :class:`Scheduler` lifecycle wrapper and the :class:`AnalysisJob`
that runs on it. Startup wiring (constructing the scheduler, registering the
job, starting/stopping with the app) lives in ``app.main``.
"""

from app.tasks.analysis_job import AnalysisJob, AnalysisPipeline, pipeline_not_configured
from app.tasks.outcome_job import OutcomeJob, OutcomePipeline
from app.tasks.scheduler import Scheduler

#: Stable scheduler job ids. Defined here (not in ``app.main``) so the startup
#: wiring *and* read-side endpoints — e.g. ``GET /analysis/status`` querying the
#: next analysis fire time — reference the same ids without string drift.
ANALYSIS_JOB_ID = "analysis-cycle"
OUTCOME_JOB_ID = "outcome-cycle"

__all__ = [
    "ANALYSIS_JOB_ID",
    "OUTCOME_JOB_ID",
    "AnalysisJob",
    "AnalysisPipeline",
    "OutcomeJob",
    "OutcomePipeline",
    "Scheduler",
    "pipeline_not_configured",
]
