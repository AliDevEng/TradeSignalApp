"""The pair controller — read-side business logic for trading pairs.

Pairs are a small, enumerable lookup set (one row per instrument), so this
controller deliberately offers no pagination — listing them whole is cheaper
than the round trips paging would add. Like the signal controller it is
request-scoped: it borrows the request's session through an injected
``PairRepository`` and maps the ORM ``Pair`` onto the wire
:class:`PairResponse`, keeping the view free of any persistence import.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.controllers.exceptions import ResourceNotFoundError
from app.database.repository import PairRepository
from app.models import Pair
from app.schemas.pair import PairResponse


class PairController:
    """Serves the pair list and single-pair lookups."""

    def __init__(self, *, pairs: PairRepository) -> None:
        self._pairs = pairs

    async def list_pairs(self, *, include_inactive: bool = False) -> list[PairResponse]:
        """All pairs, symbol-ordered. By default only those active for trading.

        ``include_inactive`` surfaces soft-disabled pairs too — useful for an
        admin view that needs to see the full set, not just the tradable subset.
        """
        rows: Sequence[Pair] = (
            await self._pairs.list_all() if include_inactive else await self._pairs.list_active()
        )
        return [self._to_response(pair) for pair in rows]

    async def get_pair(self, symbol: str) -> PairResponse:
        """A single pair by symbol, or :class:`ResourceNotFoundError` if absent."""
        pair = await self._pairs.get_by_symbol(symbol)
        if pair is None:
            raise ResourceNotFoundError("pair", symbol)
        return self._to_response(pair)

    @staticmethod
    def _to_response(pair: Pair) -> PairResponse:
        return PairResponse(
            id=pair.id,
            symbol=pair.symbol,
            base_currency=pair.base_currency,
            quote_currency=pair.quote_currency,
            display_name=pair.display_name,
            is_active=pair.is_active,
        )
