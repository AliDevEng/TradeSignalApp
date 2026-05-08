"""Persistence-layer query orchestration.

A repository encapsulates one ORM model's read/write contract behind
a narrow, testable surface. Controllers depend on repos (never on raw
``select`` / ``Session`` calls) so query churn is contained to a
single file when the schema evolves.

Transaction boundaries live with the controller, not the repository —
repos stage work on the session but never commit. That separation is
what lets a controller batch multiple repository calls into one
atomic unit of work.
"""

from app.database.repository.analysis_run_repo import AnalysisRunRepository
from app.database.repository.base import BaseRepository
from app.database.repository.pair_repo import PairRepository
from app.database.repository.signal_repo import SignalRepository

__all__ = [
    "AnalysisRunRepository",
    "BaseRepository",
    "PairRepository",
    "SignalRepository",
]
