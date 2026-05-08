import pytest
from app.config import Settings
from pydantic import ValidationError


def _base_env(overrides: dict | None = None) -> dict:
    """Minimal valid env for constructing Settings without a .env file."""
    env = {
        "database_url": "postgresql+asyncpg://user:pw@localhost:5432/test",
        "ai_api_key": "test-key",
        "twelve_data_api_key": "test-key",
    }
    if overrides:
        env.update(overrides)
    return env


def test_defaults_are_applied():
    s = Settings(**_base_env(), _env_file=None)
    assert s.app_env == "development"
    assert s.app_port == 8000
    assert s.debug is False
    assert s.ai_provider == "groq"
    assert s.analysis_interval_minutes == 15
    assert s.analysis_candle_count == 200
    assert s.analysis_timeframe == "1h"


def test_pairs_property_parses_comma_string():
    s = Settings(**_base_env({"active_pairs": "XAUUSD,GBPUSD,EURUSD"}), _env_file=None)
    assert s.pairs == ["XAUUSD", "GBPUSD", "EURUSD"]


def test_pairs_property_strips_whitespace():
    s = Settings(**_base_env({"active_pairs": " XAUUSD , GBPUSD , EURUSD "}), _env_file=None)
    assert s.pairs == ["XAUUSD", "GBPUSD", "EURUSD"]


def test_pairs_property_ignores_empty_segments():
    s = Settings(**_base_env({"active_pairs": "XAUUSD,,EURUSD,"}), _env_file=None)
    assert s.pairs == ["XAUUSD", "EURUSD"]


def test_is_development_true_for_development_env():
    s = Settings(**_base_env({"app_env": "development"}), _env_file=None)
    assert s.is_development is True
    assert s.is_production is False


def test_is_production_true_for_production_env():
    s = Settings(**_base_env({"app_env": "production"}), _env_file=None)
    assert s.is_production is True
    assert s.is_development is False


def test_missing_database_url_raises():
    env = {
        "ai_api_key": "test-key",
        "twelve_data_api_key": "test-key",
    }
    with pytest.raises(ValidationError) as exc_info:
        Settings(**env, _env_file=None)
    assert "database_url" in str(exc_info.value)


def test_missing_ai_api_key_raises():
    env = {
        "database_url": "postgresql+asyncpg://user:pw@localhost:5432/test",
        "twelve_data_api_key": "test-key",
    }
    with pytest.raises(ValidationError) as exc_info:
        Settings(**env, _env_file=None)
    assert "ai_api_key" in str(exc_info.value)


def test_app_port_coerced_from_string():
    s = Settings(**_base_env({"app_port": "9000"}), _env_file=None)
    assert s.app_port == 9000


def test_debug_coerced_from_string():
    s = Settings(**_base_env({"debug": "true"}), _env_file=None)
    assert s.debug is True
