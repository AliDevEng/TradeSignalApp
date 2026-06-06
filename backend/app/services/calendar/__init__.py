"""Economic-calendar awareness — the news that actually moves Gold and FX.

Gold gets repriced violently around high-impact USD releases (CPI, FOMC, NFP);
trading blind into them is one of the fastest ways an otherwise-good signal turns
into a loss. This package supplies the *upcoming high-impact events* the prompt
and the quality gate use to widen caution / veto a trade near a release.

The shape mirrors :mod:`app.services.market_data`: an
:class:`EconomicCalendarProvider` ABC behind a factory, so a static
config-driven source today can be swapped for a live HTTP feed later without the
controller changing. Off by default (``economic_calendar_enabled = false``),
where it behaves exactly as if there were no events.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.calendar.base import (
    EconomicCalendarError,
    EconomicCalendarProvider,
    EconomicEvent,
)
from app.services.calendar.providers import (
    NullEconomicCalendarProvider,
    StaticEconomicCalendarProvider,
)

if TYPE_CHECKING:
    from app.config import Settings

__all__ = [
    "EconomicCalendarError",
    "EconomicCalendarProvider",
    "EconomicEvent",
    "NullEconomicCalendarProvider",
    "StaticEconomicCalendarProvider",
    "build_economic_calendar_provider",
]


def build_economic_calendar_provider(settings: Settings) -> EconomicCalendarProvider:
    """Construct the calendar provider selected by configuration.

    Disabled (the default) → a :class:`NullEconomicCalendarProvider` that always
    reports no events, so every downstream consumer behaves exactly as before the
    feature existed. Enabled → a :class:`StaticEconomicCalendarProvider` seeded
    from the operator-supplied event list. The single seam a future live HTTP
    provider slots into.
    """
    if not settings.economic_calendar_enabled:
        return NullEconomicCalendarProvider()
    events = StaticEconomicCalendarProvider.parse_events(settings.economic_calendar_events_json)
    return StaticEconomicCalendarProvider(events)
