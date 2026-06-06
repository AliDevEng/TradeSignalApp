"""Off-platform notifications — deliver signals where the user actually is.

The browser stream (SSE) keeps an open app live; notifications reach the user
when the app is closed. The shape mirrors the other provider families: a
:class:`Notifier` ABC behind a factory, so a Telegram bot today can be swapped
for email/Slack/webhook later without the dispatcher changing. Off by default
(``notifications_enabled = false`` → the null notifier), where the whole path is
inert. The pure :class:`NotificationPreferences` decide *which* events notify;
the :class:`NotificationDispatcher` is the thin bus→notifier bridge.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.notifications.base import (
    NotificationError,
    NotificationMessage,
    Notifier,
)
from app.services.notifications.dispatcher import NotificationDispatcher
from app.services.notifications.preferences import NotificationPreferences, render
from app.services.notifications.providers import NullNotifier, TelegramNotifier

if TYPE_CHECKING:
    from app.config import Settings

__all__ = [
    "NotificationDispatcher",
    "NotificationError",
    "NotificationMessage",
    "NotificationPreferences",
    "Notifier",
    "NullNotifier",
    "TelegramNotifier",
    "build_notifier",
    "build_preferences",
    "render",
]


def build_notifier(settings: Settings) -> Notifier:
    """Construct the notifier selected by configuration.

    Disabled (the default) → a :class:`NullNotifier` that drops everything, so the
    notification path is inert. Enabled → the configured provider; ``telegram``
    requires a bot token and chat id (validated at construction — an enabled but
    unconfigured notifier fails fast rather than silently dropping messages).
    """
    if not settings.notifications_enabled:
        return NullNotifier()
    if settings.notification_provider == "telegram":
        return TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            timeout_seconds=settings.notification_timeout_seconds,
        )
    # Unreachable while ``notification_provider`` is a single-value Literal, but
    # keeps the factory honest as providers are added.
    raise NotificationError(f"Unknown notification provider {settings.notification_provider!r}")


def build_preferences(settings: Settings) -> NotificationPreferences:
    """Project the notification config onto the pure preference policy."""
    return NotificationPreferences(
        min_confidence=settings.notification_min_confidence,
        signal_types=frozenset(settings.notification_signal_types),
        only_actionable=settings.notification_only_actionable,
        on_signal_created=settings.notification_on_signal_created,
        on_signal_closed=settings.notification_on_signal_closed,
    )
