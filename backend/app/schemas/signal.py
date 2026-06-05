"""Wire-format models for signals — the shape the API surfaces to the frontend.

This module is transport-agnostic and deliberately decoupled from persistence:
per the layering table in ``backend/README.md``, schemas may import ``pydantic``
and stdlib only — never ``sqlalchemy``, the ORM models, or the service layer.
That is why ``direction`` is a plain ``Literal`` here rather than a reuse of the
ORM ``SignalDirection`` enum, and why the ORM→wire mapping lives in the
controller, not in a ``from_attributes`` hook on this model: keeping the
translation explicit (and in the layer allowed to see both sides) is what stops
a stray ``signals`` column change from silently reshaping the public contract.

Money fields are ``Decimal``. They serialise to JSON **strings**, not numbers —
the same "never float for prices" discipline the storage layer keeps (see the
``Numeric`` columns on the ``Signal`` model). Clients parse them to a number at
the display boundary, mirroring how the backend only drops to ``float`` at the
pandas boundary in the indicator calculator.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

SignalDirection = Literal["buy", "sell", "neutral"]
SignalType = Literal["scalp", "swing"]
SignalOutcome = Literal[
    "open",
    "hit_tp1",
    "hit_tp2",
    "hit_tp3",
    "hit_sl",
    "expired",
    "cancelled",
]

# Coarse, lifecycle-derived status the browse UI filters by (computed from
# direction + expiry, not stored): a directional, unexpired signal is "active";
# a neutral one is "watchlist"; a lapsed one is "expired".
SignalStatusFilter = Literal["active", "watchlist", "expired"]
# Outcome grouped into result categories for filtering (a "win" is any
# take-profit rung, a "loss" is the stop, "expired" covers expired/cancelled).
SignalResultFilter = Literal["open", "win", "loss", "expired"]
# Server-side ordering for the signal list.
SignalSort = Literal["confidence", "newest", "symbol"]


class SignalResponse(BaseModel):
    """A persisted trade signal as returned by the read endpoints.

    ``pair_symbol`` is denormalised onto the response so the frontend can render
    a signal without a second round trip to resolve the pair — the controller
    fills it from the eagerly-loaded ``Pair`` while the session is still open.
    """

    id: uuid.UUID
    pair_id: int
    pair_symbol: str | None = None
    analysis_run_id: uuid.UUID | None = None

    direction: SignalDirection
    # Trade horizon this signal is framed on. A run emits one of each style per
    # pair (scalp = short-term/lower TF, swing = higher TF).
    signal_type: SignalType
    confidence: float = Field(ge=0.0, le=1.0)

    entry_price: Decimal
    stop_loss: Decimal | None = None
    # The take-profit ladder, ordered TP1..TP3. ``take_profit`` is the primary
    # target (TP1); the secondary scale-out targets are nullable because a
    # signal may carry fewer than three.
    take_profit: Decimal | None = None
    take_profit_2: Decimal | None = None
    take_profit_3: Decimal | None = None

    timeframe: str
    rationale: str | None = None
    # The raw indicator values that fed the AI prompt at generation time —
    # surfaced verbatim so the frontend can explain *why* a signal exists.
    indicators_snapshot: dict[str, Any] | None = None

    generated_at: datetime
    expires_at: datetime | None = None

    ai_provider: str | None = None
    ai_model: str | None = None

    # ── Outcome tracking (Iteration 7) ────────────────────────────────────
    # What price did after the signal was generated. ``outcome`` is ``open``
    # until the evaluator finds a terminal result; ``realized_r`` (in R
    # multiples) and ``closed_at`` are populated only once it closes.
    outcome: SignalOutcome = "open"
    realized_r: Decimal | None = None
    closed_at: datetime | None = None
