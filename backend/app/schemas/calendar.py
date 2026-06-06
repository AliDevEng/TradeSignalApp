"""Wire-format models for the economic-calendar endpoint.

Transport-agnostic like every schema (pydantic + stdlib only): the ORM/service
``EconomicEvent`` is mapped onto :class:`EconomicEventResponse` in the controller,
never here, so a change to the service value object can't silently reshape the
public contract.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EconomicEventResponse(BaseModel):
    """A single upcoming high-impact macro release."""

    title: str
    currency: str
    impact: str
    scheduled_at: datetime


class CalendarResponse(BaseModel):
    """Upcoming events plus the feature's state, for the frontend banner.

    ``enabled`` mirrors ``ECONOMIC_CALENDAR_ENABLED`` so the UI can distinguish
    "the feature is off" from "it's on but nothing is scheduled" — both return an
    empty ``events`` list, but only the first should hide the banner entirely.
    """

    enabled: bool
    within_hours: int = Field(ge=1)
    events: list[EconomicEventResponse]
