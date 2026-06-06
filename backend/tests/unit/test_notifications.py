"""Unit tests for the notifications subsystem (Iteration 11).

Three layers, each tested against the seam below it:
- :class:`NotificationPreferences` + :func:`render` — pure policy/formatting.
- :class:`TelegramNotifier` — driven by ``httpx.MockTransport`` (no network),
  asserting the Bot-API payload and error mapping.
- :class:`NotificationDispatcher` — end-to-end over a real :class:`EventBus`,
  asserting it honours preferences and isolates delivery failures.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
from app.services.events import Event, EventBus
from app.services.notifications import (
    NotificationDispatcher,
    NotificationError,
    NotificationMessage,
    NotificationPreferences,
    Notifier,
    NullNotifier,
    TelegramNotifier,
    render,
)


def _event(event_type, data, *, event_id=1) -> Event:
    from datetime import UTC, datetime

    return Event(id=event_id, type=event_type, at=datetime.now(UTC), data=data)


# ── Preferences (pure) ────────────────────────────────────────────────────────


def test_preferences_admit_confident_actionable_signal():
    prefs = NotificationPreferences(min_confidence=0.7)
    event = _event(
        "signal.created", {"signal_type": "scalp", "confidence": 0.8, "should_trade": True}
    )
    assert prefs.should_notify(event) is True


def test_preferences_reject_low_confidence():
    prefs = NotificationPreferences(min_confidence=0.7)
    event = _event(
        "signal.created", {"signal_type": "scalp", "confidence": 0.5, "should_trade": True}
    )
    assert prefs.should_notify(event) is False


def test_preferences_reject_non_actionable_when_only_actionable():
    prefs = NotificationPreferences(min_confidence=0.0, only_actionable=True)
    event = _event(
        "signal.created", {"signal_type": "scalp", "confidence": 0.9, "should_trade": False}
    )
    assert prefs.should_notify(event) is False


def test_preferences_allow_non_actionable_when_flag_off():
    prefs = NotificationPreferences(min_confidence=0.0, only_actionable=False)
    event = _event(
        "signal.created", {"signal_type": "scalp", "confidence": 0.9, "should_trade": False}
    )
    assert prefs.should_notify(event) is True


def test_preferences_filter_by_style():
    prefs = NotificationPreferences(min_confidence=0.0, signal_types=frozenset({"swing"}))
    scalp = _event(
        "signal.created", {"signal_type": "scalp", "confidence": 0.9, "should_trade": True}
    )
    swing = _event(
        "signal.created", {"signal_type": "swing", "confidence": 0.9, "should_trade": True}
    )
    assert prefs.should_notify(scalp) is False
    assert prefs.should_notify(swing) is True


def test_preferences_respect_event_toggles():
    no_created = NotificationPreferences(min_confidence=0.0, on_signal_created=False)
    no_closed = NotificationPreferences(on_signal_closed=False)
    created = _event(
        "signal.created", {"signal_type": "scalp", "confidence": 0.9, "should_trade": True}
    )
    closed = _event("signal.closed", {"signal_type": "scalp", "outcome": "hit_tp1"})
    assert no_created.should_notify(created) is False
    assert no_closed.should_notify(closed) is False


def test_preferences_never_notify_run_finished():
    prefs = NotificationPreferences(min_confidence=0.0)
    assert prefs.should_notify(_event("run.finished", {"status": "success"})) is False


# ── Rendering (pure) ──────────────────────────────────────────────────────────


def test_render_created_message():
    event = _event(
        "signal.created",
        {
            "signal_id": "abc",
            "pair": "XAUUSD",
            "direction": "buy",
            "signal_type": "scalp",
            "confidence": 0.82,
            "timeframe": "1h",
            "entry": "2345.6",
            "stop_loss": "2340.0",
            "take_profit": "2360.0",
        },
    )
    message = render(event)
    assert "BUY" in message.title
    assert "XAUUSD" in message.title
    assert "82% confidence" in message.body
    assert message.url == "/signals/abc"


def test_render_closed_message():
    event = _event(
        "signal.closed",
        {"signal_id": "xyz", "pair": "XAUUSD", "outcome": "hit_tp1", "realized_r": "1.50"},
    )
    message = render(event)
    assert "closed" in message.title.lower()
    assert "HIT TP1" in message.body
    assert "1.50R" in message.body
    assert message.url == "/signals/xyz"


def test_render_tolerates_partial_payload():
    message = render(_event("signal.created", {}))
    assert isinstance(message, NotificationMessage)
    assert message.title  # never empty


# ── NullNotifier ──────────────────────────────────────────────────────────────


async def test_null_notifier_is_inert():
    notifier = NullNotifier()
    await notifier.send(NotificationMessage(title="t", body="b"))
    await notifier.aclose()  # idempotent no-op


# ── TelegramNotifier (httpx MockTransport) ────────────────────────────────────


async def test_telegram_notifier_posts_expected_payload():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        import json as _json

        captured["body"] = _json.loads(request.content)
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    notifier = TelegramNotifier(bot_token="T0KEN", chat_id="123", client=client)
    try:
        await notifier.send(NotificationMessage(title="Title", body="Body", url="/signals/1"))
    finally:
        await notifier.aclose()

    assert captured["url"].endswith("/botT0KEN/sendMessage")
    assert captured["body"]["chat_id"] == "123"
    assert "Title" in captured["body"]["text"]
    assert captured["body"]["parse_mode"] == "HTML"


async def test_telegram_notifier_maps_api_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"ok": False, "description": "bad chat id"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    notifier = TelegramNotifier(bot_token="T", chat_id="1", client=client)
    try:
        with pytest.raises(NotificationError):
            await notifier.send(NotificationMessage(title="t", body="b"))
    finally:
        await notifier.aclose()


async def test_telegram_notifier_maps_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    notifier = TelegramNotifier(bot_token="T", chat_id="1", client=client)
    try:
        with pytest.raises(NotificationError):
            await notifier.send(NotificationMessage(title="t", body="b"))
    finally:
        await notifier.aclose()


def test_telegram_notifier_requires_credentials():
    with pytest.raises(NotificationError):
        TelegramNotifier(bot_token="", chat_id="1")
    with pytest.raises(NotificationError):
        TelegramNotifier(bot_token="T", chat_id="")


def test_telegram_escapes_html():
    notifier = TelegramNotifier(
        bot_token="T",
        chat_id="1",
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))),
    )
    payload = notifier._payload(NotificationMessage(title="A & B <x>", body="ok"))
    assert "&amp;" in payload["text"]
    assert "&lt;x&gt;" in payload["text"]


# ── Dispatcher (end-to-end over the bus) ──────────────────────────────────────


class _RecordingNotifier(Notifier):
    provider_name = "recording"

    def __init__(self, *, fail: bool = False) -> None:
        self.messages: list[NotificationMessage] = []
        self._fail = fail
        self.closed = False

    async def send(self, message: NotificationMessage) -> None:
        if self._fail:
            raise NotificationError("delivery failed")
        self.messages.append(message)

    async def aclose(self) -> None:
        self.closed = True


async def _wait_until(predicate, *, timeout: float = 1.0) -> None:
    async def _poll() -> None:
        while not predicate():
            await asyncio.sleep(0.005)

    await asyncio.wait_for(_poll(), timeout=timeout)


async def test_dispatcher_delivers_passing_events_and_skips_others():
    bus = EventBus()
    notifier = _RecordingNotifier()
    prefs = NotificationPreferences(min_confidence=0.7)
    dispatcher = NotificationDispatcher(bus=bus, notifier=notifier, preferences=prefs)
    dispatcher.start()
    try:
        # Passes: confident, actionable scalp.
        bus.publish(
            "signal.created",
            {
                "signal_id": "1",
                "signal_type": "scalp",
                "confidence": 0.9,
                "should_trade": True,
                "pair": "XAUUSD",
                "direction": "buy",
            },
        )
        # Filtered out: low confidence.
        bus.publish(
            "signal.created",
            {"signal_id": "2", "signal_type": "scalp", "confidence": 0.2, "should_trade": True},
        )
        # Filtered out: run.finished is never a push.
        bus.publish("run.finished", {"status": "success"})

        await _wait_until(lambda: len(notifier.messages) == 1)
        assert "XAUUSD" in notifier.messages[0].title
    finally:
        await dispatcher.stop()
    assert notifier.closed is True
    assert dispatcher.running is False


async def test_dispatcher_isolates_delivery_failures():
    bus = EventBus()
    notifier = _RecordingNotifier(fail=True)
    prefs = NotificationPreferences(min_confidence=0.0)
    dispatcher = NotificationDispatcher(bus=bus, notifier=notifier, preferences=prefs)
    dispatcher.start()
    try:
        bus.publish(
            "signal.closed",
            {
                "signal_id": "1",
                "signal_type": "scalp",
                "outcome": "hit_sl",
                "pair": "XAUUSD",
                "direction": "buy",
            },
        )
        # The loop must survive the failure and stay running.
        await asyncio.sleep(0.05)
        assert dispatcher.running is True
    finally:
        await dispatcher.stop()


async def test_dispatcher_start_is_idempotent():
    bus = EventBus()
    dispatcher = NotificationDispatcher(
        bus=bus, notifier=_RecordingNotifier(), preferences=NotificationPreferences()
    )
    dispatcher.start()
    task = dispatcher._task
    dispatcher.start()  # no-op
    assert dispatcher._task is task
    await dispatcher.stop()
