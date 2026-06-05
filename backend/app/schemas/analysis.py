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

# The coarse pipeline state the UI cares about, derived from the scheduler and
# the latest run: a cycle is in flight, the schedule is idle between runs, or
# the scheduler is switched off entirely.
PipelineStateLiteral = Literal["idle", "running", "disabled"]


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


class PipelineStatusResponse(BaseModel):
    """Live status of the analysis pipeline for the dashboard "next signal" UI.

    Combines two sources of truth: the scheduler (when the next cycle fires)
    and the run ledger (whether one is in flight right now, plus context from
    the last completed run). The frontend renders a "processing" banner while
    ``state == "running"`` and a countdown to ``next_run_at`` otherwise.
    """

    state: PipelineStateLiteral
    interval_minutes: int
    #: When the next scheduled cycle fires. ``None`` if the scheduler is off or
    #: has no upcoming run; the UI then hides the countdown.
    next_run_at: datetime | None = None
    #: The most-recent run for context (status, finished_at, signal counts).
    last_run: AnalysisRunResponse | None = None


class AnalysisRunAccepted(BaseModel):
    """Acknowledgement for a manually triggered run (HTTP 202).

    The run executes asynchronously after the response is sent, so there is no
    completed run to return yet — the client polls ``GET /analysis/runs`` to
    observe it. A static, typed ack keeps the contract explicit rather than
    returning a bare message string.
    """

    status: Literal["accepted"] = "accepted"
    detail: str = "Analysis run scheduled; poll /analysis/runs to track it."
