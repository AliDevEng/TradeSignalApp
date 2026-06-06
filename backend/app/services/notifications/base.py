"""Notification domain contract: the ``NotificationMessage`` value object + ABC.

Provider-agnostic by design, exactly like the market-data and calendar
contracts: :class:`NotificationMessage` is the single shape the dispatcher
speaks, so a Telegram bot today can be swapped for email/Slack/webhook tomorrow
by adding one :class:`Notifier` implementation with nothing upstream changing.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

from app.services import ServiceError


class NotificationError(ServiceError):
    """Base for every notification failure (transport, config, …).

    A :class:`ServiceError` so the rest of the codebase catches one base; the
    dispatcher isolates these so a delivery outage never disturbs the pipeline.
    """


@dataclass(frozen=True, slots=True)
class NotificationMessage:
    """A channel-agnostic message: a short title, a body, and an optional link.

    ``url`` is a deep link back into the app (e.g. the signal detail page) that
    transports able to render links can attach. Kept deliberately small so every
    channel — from a 4096-char Telegram message to an SMS — can carry it.
    """

    title: str
    body: str
    url: str | None = None


class Notifier(abc.ABC):
    """Async sink for outbound notifications."""

    #: Stable identifier for logs/health, mirroring the other provider ABCs.
    provider_name: str

    @abc.abstractmethod
    async def send(self, message: NotificationMessage) -> None:
        """Deliver one message.

        Implementations raise a :class:`NotificationError` subclass on failure —
        never a raw transport exception — so the dispatcher can isolate a
        delivery outage exactly like a market-data one.
        """

    @abc.abstractmethod
    async def aclose(self) -> None:
        """Release any held resources (HTTP clients, …). Must be idempotent."""
