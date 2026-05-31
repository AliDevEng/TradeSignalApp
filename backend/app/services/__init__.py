"""Service layer — external integrations and pure computation.

Layering contract (see the table in ``backend/README.md``): services may
import stdlib, third-party SDKs, and ``app.schemas``; they must never import
``app.views`` or ``app.controllers``. That one-way dependency is what keeps
the pipeline pieces unit-testable without spinning up FastAPI and lets the
Iteration-4 controller compose them freely.

Every failure a service raises derives from :class:`ServiceError`. The
controller that orchestrates the analysis pipeline therefore has a single,
predictable base to catch — it can record a run as failed without having to
know (or import) provider-specific exception types like ``httpx.HTTPError``
or ``anthropic.APIError``. Leaking those upward would couple the controller
to the very integrations the service layer exists to hide.
"""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for every error originating in the service layer."""
