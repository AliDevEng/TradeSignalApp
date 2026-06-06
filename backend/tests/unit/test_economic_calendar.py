"""Unit tests for the economic-calendar providers + factory."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from app.config import Settings
from app.services.calendar import (
    EconomicCalendarError,
    EconomicEvent,
    NullEconomicCalendarProvider,
    StaticEconomicCalendarProvider,
    build_economic_calendar_provider,
)

_NOW = datetime(2026, 6, 6, 12, 0, tzinfo=UTC)


def _event(minutes_from_now: int, *, impact: str = "high", currency: str = "USD") -> EconomicEvent:
    return EconomicEvent(
        title="CPI",
        currency=currency,
        impact=impact,
        scheduled_at=_NOW + timedelta(minutes=minutes_from_now),
    )


# ── EconomicEvent ─────────────────────────────────────────────────────────────


def test_event_requires_timezone_aware_datetime():
    with pytest.raises(EconomicCalendarError, match="timezone-aware"):
        EconomicEvent(title="CPI", currency="USD", impact="high", scheduled_at=datetime(2026, 6, 6))


def test_event_affects_matches_currency_in_symbol():
    event = _event(30, currency="USD")
    assert event.affects("XAUUSD")
    assert event.affects("EURUSD")
    assert not event.affects("EURGBP")


def test_event_high_impact_flag():
    assert _event(30, impact="high").is_high_impact
    assert not _event(30, impact="medium").is_high_impact


# ── NullEconomicCalendarProvider ──────────────────────────────────────────────


async def test_null_provider_reports_no_events():
    provider = NullEconomicCalendarProvider()
    assert await provider.upcoming(within=timedelta(hours=1), now=_NOW) == []
    await provider.aclose()


# ── StaticEconomicCalendarProvider ────────────────────────────────────────────


async def test_static_provider_filters_to_the_window():
    provider = StaticEconomicCalendarProvider(
        [_event(30), _event(120), _event(-30)]  # in-window, out-of-window, past
    )
    upcoming = await provider.upcoming(within=timedelta(hours=1), now=_NOW)
    assert len(upcoming) == 1
    assert upcoming[0].scheduled_at == _NOW + timedelta(minutes=30)


async def test_static_provider_orders_soonest_first():
    provider = StaticEconomicCalendarProvider([_event(50), _event(10), _event(30)])
    upcoming = await provider.upcoming(within=timedelta(hours=2), now=_NOW)
    assert [e.scheduled_at for e in upcoming] == [
        _NOW + timedelta(minutes=10),
        _NOW + timedelta(minutes=30),
        _NOW + timedelta(minutes=50),
    ]


def test_parse_events_round_trips_json():
    raw = json.dumps(
        [{"title": "FOMC", "currency": "USD", "impact": "high", "scheduled_at": _NOW.isoformat()}]
    )
    events = StaticEconomicCalendarProvider.parse_events(raw)
    assert len(events) == 1
    assert events[0].title == "FOMC"
    assert events[0].scheduled_at == _NOW


def test_parse_events_empty_string_is_no_events():
    assert StaticEconomicCalendarProvider.parse_events("  ") == []


def test_parse_events_rejects_malformed_json():
    with pytest.raises(EconomicCalendarError, match="not valid JSON"):
        StaticEconomicCalendarProvider.parse_events("{not json")


def test_parse_events_rejects_missing_fields():
    with pytest.raises(EconomicCalendarError, match="invalid calendar event"):
        StaticEconomicCalendarProvider.parse_events('[{"title": "x"}]')


# ── Factory ───────────────────────────────────────────────────────────────────


def _settings(**overrides) -> Settings:
    base = {
        "database_url": "postgresql+asyncpg://u:p@localhost/db",
        "ai_api_key": "k",
        "twelve_data_api_key": "k",
    }
    base.update(overrides)
    return Settings(**base, _env_file=None)


def test_factory_returns_null_when_disabled():
    provider = build_economic_calendar_provider(_settings(economic_calendar_enabled=False))
    assert isinstance(provider, NullEconomicCalendarProvider)


def test_factory_returns_static_when_enabled():
    raw = json.dumps(
        [{"title": "CPI", "currency": "USD", "impact": "high", "scheduled_at": _NOW.isoformat()}]
    )
    provider = build_economic_calendar_provider(
        _settings(economic_calendar_enabled=True, economic_calendar_events_json=raw)
    )
    assert isinstance(provider, StaticEconomicCalendarProvider)
