"""Controllers — business-logic orchestration (the C in MVC).

A controller owns a unit of work: it composes services and repositories,
decides transaction boundaries, and translates between the persistence/service
layers and the wire schemas the views speak. It may import services,
repositories, models, schemas and config; it must never import ``app.views`` or
``fastapi`` (see the layering table in ``backend/README.md``). That keeps the
business logic testable without standing up the web framework.

Two complementary shapes live here: the :class:`AnalysisController` is a
background *command* orchestrator that owns its own database sessions, while the
:class:`SignalController` is a request-scoped *query* service that borrows the
request's session. Controllers return the carriers in ``results`` and signal
failures with the exceptions in ``exceptions`` — both transport-agnostic, so the
view layer owns the mapping to HTTP.
"""

from app.controllers.analysis_controller import AnalysisController
from app.controllers.analysis_run_controller import AnalysisRunController
from app.controllers.calendar_controller import CalendarController
from app.controllers.exceptions import ControllerError, ResourceNotFoundError
from app.controllers.outcome_controller import OutcomeController, OutcomeRunSummary
from app.controllers.pair_controller import PairController
from app.controllers.performance_controller import PerformanceController
from app.controllers.results import Page
from app.controllers.risk_controller import RiskController
from app.controllers.signal_controller import SignalController

__all__ = [
    "AnalysisController",
    "AnalysisRunController",
    "CalendarController",
    "ControllerError",
    "OutcomeController",
    "OutcomeRunSummary",
    "Page",
    "PairController",
    "PerformanceController",
    "ResourceNotFoundError",
    "RiskController",
    "SignalController",
]
