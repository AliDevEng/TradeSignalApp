"""Real-time event plumbing — the in-process event bus (Iteration 11).

The analysis and outcome pipelines publish domain events
(``signal.created`` / ``signal.closed`` / ``run.finished``); the SSE endpoint and
the notification dispatcher consume them. The :class:`EventPublisher` ABC is the
producer-facing seam (so controllers stay swappable against
:class:`NullEventBus` in tests and a future distributed backend in production);
:class:`EventBus` is the concrete process-local fan-out implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.events.bus import (
    Event,
    EventBus,
    EventPublisher,
    EventType,
    NullEventBus,
    Subscription,
)

if TYPE_CHECKING:
    from app.config import Settings

__all__ = [
    "Event",
    "EventBus",
    "EventPublisher",
    "EventType",
    "NullEventBus",
    "Subscription",
    "build_event_bus",
]


def build_event_bus(settings: Settings) -> EventBus:
    """Construct the process-local event bus sized from configuration.

    A single bus per process, shared by every producer (the pipelines) and every
    consumer (SSE clients + the notification dispatcher). The queue/replay sizes
    are operator-tunable so a high-traffic deployment can widen them without code
    changes.
    """
    return EventBus(
        max_queue=settings.stream_max_queue,
        replay_buffer=settings.stream_replay_buffer,
    )
