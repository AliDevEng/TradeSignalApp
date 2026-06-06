"""Unit tests for the in-process event bus (Iteration 11).

The bus is the spine of real-time delivery, so its guarantees are pinned
directly: monotonic ids, fan-out to subscribers, ``Last-Event-ID`` replay from a
bounded buffer, and — critically — that a slow consumer is *dropped* rather than
allowed to block the producer.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from app.services.events import EventBus, NullEventBus


def test_publish_assigns_monotonic_ids_from_one():
    bus = EventBus()
    first = bus.publish("run.finished", {"a": 1})
    second = bus.publish("signal.created", {"b": 2})
    assert first.id == 1
    assert second.id == 2
    assert first.type == "run.finished"
    assert first.at.tzinfo is not None  # timezone-aware


def test_to_sse_is_well_formed():
    bus = EventBus()
    event = bus.publish("signal.created", {"pair": "XAUUSD"})
    sse = event.to_sse()
    assert sse.startswith(f"id: {event.id}\n")
    assert "event: signal.created\n" in sse
    assert sse.endswith("\n\n")
    # The data line is a single JSON object carrying the payload + envelope.
    data_line = next(line for line in sse.splitlines() if line.startswith("data: "))
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload["type"] == "signal.created"
    assert payload["data"] == {"pair": "XAUUSD"}
    assert payload["id"] == event.id


async def test_subscriber_receives_published_events():
    bus = EventBus()
    sub = bus.subscribe()
    try:
        bus.publish("signal.created", {"n": 1})
        event = await asyncio.wait_for(sub.get(), timeout=1)
        assert event.data == {"n": 1}
    finally:
        sub.close()


def test_replay_since_returns_only_newer_events():
    bus = EventBus()
    e1 = bus.publish("signal.created", {"n": 1})
    e2 = bus.publish("signal.created", {"n": 2})
    e3 = bus.publish("signal.closed", {"n": 3})

    assert [e.id for e in bus.replay_since(e1.id)] == [e2.id, e3.id]
    # A fresh connection (no Last-Event-ID) replays nothing — it wants live only.
    assert bus.replay_since(None) == []
    assert bus.replay_since(e3.id) == []


def test_replay_buffer_is_bounded():
    bus = EventBus(replay_buffer=2)
    bus.publish("signal.created", {"n": 1})
    bus.publish("signal.created", {"n": 2})
    bus.publish("signal.created", {"n": 3})
    # Only the last two are retained; resuming from 0 yields ids 2 and 3.
    replayed = bus.replay_since(0)
    assert [e.data["n"] for e in replayed] == [2, 3]


def test_slow_consumer_is_marked_dropped_not_blocking():
    bus = EventBus(max_queue=1)
    sub = bus.subscribe()
    try:
        # First fills the queue; the second overflows it. Neither call blocks.
        bus.publish("signal.created", {"n": 1})
        bus.publish("signal.created", {"n": 2})
        assert sub.dropped is True
    finally:
        sub.close()


def test_close_detaches_subscriber():
    bus = EventBus()
    sub = bus.subscribe()
    assert bus.subscriber_count == 1
    sub.close()
    assert bus.subscriber_count == 0
    # A publish after close does not reach the detached subscriber's queue.
    bus.publish("signal.created", {"n": 1})
    assert sub.queue.empty()


def test_close_is_idempotent():
    bus = EventBus()
    sub = bus.subscribe()
    sub.close()
    sub.close()  # must not raise
    assert bus.subscriber_count == 0


def test_null_bus_is_inert():
    bus = NullEventBus()
    event = bus.publish("signal.created", {"n": 1})
    assert event.id == 0  # a throwaway event, nothing recorded


@pytest.mark.parametrize("event_type", ["signal.created", "signal.closed", "run.finished"])
def test_all_event_types_publish(event_type):
    bus = EventBus()
    event = bus.publish(event_type, {})  # type: ignore[arg-type]
    assert event.type == event_type
