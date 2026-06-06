"""The notification dispatcher — bridges the event bus to a :class:`Notifier`.

It is the only consumer that turns domain events into off-platform pushes. A
single long-lived background task subscribes to the bus, applies the pure
:class:`NotificationPreferences`, renders a :class:`NotificationMessage`, and
hands it to the notifier — with every delivery isolated so a Telegram outage
never disturbs the pipeline or stops later notifications.

It is started/stopped from the FastAPI lifespan, mirroring the scheduler: built
once, started only when notifications are enabled, stopped on shutdown.
"""

from __future__ import annotations

import asyncio
import logging

from app.services.events import Event, EventBus, Subscription
from app.services.notifications.base import NotificationError, Notifier
from app.services.notifications.preferences import NotificationPreferences, render

logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """Consumes bus events on a background task and dispatches notifications."""

    def __init__(
        self,
        *,
        bus: EventBus,
        notifier: Notifier,
        preferences: NotificationPreferences,
    ) -> None:
        self._bus = bus
        self._notifier = notifier
        self._preferences = preferences
        self._task: asyncio.Task[None] | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def start(self) -> None:
        """Subscribe and spawn the consume loop. Idempotent — a second call is a no-op.

        Must be called from within a running event loop (the lifespan provides
        one). The subscription is created *synchronously* here, before the task is
        scheduled, so any event published the instant after ``start()`` returns is
        already captured — closing the startup race where early events would be
        delivered to the bus before the consumer had attached.
        """
        if self.running:
            return
        sub = self._bus.subscribe()
        self._task = asyncio.create_task(self._consume(sub), name="notification-dispatcher")
        logger.info("Notification dispatcher started (provider=%s)", self._notifier.provider_name)

    async def stop(self) -> None:
        """Cancel the consume loop and close the notifier. Idempotent and safe."""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._notifier.aclose()
        logger.info("Notification dispatcher stopped")

    async def _consume(self, sub: Subscription) -> None:
        """Drain the bus forever, dispatching events that pass the filters.

        Resilient by construction: a per-event failure is logged and skipped; a
        slow-consumer drop resubscribes (losing only the events that overflowed,
        which for best-effort notifications is acceptable). Only cancellation
        (shutdown) ends the loop. ``sub`` is created in :meth:`start` so it is
        attached before any post-start publish.
        """
        try:
            while True:
                event = await sub.get()
                if sub.dropped:
                    # We fell behind while delivering; reset by resubscribing so
                    # the queue is clear. Notifications are best-effort, so the
                    # overflowed events are intentionally not replayed here.
                    logger.warning("Notification dispatcher fell behind; resubscribing")
                    sub.close()
                    sub = self._bus.subscribe()
                await self._dispatch(event)
        except asyncio.CancelledError:
            raise
        except Exception:  # a bug in the loop must not silently kill notifications
            logger.exception("Notification dispatcher loop crashed")
        finally:
            sub.close()

    async def _dispatch(self, event: Event) -> None:
        if not self._preferences.should_notify(event):
            return
        message = render(event)
        try:
            await self._notifier.send(message)
        except NotificationError as exc:
            logger.warning("Notification delivery failed: %s", exc)
        except Exception:  # last-resort containment around the transport
            logger.exception("Unexpected error delivering notification")
