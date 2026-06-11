"""In-process publish/subscribe event bus — the spine of real-time delivery.

The analysis and outcome pipelines *publish* domain events (a signal was
created, a signal closed, a run finished); the SSE endpoint and the notification
dispatcher *subscribe* to them. Keeping the producers decoupled from the
consumers behind one narrow bus is what lets a single ``publish`` call fan out to
"every connected browser" *and* "Telegram" without either producer knowing the
other consumer exists.

Design decisions worth stating up front, because they are load-bearing:

* **Publishing never blocks and never fails a pipeline.** ``publish`` is a plain
  synchronous call: it stamps the event with a monotonic id, appends it to a
  bounded replay buffer, and ``put_nowait``s it onto each subscriber's queue. A
  full queue (a slow consumer) marks that subscriber *dropped* rather than
  raising or awaiting — a stalled browser tab must never apply backpressure to
  the trading pipeline.

* **Monotonic ids enable SSE resume.** Every event carries an ``id`` from a
  process-local counter. A reconnecting client sends ``Last-Event-ID`` and the
  bus replays everything newer from its ring buffer, so a brief disconnect
  doesn't silently drop a signal.

* **In-process by design (Iteration 11 scope).** This bus lives in one process,
  which is the right fit while the scheduler — the sole event *producer* — runs
  on exactly one instance (``scheduler_enabled``). Horizontal scale-out of the
  *consumers* (multiple API replicas each serving SSE) is the seam a future
  Redis/NATS-backed :class:`EventPublisher` slots into without touching the
  controllers, exactly like the market-data/calendar provider swaps. The
  abstract :class:`EventPublisher` is that seam.

Layering: this is a service (``app.services``) — it may be imported by
controllers and (via the lifespan) wired to the views, but it imports nothing
from ``app.views``/``app.controllers`` itself.
"""

from __future__ import annotations

import abc
import asyncio
import json
import logging
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final, Literal

logger = logging.getLogger(__name__)

#: The closed vocabulary of domain events. A ``Literal`` (not a free string) so a
#: typo in a ``publish`` call is a type error and the frontend can switch on a
#: known set.
#:
#: ``run.started``/``run.progress`` narrate a pipeline cycle *while it runs* so the
#: UI can show the otherwise-invisible background workflow (fetching → analysing →
#: scoring). They are high-frequency and *transient* — only the live view cares —
#: so they are published with ``buffer=False`` (kept out of the replay ring), while
#: the durable ``signal.*``/``run.finished`` events are buffered for resume.
EventType = Literal[
    "signal.created",
    "signal.closed",
    "run.started",
    "run.progress",
    "run.finished",
]

#: SSE field terminator: a single record ends with a blank line.
_SSE_TERMINATOR: Final[str] = "\n\n"


@dataclass(frozen=True, slots=True)
class Event:
    """One domain event: a monotonic id, a type, a UTC timestamp, and a payload.

    ``data`` is a plain JSON-serialisable dict (the producer is responsible for
    projecting ``Decimal``/``datetime`` to strings) so the same event renders to
    SSE for browsers and to a notification message without re-shaping.
    """

    id: int
    type: EventType
    at: datetime
    data: dict[str, Any]

    def to_sse(self) -> str:
        """Render as a Server-Sent-Events record.

        Emits ``id`` (so the browser tracks ``Last-Event-ID`` automatically),
        ``event`` (the type, for ``addEventListener``), and a single ``data``
        line carrying the JSON payload. ``ensure_ascii`` keeps the byte stream
        7-bit clean across proxies.
        """
        payload = json.dumps(
            {"id": self.id, "type": self.type, "at": self.at.isoformat(), "data": self.data},
            ensure_ascii=True,
            separators=(",", ":"),
        )
        return f"id: {self.id}\nevent: {self.type}\ndata: {payload}{_SSE_TERMINATOR}"


class Subscription:
    """A single consumer's view of the bus: a bounded queue plus a drop flag.

    Created by :meth:`EventBus.subscribe` and released by :meth:`close` (idempotent).
    ``dropped`` flips to ``True`` the moment the bus fails to enqueue an event
    because this consumer fell too far behind — the consumer is expected to
    notice, tell the client to reconnect (which resumes via ``Last-Event-ID``),
    and close. Keeping the policy "drop + resume" rather than "block" is what
    isolates one slow client from every other consumer and from the producer.
    """

    __slots__ = ("_bus", "dropped", "queue")

    def __init__(self, bus: EventBus, maxsize: int) -> None:
        self._bus = bus
        self.queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=maxsize)
        self.dropped = False

    async def get(self) -> Event:
        """Await the next event for this subscriber."""
        return await self.queue.get()

    def close(self) -> None:
        """Detach from the bus so no further events are enqueued. Idempotent."""
        self._bus._remove(self)


