"""Repository for the ``pairs`` lookup table.

Pairs are short-lived to write (they're added once when an instrument
is enabled) and frequently read in the analysis pipeline. The query
surface here is intentionally thin — symbol lookups, the active-set
projection, and the seeding upsert. Anything more elaborate (joins
against signals, etc.) lives in the consumer that needs it.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database.repository.base import BaseRepository
from app.models import Pair


class PairRepository(BaseRepository[Pair]):
    model = Pair

    async def get_by_symbol(self, symbol: str) -> Pair | None:
        """Resolve a pair by its trading symbol (case-insensitive in).

        Symbols are normalised to upper-case at the config layer
        (``Settings._require_pairs``), so a caller passing the raw
        config value always hits the unique index. We still upper-case
        defensively here so ad-hoc callers (debug shells, scripts)
        don't have to remember the convention.
        """
        stmt = select(Pair).where(Pair.symbol == symbol.upper())
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def list_active(self) -> Sequence[Pair]:
        """All pairs currently flagged for trading, ordered by symbol.

        Symbol-ordered output keeps API responses deterministic without
        the consumer having to sort. ``is_active`` is a soft-disable
        flag — disabled pairs stay in the table to preserve referential
        integrity with historical signals.
        """
        stmt = select(Pair).where(Pair.is_active.is_(True)).order_by(Pair.symbol)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_all(self) -> Sequence[Pair]:
        """Every pair, active or not, ordered by symbol."""
        stmt = select(Pair).order_by(Pair.symbol)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def upsert_by_symbol(
        self,
        *,
        symbol: str,
        base_currency: str,
        quote_currency: str,
        display_name: str | None = None,
        is_active: bool = True,
    ) -> None:
        """Idempotent insert keyed on ``symbol``.

        Used by the ``ACTIVE_PAIRS`` bootstrap on startup: every entry
        listed in config must exist as a row, but re-running the
        bootstrap on an already-seeded database must not raise. We use
        Postgres' native ``ON CONFLICT DO UPDATE`` so the operation
        round-trips once instead of doing a SELECT-then-INSERT race.

        Currency code metadata is refreshed on conflict (the symbol
        unique constraint is the conflict target) so a corrected
        ``base_currency`` in code propagates without manual SQL.

        ``is_active`` is *not* refreshed on conflict — once an
        operator has manually disabled a pair via the admin path, a
        bootstrap run must not silently re-enable it.
        """
        stmt = pg_insert(Pair).values(
            symbol=symbol.upper(),
            base_currency=base_currency.upper(),
            quote_currency=quote_currency.upper(),
            display_name=display_name,
            is_active=is_active,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Pair.symbol],
            set_={
                "base_currency": stmt.excluded.base_currency,
                "quote_currency": stmt.excluded.quote_currency,
                "display_name": stmt.excluded.display_name,
            },
        )
        await self._session.execute(stmt)
