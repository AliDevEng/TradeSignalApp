"""Unit tests for the read-side :class:`CalendarController`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.controllers.calendar_controller import CalendarController
from app.schemas.calendar import CalendarResponse
from app.services.calendar import (
    EconomicEvent,
    NullEconomicCalendarProvider,
    StaticEconomicCalendarProvider,
)

_NOW = datetime(2026, 6, 6, 12, 0, tzinfo=UTC)


def _event(minutes: int, *, currency: str = "USD", impact: str = "high") -> EconomicEvent:
    return EconomicEvent(
        title="CPI",
        currency=currency,
        impact=impact,
        scheduled_at=_NOW + timedelta(minutes=minutes),
    )


async def test_maps_events_within_window_and_reports_enabled():
    provider = StaticEconomicCalendarProvider([_event(30), _event(300)])  # one in 1h window
    controller = CalendarController(calendar=provider, enabled=True, clock=lambda: _NOW)

    report = await controller.get_upcoming(within_hours=1)

    assert isinstance(report, CalendarResponse)
    assert report.enabled is True
    assert report.within_hours == 1
    assert len(report.events) == 1
    assert report.events[0].title == "CPI"
    assert report.events[0].scheduled_at == _NOW + timedelta(minutes=30)


async def test_disabled_calendar_reports_no_events():
    controller = CalendarController(
        calendar=NullEconomicCalendarProvider(), enabled=False, clock=lambda: _NOW
    )

    report = await controller.get_upcoming(within_hours=24)

    assert report.enabled is False
    assert report.events == []


async def test_window_is_honoured():
    provider = StaticEconomicCalendarProvider([_event(30), _event(120)])
    controller = CalendarController(calendar=provider, enabled=True, clock=lambda: _NOW)

    # A 3-hour window now includes both events.
    report = await controller.get_upcoming(within_hours=3)
    assert len(report.events) == 2