class EventPublisher(abc.ABC):
    """The narrow producer-facing seam controllers depend on.

    Controllers only ever *publish*; depending on this abstract surface (rather
    than the concrete :class:`EventBus`) keeps them swappable against the
    :class:`NullEventBus` in tests and a future distributed backend in
    production.
    """

    @abc.abstractmethod
    def publish(self, event_type: EventType, data: dict[str, Any], *, buffer: bool = True) -> Event:
        """Publish an event and return the stamped :class:`Event`.

        ``buffer=False`` fans the event out to live subscribers but keeps it out
        of the replay ring — the right choice for transient progress chatter a
        reconnecting client should not be re-told.
        """


class NullEventBus(EventPublisher):
    """A publisher that swallows everything — the default when no bus is wired.

    Lets a controller be constructed and unit-tested without a real bus, and
    keeps publishing a guaranteed no-op cost where streaming is irrelevant.
    """

    def publish(self, event_type: EventType, data: dict[str, Any], *, buffer: bool = True) -> Event:
        return Event(id=0, type=event_type, at=datetime.now(UTC), data=data)


class EventBus(EventPublisher):
    """Process-local fan-out bus with bounded per-subscriber queues + replay.

    Constructed once in the lifespan and shared by every producer and consumer in
    the process. Thread-affinity note: all access happens on the single asyncio
    event loop (the scheduler and the ASGI server share it), so the plain ``set``
    of subscribers and the integer counter need no locking — there is never more
    than one coroutine mutating them at a time between awaits.
    """

    def __init__(self, *, max_queue: int = 100, replay_buffer: int = 200) -> None:
        self._subscribers: set[Subscription] = set()
        # Ring buffer of recent events for ``Last-Event-ID`` resume. Bounded so a
        # long-lived process can't grow it without limit; a client offline longer
        # than ``replay_buffer`` events simply resumes from the oldest retained.
        self._recent: deque[Event] = deque(maxlen=replay_buffer)
        self._max_queue = max_queue
        self._seq = 0

    # ── Producer side ────────────────────────────────────────────────────────

    def publish(self, event_type: EventType, data: dict[str, Any], *, buffer: bool = True) -> Event:
        """Stamp, (optionally) buffer, and fan an event out to subscribers. Never blocks.

        ``buffer=False`` skips the replay ring so transient progress events don't
        evict the durable ``signal.*``/``run.finished`` events a reconnecting
        client genuinely needs to resume — the live subscribers still receive it.
        """
        self._seq += 1
        event = Event(id=self._seq, type=event_type, at=datetime.now(UTC), data=data)
        if buffer:
            self._recent.append(event)
        for sub in self._subscribers:
            try:
                sub.queue.put_nowait(event)
            except asyncio.QueueFull:
                # Slow consumer: mark it dropped instead of blocking the producer.
                # The consumer loop checks this flag and disconnects the client,
                # which reconnects and resumes from the replay buffer.
                if not sub.dropped:
                    logger.warning("SSE subscriber fell behind; marking for reconnect")
                sub.dropped = True
        return event

    # ── Consumer side ────────────────────────────────────────────────────────

    def subscribe(self) -> Subscription:
        """Register a new consumer and return its :class:`Subscription`.

        The caller owns the lifecycle: drain it with :meth:`Subscription.get` and
        always :meth:`Subscription.close` it (a ``try/finally``) so a disconnected
        client doesn't leak a queue the producer keeps filling.
        """
        sub = Subscription(self, self._max_queue)
        self._subscribers.add(sub)
        return sub

    def _remove(self, sub: Subscription) -> None:
        self._subscribers.discard(sub)

    def replay_since(self, last_event_id: int | None) -> list[Event]:
        """Buffered events newer than ``last_event_id`` (oldest-first).

        ``None`` (a fresh connection with no ``Last-Event-ID``) replays nothing —
        a new client wants the live stream, not history. A known id replays
        everything retained that is strictly newer, so a reconnect within the
        buffer window loses no events.
        """
        if last_event_id is None:
            return []
        return [event for event in self._recent if event.id > last_event_id]

    @property
    def subscriber_count(self) -> int:
        """Number of currently-attached subscribers (for health/diagnostics)."""
        return len(self._subscribers)
