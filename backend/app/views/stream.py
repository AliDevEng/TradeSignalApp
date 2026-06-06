"""Stream router — Server-Sent Events for real-time signal/run updates.

``GET /api/v1/stream`` holds an open connection and pushes the same domain events
the pipelines publish (``signal.created`` / ``signal.closed`` / ``run.finished``)
to the browser, so the UI updates the instant a signal lands instead of waiting
for the next poll. SSE (not WebSockets) because the flow is strictly one-way
server→client — SSE rides plain HTTP, reconnects automatically, and resumes via
``Last-Event-ID`` with no extra protocol.

The view is deliberately thin: the fan-out, buffering, and replay live in the
:class:`~app.services.events.EventBus`; this module only translates an HTTP
connection into a subscription and frames events as the SSE wire format. The
generator is factored out (and takes a plain ``is_disconnected`` callable, not the
request) so the streaming loop — heartbeats, replay, slow-consumer handling — is
unit-testable without a live ASGI server.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.config import SettingsDep
from app.dependencies import EventBusDep
from app.services.events import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream", tags=["Stream"])

#: Reconnect delay (ms) advertised to the browser's EventSource via ``retry:``.
_RETRY_MS = 3000


def _resolve_last_event_id(request: Request, query_value: int | None) -> int | None:
    """Resolve the resume point: the ``Last-Event-ID`` header wins, else the query.

    Browsers re-send the header automatically on reconnect; the query parameter
    is a fallback for non-browser clients (and tests). A malformed header is
    ignored (treated as "no resume") rather than failing the connection.
    """
    header = request.headers.get("last-event-id")
    if header is not None:
        try:
            return int(header)
        except ValueError:
            return None
    return query_value


async def sse_event_stream(
    *,
    bus: EventBus,
    is_disconnected: Callable[[], Awaitable[bool]],
    heartbeat_seconds: float,
    last_event_id: int | None,
) -> AsyncIterator[str]:
    """Yield SSE records for one client until it disconnects or falls behind.

    The lifecycle is: subscribe → replay anything missed since
    ``last_event_id`` → then loop, emitting live events and a keep-alive comment
    whenever ``heartbeat_seconds`` passes with no traffic (so idle proxies don't
    drop the connection). If this client can't keep up (its bounded queue
    overflowed), the bus marks it dropped; we send a ``reconnect`` event and close
    so the browser reconnects and resumes cleanly via ``Last-Event-ID``.
    """
    sub = bus.subscribe()
    try:
        # Advertise the reconnect delay once, up front.
        yield f"retry: {_RETRY_MS}\n\n"
        # Replay anything the client missed while disconnected.
        for event in bus.replay_since(last_event_id):
            yield event.to_sse()

        while True:
            if await is_disconnected():
                break
            try:
                event = await asyncio.wait_for(sub.get(), timeout=heartbeat_seconds)
            except TimeoutError:
                # No traffic this interval — send a comment line as a heartbeat.
                yield ": keep-alive\n\n"
                continue
            yield event.to_sse()
            if sub.dropped:
                # We overflowed mid-delivery; ask the client to reconnect (it
                # resumes from the replay buffer) rather than silently lose events.
                yield "event: reconnect\ndata: {}\n\n"
                break
    finally:
        sub.close()


@router.get(
    "",
    summary="Real-time event stream (Server-Sent Events)",
    response_class=StreamingResponse,
)
async def stream(
    request: Request,
    bus: EventBusDep,
    settings: SettingsDep,
    last_event_id: int | None = Query(
        default=None,
        ge=0,
        description="Resume point — events newer than this id are replayed. "
        "Overridden by the Last-Event-ID header when present (browsers send it "
        "automatically on reconnect).",
    ),
) -> StreamingResponse:
    resume_from = _resolve_last_event_id(request, last_event_id)
    generator = sse_event_stream(
        bus=bus,
        is_disconnected=request.is_disconnected,
        heartbeat_seconds=settings.stream_heartbeat_seconds,
        last_event_id=resume_from,
    )
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            # Defeat caching/buffering layers that would otherwise hold the stream.
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
