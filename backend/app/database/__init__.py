"""Database adapter — async SQLAlchemy engine and session lifecycle.

Public surface kept narrow on purpose: callers depend on `Database` for
lifecycle ops and pull request-scoped sessions through the FastAPI
dependencies in `app.dependencies` (`DatabaseDep`, `DBSessionDep`).
"""

from app.database.connection import Database

__all__ = ["Database"]
