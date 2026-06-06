"""Notification preferences — the *pure* policy applied before dispatch.

Whether an event deserves a notification (and what it should say) is decided here
by deterministic, IO-free functions over the event payload, so the policy is
unit-tested directly rather than inferred from dispatcher behaviour. The
dispatcher is then a thin loop: consume an event → ``should_notify`` → ``render``
→ hand to the :class:`~app.services.notifications.base.Notifier`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.events import Event
from app.services.notifications.base import NotificationMessage


@dataclass(frozen=True, slots=True)
class NotificationPreferences:
    """Operator-configured filters governing which events notify.

    Defaults are conservative: only reasonably-confident, *actionable* new
    signals and closes for both styles. ``signal_types`` is a frozenset so
    membership is cheap and the value is hashable/immutable.
    """

    min_confidence: float = 0.7
    signal_types: frozenset[str] = field(default_factory=lambda: frozenset({"scalp", "swing"}))
    only_actionable: bool = True
    on_signal_created: bool = True
    on_signal_closed: bool = True

    def should_notify(self, event: Event) -> bool:
        """Whether ``event`` passes the configured filters.

        Unknown event types (e.g. ``run.finished``, which is for the live UI, not
        a push) never notify. The checks read only scalar fields the producers
        guarantee on the payload, defaulting safely when one is absent.
        """
        if event.type == "signal.created":
            return self._allow_created(event.data)
        if event.type == "signal.closed":
            return self._allow_closed(event.data)
        return False

    def _allow_created(self, data: dict[str, object]) -> bool:
        if not self.on_signal_created:
            return False
        if not self._style_allowed(data):
            return False
        if self.only_actionable and not bool(data.get("should_trade", True)):
            return False
        confidence = data.get("confidence")
        if isinstance(confidence, (int, float)):
            return float(confidence) >= self.min_confidence
        # No confidence on the payload → don't gate on it (fail open for the flag).
        return True

    def _allow_closed(self, data: dict[str, object]) -> bool:
        if not self.on_signal_closed:
            return False
        return self._style_allowed(data)

    def _style_allowed(self, data: dict[str, object]) -> bool:
        style = data.get("signal_type")
        # A payload with no style is allowed through rather than silently dropped.
        return style is None or str(style) in self.signal_types


def render(event: Event) -> NotificationMessage:
    """Project an event onto a human-facing :class:`NotificationMessage`.

    Pure and total: it tolerates a partial payload (a missing field renders a
    sensible placeholder) so a notification is never lost to a formatting error.
    Only the event types ``should_notify`` admits are expected here, but it
    degrades gracefully for any.
    """
    data = event.data
    if event.type == "signal.created":
        return _render_created(data)
    if event.type == "signal.closed":
        return _render_closed(data)
    return NotificationMessage(title="TradeSignal AI", body=event.type)


def _render_created(data: dict[str, object]) -> NotificationMessage:
    pair = str(data.get("pair", "?"))
    direction = str(data.get("direction", "")).upper()
    style = str(data.get("signal_type", "")).capitalize()
    confidence = data.get("confidence")
    timeframe = str(data.get("timeframe", "")).upper()

    title = f"New {direction} signal · {pair}"
    parts = [p for p in (style, timeframe) if p]
    body_bits = [" ".join(parts)] if parts else []
    if isinstance(confidence, (int, float)):
        body_bits.append(f"{round(float(confidence) * 100)}% confidence")
    entry = data.get("entry")
    if entry is not None:
        line = f"Entry {entry}"
        stop = data.get("stop_loss")
        target = data.get("take_profit")
        if stop is not None:
            line += f" · SL {stop}"
        if target is not None:
            line += f" · TP {target}"
        body_bits.append(line)
    return NotificationMessage(
        title=title,
        body=" — ".join(body_bits) if body_bits else "A new trade signal is available.",
        url=_signal_url(data),
    )


def _render_closed(data: dict[str, object]) -> NotificationMessage:
    pair = str(data.get("pair", "?"))
    outcome = str(data.get("outcome", "closed")).replace("_", " ").upper()
    realized_r = data.get("realized_r")
    title = f"Signal closed · {pair}"
    body = f"Outcome: {outcome}"
    if realized_r is not None:
        body += f" ({realized_r}R)"
    return NotificationMessage(title=title, body=body, url=_signal_url(data))


def _signal_url(data: dict[str, object]) -> str | None:
    """A relative deep link to the signal, when an id is present.

    Relative on purpose — the public site origin is a frontend concern; a
    transport that needs an absolute URL composes it from its own config.
    """
    signal_id = data.get("signal_id")
    return f"/signals/{signal_id}" if signal_id else None
