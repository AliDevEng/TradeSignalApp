"""SQLAlchemy ORM models.

Re-exporting every model here serves two purposes:

1. Public callers (controllers, repositories, tests) get a single
   import path: ``from app.models import Pair, Signal, AnalysisRun``.
2. Importing ``app.models`` registers every table on
   ``Base.metadata`` as a side effect — that registry is what Alembic
   autogenerate scans. If a model is added in a new file but not
   re-exported here, autogenerate will silently miss it. Keeping this
   list authoritative is the contract that prevents that.

Order matters: `pair` and `analysis_run` are imported before `signal`
so that the foreign-key targets exist on the metadata registry before
the dependent table is loaded. Cycles are avoided entirely by guarding
back-reference type hints with ``TYPE_CHECKING``.
"""

from app.models.analysis_run import (
    AnalysisRun,
    AnalysisRunStatus,
    AnalysisRunTrigger,
)
from app.models.base import Base, TimestampMixin
from app.models.pair import Pair
from app.models.signal import Signal, SignalDirection, SignalType

__all__ = [
    "AnalysisRun",
    "AnalysisRunStatus",
    "AnalysisRunTrigger",
    "Base",
    "Pair",
    "Signal",
    "SignalDirection",
    "SignalType",
    "TimestampMixin",
]
