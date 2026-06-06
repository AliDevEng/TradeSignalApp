"""Economic-calendar domain contract: the ``EconomicEvent`` value object + ABC.

Provider-agnostic by design, exactly like the market-data contract: ``EconomicEvent``
is the single shape the rest of the pipeline speaks, so a static config source can
be swapped for a live feed by adding one :class:`EconomicCalendarProvider`
implementation with nothing downstream changing.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.services import ServiceError


class EconomicCalendarError(ServiceError):
    """Base for every economic-calendar failure (parse, fetch, …)."""


@dataclass(frozen=True, slots=True)
class EconomicEvent:
    """A single scheduled macro release, normalised across sources.

    ``currency`` is the ISO code the event prices (e.g. ``"USD"``); ``impact`` is
    a coarse ``"high"``/``"medium"``/``"low"``. ``scheduled_at`` is timezone-aware
    UTC — a naive datetime is rejected so a window comparison can never silently
    mix zones.
    """

    title: str
    currency: str
    impact: str
    scheduled_at: datetime

    def __post_init__(self) -> None:
        if self.scheduled_at.tzinfo is None:
            raise EconomicCalendarError(f"event {self.title!r} scheduled_at must be timezone-aware")

    @property
    def is_high_impact(self) -> bool:
        return self.impact.lower() == "high"

    def affects(self, symbol: str) -> bool:
        """Whether this event is relevant to a trading ``symbol``.

        A currency is relevant when its code appears in the pair symbol
        (``USD`` in ``XAUUSD``/``EURUSD``), which is the common case for the
        USD-driven releases that move Gold and the majors.
        """
        return self.currency.upper() in symbol.upper()

    def label(self) -> str:
        """Compact human label for prompts and veto reasons."""
        return f"{self.currency} {self.title} ({self.impact})"


class EconomicCalendarProvider(abc.ABC):
    """Async source of upcoming scheduled economic events."""

    #: Stable identifier for logs/health, mirroring the other provider ABCs.
    provider_name: str

    @abc.abstractmethod
    async def upcoming(
        self,
        *,
        within: timedelta,
        now: datetime,
    ) -> list[EconomicEvent]:
        """Events scheduled in the half-open window ``[now, now + within)``.

        Ordered soonest-first. Implementations raise an
        :class:`EconomicCalendarError` subclass on failure — never a raw
        transport/parse exception — so the pipeline can isolate a calendar
        outage exactly like a market-data one.
        """

    @abc.abstractmethod
    async def aclose(self) -> None:
        """Release any held resources. Must be idempotent."""
