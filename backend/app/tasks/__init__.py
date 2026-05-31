"""Background task package: the scheduler adapter and the analysis job.

Exposes the :class:`Scheduler` lifecycle wrapper and the :class:`AnalysisJob`
that runs on it. Startup wiring (constructing the scheduler, registering the
job, starting/stopping with the app) lives in ``app.main``.
"""

from app.tasks.analysis_job import AnalysisJob, AnalysisPipeline, pipeline_not_configured
from app.tasks.scheduler import Scheduler

__all__ = [
    "AnalysisJob",
    "AnalysisPipeline",
    "Scheduler",
    "pipeline_not_configured",
]
