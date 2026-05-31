"""Controllers — business-logic orchestration (the C in MVC).

A controller owns a unit of work: it composes services and repositories,
decides transaction boundaries, and translates between the persistence/service
layers and the wire schemas the views speak. It may import services,
repositories, models, schemas and config; it must never import ``app.views`` or
``fastapi`` (see the layering table in ``backend/README.md``). That keeps the
business logic testable without standing up the web framework.
"""

from app.controllers.analysis_controller import AnalysisController

__all__ = ["AnalysisController"]
