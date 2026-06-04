"""Wire-format models for analysis runs — the operator/observability surface.

An ``analysis_runs`` row is the ledger of one pipeline execution: when it ran,
what it processed, which provider produced its signals, and how it ended. These
models expose that for the "recent runs" dashboard and the manual-trigger
acknowledgement.

Pure pydantic + stdlib (no ORM import), so ``status`` and ``trigger`` are
``Literal`` mirrors of the ORM enums rather than the enums themselves. The
literal values are kept identical to ``AnalysisRunStatus`` / ``AnalysisRunTrigger``
on the model; the controller converts between the two at the boundary.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

# Mirrors of the ORM enums. Exposed as a query-filter type too, so the router
# gets validation + OpenAPI enum documentation for free.
AnalysisRunStatusLiteral = Literal["pending", "running", "success", "partial", "failed"]
AnalysisRunTriggerLiteral = Literal["scheduler", "manual"]


class AnalysisRunResponse(BaseModel):
    """A single pipeline run as surfaced by the API."""

    id: uuid.UUID
    status: AnalysisRunStatusLiteral
    trigger: AnalysisRunTriggerLiteral

    timeframe: str
    candle_count: int

    started_at: datetime
    finished_at: datetime | None = None

    pairs_processed: int
    pairs_failed: int

    ai_provider: str | None = None
    ai_model: str | None = None
    error_message: str | None = None

    # AI token usage + estimated cost for the run (Iteration 9). All nullable:
    # a provider may not report usage, and an unpriced model leaves cost undefined.
    # ``cost_usd`` is a ``Decimal`` and serialises to a JSON string, like every
    # money field in the API.
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: Decimal | None = None


class AnalysisRunAccepted(BaseModel):
    """Acknowledgement for a manually triggered run (HTTP 202).

    The run executes asynchronously after the response is sent, so there is no
    completed run to return yet — the client polls ``GET /analysis/runs`` to
    observe it. A static, typed ack keeps the contract explicit rather than
    returning a bare message string.
    """

    status: Literal["accepted"] = "accepted"
    detail: str = "Analysis run scheduled; poll /analysis/runs to track it."
