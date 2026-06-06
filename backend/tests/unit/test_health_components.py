"""Unit tests for the health component-status helpers.

These cover the state transitions that are awkward to reproduce through the
full HTTP path — in particular the "enabled but not running" anomaly, which
must surface as `down`.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.views.health import _notifications_status, _readiness, _scheduler_status


def test_scheduler_absent_is_not_configured():
    assert _scheduler_status(None, enabled=True).status == "not_configured"


def test_scheduler_running_is_ok():
    scheduler = SimpleNamespace(running=True)
    assert _scheduler_status(scheduler, enabled=True).status == "ok"


def test_scheduler_enabled_but_stopped_is_down():
    """A scheduler that should be running but isn't is a real anomaly."""
    scheduler = SimpleNamespace(running=False)
    status = _scheduler_status(scheduler, enabled=True)
    assert status.status == "down"
    assert status.detail


def test_scheduler_disabled_by_config_is_not_configured():
    scheduler = SimpleNamespace(running=False)
    assert _scheduler_status(scheduler, enabled=False).status == "not_configured"


def test_readiness_present_is_ok():
    assert _readiness(object(), "X").status == "ok"


def test_readiness_absent_is_not_configured():
    assert _readiness(None, "X").status == "not_configured"


def test_notifications_disabled_is_not_configured():
    status = _notifications_status(object(), SimpleNamespace(running=True), enabled=False)
    assert status.status == "not_configured"


def test_notifications_enabled_and_running_is_ok():
    notifier = object()
    dispatcher = SimpleNamespace(running=True)
    assert _notifications_status(notifier, dispatcher, enabled=True).status == "ok"


def test_notifications_enabled_but_dispatcher_stopped_is_down():
    """Enabled but the dispatcher isn't consuming is a real anomaly."""
    status = _notifications_status(object(), SimpleNamespace(running=False), enabled=True)
    assert status.status == "down"
    assert status.detail


def test_notifications_enabled_but_absent_is_not_configured():
    assert _notifications_status(None, None, enabled=True).status == "not_configured"
