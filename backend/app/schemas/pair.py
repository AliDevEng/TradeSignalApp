"""Wire-format model for trading pairs.

Transport-agnostic and persistence-free, like every module under ``schemas/``:
pydantic + stdlib only (see the layering table in ``backend/README.md``). The
ORM→wire mapping lives in the pair controller, which is the layer allowed to see
both sides.
"""

from __future__ import annotations

from pydantic import BaseModel


class PairResponse(BaseModel):
    """A tradable instrument as surfaced by the API.

    ``is_active`` is included so the frontend can distinguish a pair that is
    temporarily disabled (kept for historical signal integrity) from one it
    should offer for new analysis.
    """

    id: int
    symbol: str
    base_currency: str
    quote_currency: str
    display_name: str | None = None
    is_active: bool
