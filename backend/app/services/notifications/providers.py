"""Concrete notifiers: a no-op and a Telegram bot sink.

``NullNotifier`` is the disabled default — it drops every message, so the whole
notification path is inert unless explicitly configured.
``TelegramNotifier`` posts to the Telegram Bot API ``sendMessage`` endpoint
(``https://api.telegram.org/bot<token>/sendMessage``), which needs only a bot
token and a chat id — the "chatbot id" an operator drops in to go live.
"""

from __future__ import annotations

import logging

import httpx

from app.services.notifications.base import (
    NotificationError,
    NotificationMessage,
    Notifier,
)

logger = logging.getLogger(__name__)

#: Telegram caps a message at 4096 characters; we trim defensively well under it.
_TELEGRAM_MAX_CHARS = 3500


class NullNotifier(Notifier):
    """Drops every message — the behaviour when notifications are disabled."""

    provider_name = "null"

    async def send(self, message: NotificationMessage) -> None:
        return None

    async def aclose(self) -> None:
        return None


class TelegramNotifier(Notifier):
    """Delivers messages to a Telegram chat via the Bot API.

    Constructed with a bot token and a target chat id (both from config). Owns a
    long-lived :class:`httpx.AsyncClient`; transport and API-level failures are
    normalised to :class:`NotificationError` so the dispatcher never sees a raw
    ``httpx`` exception.
    """

    provider_name = "telegram"

    def __init__(
        self,
        *,
        bot_token: str,
        chat_id: str,
        timeout_seconds: float = 10.0,
        base_url: str = "https://api.telegram.org",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not bot_token or not chat_id:
            # Fail fast: an "enabled but unconfigured" notifier is a silent
            # black hole. The factory only builds this when both are present, so
            # this guards a direct/mis-wired construction.
            raise NotificationError("TelegramNotifier requires both a bot token and a chat id")
        self._chat_id = chat_id
        self._url = f"{base_url.rstrip('/')}/bot{bot_token}/sendMessage"
        # Injectable client so tests drive it with httpx.MockTransport — no
        # network, exactly like the market-data provider's tests.
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)

    async def send(self, message: NotificationMessage) -> None:
        try:
            response = await self._client.post(self._url, json=self._payload(message))
        except httpx.HTTPError as exc:
            raise NotificationError(f"Telegram request failed: {exc}") from exc

        if response.status_code != httpx.codes.OK:
            # Telegram returns a JSON body with a ``description`` on error; surface
            # it in the log (not to any client) for diagnosis.
            raise NotificationError(
                f"Telegram API returned {response.status_code}: {response.text[:200]}"
            )

    async def aclose(self) -> None:
        await self._client.aclose()

    def _payload(self, message: NotificationMessage) -> dict[str, object]:
        """Render the message as a Telegram ``sendMessage`` payload (HTML mode)."""
        lines = [f"<b>{_escape(message.title)}</b>", _escape(message.body)]
        if message.url:
            lines.append(message.url)
        text = "\n".join(lines)[:_TELEGRAM_MAX_CHARS]
        return {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }


def _escape(text: str) -> str:
    """Minimal HTML escaping for Telegram's HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
