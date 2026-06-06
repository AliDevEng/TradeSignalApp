"""The calendar controller — read-side business logic for economic events.

A request-scoped *query* service (like the signal/pair controllers): it asks the
configured :class:`EconomicCalendarProvider` for the upcoming high-impact events
in a window and maps them onto the wire schema, keeping the view free of any
service import. The provider is resolved off ``app.state`` (constructed once in
the lifespan), so a disabled calendar is the null provider and this simply
reports ``enabled=False`` with no events — the endpoint always exists.

Layering: imports services (calendar) + schemas only; never ``app.views`` or
``fastapi``. A provider failure raises an :class:`EconomicCalendarError` (a
``ServiceError``), which the central error layer maps to a retryable ``503`` —
exactly like a market-data outage.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.schemas.calendar import CalendarResponse, EconomicEventResponse
from app.services.calendar import EconomicCalendarProvider, EconomicEvent


def _utcnow() -> datetime:
    """Timezone-aware UTC now. Injected so tests can pin the window."""
    return datetime.now(UTC)


class CalendarController:
    """Serves the upcoming-events read for the frontend news banner."""

    def __init__(
        self,
        *,
        calendar: EconomicCalendarProvider,
        enabled: bool,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._calendar = calendar
        self._enabled = enabled
        self._clock = clock

    async def get_upcoming(self, *, within_hours: int) -> CalendarResponse:
        """Upcoming high-impact events within ``within_hours`` of now.

        When the calendar is disabled the provider is the null one, so this
        returns ``enabled=False`` with an empty list — the behaviour the frontend
        treats as "no banner".
        """
        now = self._clock()
        events = await self._calendar.upcoming(within=timedelta(hours=within_hours), now=now)
        return CalendarResponse(
            enabled=self._enabled,
            within_hours=within_hours,
            events=[self._to_response(event) for event in events],
        )

    @staticmethod
    def _to_response(event: EconomicEvent) -> EconomicEventResponse:
        return EconomicEventResponse(
            title=event.title,
            currency=event.currency,
            impact=event.impact,
            scheduled_at=event.scheduled_at,
        )
