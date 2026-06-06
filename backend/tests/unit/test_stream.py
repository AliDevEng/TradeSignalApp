"""Unit tests for the SSE stream view (Iteration 11).

The streaming loop is factored out of the route (it takes a plain
``is_disconnected`` callable, not the request) precisely so its behaviour —
replay, heartbeats, slow-consumer reconnect — can be driven deterministically
here without a live ASGI server. A thin route-level test then confirms the
endpoint wires the generator up with the right content type.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.services.events import EventBus
from app.views.stream import _resolve_last_event_id, sse_event_stream


def _request(headers: dict[str, str]) -> SimpleNamespace:
    return SimpleNamespace(headers=headers)


# ── _resolve_last_event_id ────────────────────────────────────────────────────


def test_header_wins_over_query():
    request = _request({"last-event-id": "42"})
    assert _resolve_last_event_id(request, 7) == 42  # type: ignore[arg-type]


def test_falls_back_to_query_when_no_header():
    request = _request({})
    assert _resolve_last_event_id(request, 7) == 7  # type: ignore[arg-type]


def test_malformed_header_is_ignored():
    request = _request({"last-event-id": "not-a-number"})
    assert _resolve_last_event_id(request, None) is None  # type: ignore[arg-type]


# ── sse_event_stream generator ────────────────────────────────────────────────


async def _never_disconnected() -> bool:
    return False


async def test_replays_buffered_events_then_stops_on_disconnect():
    bus = EventBus()
    bus.publish("signal.created", {"n": 1})
    bus.publish("signal.closed", {"n": 2})

    async def disconnected() -> bool:
        return True  # break immediately after replay

    chunks = [
        chunk
        async for chunk in sse_event_stream(
            bus=bus, is_disconnected=disconnected, heartbeat_seconds=5, last_event_id=0
        )
    ]

    text = "".join(chunks)
    assert text.startswith("retry: ")
    assert "event: signal.created" in text
    assert "event: signal.closed" in text


async def test_heartbeat_emitted_when_idle():
    bus = EventBus()
    calls = {"n": 0}

    async def disconnected() -> bool:
        calls["n"] += 1
        return calls["n"] > 1  # let one idle iteration run, then disconnect

    chunks = [
        chunk
        async for chunk in sse_event_stream(
            bus=bus, is_disconnected=disconnected, heartbeat_seconds=0.01, last_event_id=None
        )
    ]
    assert any(chunk.startswith(": keep-alive") for chunk in chunks)


async def test_live_event_is_streamed():
    bus = EventBus()
    agen = sse_event_stream(
        bus=bus, is_disconnected=_never_disconnected, heartbeat_seconds=5, last_event_id=None
    ).__aiter__()

    first = await agen.__anext__()  # the retry: preamble; also runs subscribe()
    assert first.startswith("retry: ")

    bus.publish("signal.created", {"pair": "XAUUSD"})
    streamed = await agen.__anext__()
    assert "event: signal.created" in streamed
    await agen.aclose()


async def test_slow_consumer_gets_reconnect_then_ends():
    bus = EventBus(max_queue=1)
    agen = sse_event_stream(
        bus=bus, is_disconnected=_never_disconnected, heartbeat_seconds=5, last_event_id=None
    ).__aiter__()

    await agen.__anext__()  # retry preamble; subscribes
    # Overflow the bounded queue: first fits, second marks the subscriber dropped.
    bus.publish("signal.created", {"n": 1})
    bus.publish("signal.created", {"n": 2})

    delivered = await agen.__anext__()  # the one event that fit
    assert "event: signal.created" in delivered
    reconnect = await agen.__anext__()  # then a reconnect nudge
    assert "event: reconnect" in reconnect


# ── Route-level wiring ────────────────────────────────────────────────────────


async def test_stream_route_returns_event_stream_response():
    """Call the handler directly (no ASGI transport, which buffers SSE) and assert
    it returns a ``text/event-stream`` response that replays buffered events."""
    from app.views.stream import stream

    bus = EventBus()
    bus.publish("signal.created", {"pair": "XAUUSD"})

    async def is_disconnected() -> bool:
        return True  # stop after replay so the body iterator terminates

    request = SimpleNamespace(headers={}, is_disconnected=is_disconnected)
    settings = SimpleNamespace(stream_heartbeat_seconds=5)
    response = await stream(request, bus, settings, last_event_id=0)  # type: ignore[arg-type]

    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["x-accel-buffering"] == "no"

    chunks = [
        chunk if isinstance(chunk, str) else chunk.decode()
        async for chunk in response.body_iterator
    ]
    assert any("event: signal.created" in chunk for chunk in chunks)
