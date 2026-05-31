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
    confidence: float = Field(ge=0.0, le=1.0)

    entry_price: Decimal
    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None

    timeframe: str
    rationale: str | None = None
    # The raw indicator values that fed the AI prompt at generation time —
    # surfaced verbatim so the frontend can explain *why* a signal exists.
    indicators_snapshot: dict[str, Any] | None = None

    generated_at: datetime
    expires_at: datetime | None = None

    ai_provider: str | None = None
    ai_model: str | None = None
