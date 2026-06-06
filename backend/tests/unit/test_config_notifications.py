"""Config tests for the Iteration-11 streaming + notification settings."""

import pytest
from app.config import Settings
from pydantic import ValidationError


def _base_env(overrides: dict | None = None) -> dict:
    env = {
        "database_url": "postgresql+asyncpg://user:pw@localhost:5432/test",
        "ai_api_key": "test-key",
        "twelve_data_api_key": "test-key",
    }
    if overrides:
        env.update(overrides)
    return env


# ── Defaults ───────────────────────────────────────────────────────────────


def test_streaming_and_notification_defaults():
    s = Settings(**_base_env(), _env_file=None)
    assert s.stream_heartbeat_seconds == 15
    assert s.stream_max_queue == 100
    assert s.stream_replay_buffer == 200
    assert s.notifications_enabled is False
    assert s.notification_provider == "telegram"
    assert s.telegram_bot_token == ""
    assert s.telegram_chat_id == ""
    assert s.notification_min_confidence == 0.7
    assert s.notification_signal_types == ["scalp", "swing"]
    assert s.notification_only_actionable is True
    assert s.notification_on_signal_created is True
    assert s.notification_on_signal_closed is True


# ── notification_signal_types CSV parsing + validation ───────────────────────


def test_notification_styles_parse_csv():
    s = Settings(**_base_env({"notification_signal_types": "scalp"}), _env_file=None)
    assert s.notification_signal_types == ["scalp"]


def test_notification_styles_normalise_and_dedupe():
    s = Settings(
        **_base_env({"notification_signal_types": " SWING , swing , Scalp "}), _env_file=None
    )
    assert s.notification_signal_types == ["swing", "scalp"]


def test_notification_styles_reject_unknown():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"notification_signal_types": "scal"}), _env_file=None)


def test_notification_styles_empty_means_no_filter():
    s = Settings(**_base_env({"notification_signal_types": ""}), _env_file=None)
    assert s.notification_signal_types == []


# ── Bounds ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "field,value",
    [
        ("stream_heartbeat_seconds", 0),
        ("stream_heartbeat_seconds", 301),
        ("stream_max_queue", 0),
        ("stream_replay_buffer", -1),
        ("notification_min_confidence", 1.5),
        ("notification_min_confidence", -0.1),
        ("notification_timeout_seconds", 0),
    ],
)
def test_out_of_range_values_rejected(field, value):
    with pytest.raises(ValidationError):
        Settings(**_base_env({field: value}), _env_file=None)


def test_unknown_notification_provider_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"notification_provider": "carrier-pigeon"}), _env_file=None)
