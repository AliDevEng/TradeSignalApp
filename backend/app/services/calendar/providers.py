"""Concrete economic-calendar providers: a no-op and a static config-driven one.

``NullEconomicCalendarProvider`` is the disabled default — it reports no events,
so every consumer behaves as if the feature did not exist.
``StaticEconomicCalendarProvider`` serves an operator-supplied event list (parsed
from a JSON config string), which is enough to exercise the whole news-aware path
end-to-end and is the seam a live HTTP feed later replaces.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from app.services.calendar.base import (
    EconomicCalendarError,
    EconomicCalendarProvider,
    EconomicEvent,
)


class NullEconomicCalendarProvider(EconomicCalendarProvider):
    """Always reports no events — the behaviour when the feature is disabled."""

    provider_name = "null"

    async def upcoming(self, *, within: timedelta, now: datetime) -> list[EconomicEvent]:
        return []

    async def aclose(self) -> None:
        return None


class StaticEconomicCalendarProvider(EconomicCalendarProvider):
    """Serves a fixed, in-memory event list (seeded from config).

    Deterministic and network-free, so it both powers a real deployment with a
    hand-maintained event list and makes the news-aware pipeline fully testable.
    """

    provider_name = "static"

    def __init__(self, events: list[EconomicEvent]) -> None:
        # Store soonest-first so ``upcoming`` is a single bounded slice.
        self._events = sorted(events, key=lambda e: e.scheduled_at)

    async def upcoming(self, *, within: timedelta, now: datetime) -> list[EconomicEvent]:
        horizon = now + within
        return [event for event in self._events if now <= event.scheduled_at < horizon]

    async def aclose(self) -> None:
        return None

    @staticmethod
    def parse_events(raw: str) -> list[EconomicEvent]:
        """Parse the ``economic_calendar_events_json`` config into events.

        Expects a JSON array of objects with ``title``, ``currency``, ``impact``
        and an ISO-8601 ``scheduled_at``. An empty/blank string is no events; a
        malformed payload raises :class:`EconomicCalendarError` so a typo fails
        loudly at startup rather than silently disabling news awareness.
        """
        text = raw.strip()
        if not text:
            return []
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise EconomicCalendarError(
                f"economic_calendar_events_json is not valid JSON: {exc}"
            ) from exc
        if not isinstance(payload, list):
            raise EconomicCalendarError("economic_calendar_events_json must be a JSON array")
        events: list[EconomicEvent] = []
        for item in payload:
            if not isinstance(item, dict):
                raise EconomicCalendarError("each calendar event must be a JSON object")
            try:
                scheduled_at = datetime.fromisoformat(str(item["scheduled_at"]))
                events.append(
                    EconomicEvent(
                        title=str(item["title"]),
                        currency=str(item["currency"]),
                        impact=str(item["impact"]),
                        scheduled_at=scheduled_at,
                    )
                )
            except (KeyError, ValueError) as exc:
                raise EconomicCalendarError(f"invalid calendar event {item!r}: {exc}") from exc
        return events
