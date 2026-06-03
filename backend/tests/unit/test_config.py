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


# ── Defaults ───────────────────────────────────────────────────────────────


def test_defaults_are_applied():
    s = Settings(**_base_env(), _env_file=None)
    assert s.app_env == "development"
    assert s.app_port == 8000
    assert s.debug is False
    assert s.ai_provider == "groq"
    assert s.market_data_provider == "twelve_data"
    assert s.analysis_interval_minutes == 15
    assert s.analysis_candle_count == 200
    assert s.analysis_timeframe == "1h"
    assert s.active_pairs == ["XAUUSD", "GBPUSD", "EURUSD"]
    assert s.cors_allowed_origins == ["http://localhost:3000"]


# ── active_pairs CSV parsing ───────────────────────────────────────────────


def test_active_pairs_parses_comma_string():
    s = Settings(**_base_env({"active_pairs": "XAUUSD,GBPUSD,EURUSD"}), _env_file=None)
    assert s.active_pairs == ["XAUUSD", "GBPUSD", "EURUSD"]


def test_active_pairs_strips_whitespace():
    s = Settings(**_base_env({"active_pairs": " XAUUSD , GBPUSD , EURUSD "}), _env_file=None)
    assert s.active_pairs == ["XAUUSD", "GBPUSD", "EURUSD"]


def test_active_pairs_ignores_empty_segments():
    s = Settings(**_base_env({"active_pairs": "XAUUSD,,EURUSD,"}), _env_file=None)
    assert s.active_pairs == ["XAUUSD", "EURUSD"]


def test_active_pairs_uppercased():
    s = Settings(**_base_env({"active_pairs": "xauusd,gbpusd"}), _env_file=None)
    assert s.active_pairs == ["XAUUSD", "GBPUSD"]


def test_active_pairs_empty_raises():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"active_pairs": ""}), _env_file=None)


# ── cors_allowed_origins CSV parsing ───────────────────────────────────────


def test_cors_origins_parses_csv():
    s = Settings(
        **_base_env({"cors_allowed_origins": "https://a.com,https://b.com"}),
        _env_file=None,
    )
    assert s.cors_allowed_origins == ["https://a.com", "https://b.com"]


def test_cors_origins_can_be_disabled():
    s = Settings(**_base_env({"cors_allowed_origins": ""}), _env_file=None)
    assert s.cors_allowed_origins == []


# ── Environment helpers ────────────────────────────────────────────────────


def test_is_development_true_for_development_env():
    s = Settings(**_base_env({"app_env": "development"}), _env_file=None)
    assert s.is_development is True
    assert s.is_production is False
    assert s.is_test is False


def test_is_production_true_for_production_env():
    s = Settings(**_base_env({"app_env": "production"}), _env_file=None)
    assert s.is_production is True
    assert s.is_development is False


def test_is_test_true_for_test_env():
    s = Settings(**_base_env({"app_env": "test"}), _env_file=None)
    assert s.is_test is True


def test_invalid_app_env_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"app_env": "prod"}), _env_file=None)


# ── Required fields ────────────────────────────────────────────────────────


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


# ── Type coercion and constraints ──────────────────────────────────────────


def test_app_port_coerced_from_string():
    s = Settings(**_base_env({"app_port": "9000"}), _env_file=None)
    assert s.app_port == 9000


def test_app_port_out_of_range_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"app_port": "70000"}), _env_file=None)


def test_debug_coerced_from_string():
    s = Settings(**_base_env({"debug": "true"}), _env_file=None)
    assert s.debug is True


def test_invalid_ai_provider_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"ai_provider": "openai"}), _env_file=None)


def test_invalid_timeframe_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"analysis_timeframe": "2h"}), _env_file=None)


# ── analysis_timeframes parsing/validation ──────────────────────────────────


def test_analysis_timeframes_default():
    s = Settings(**_base_env(), _env_file=None)
    assert s.analysis_timeframes == ["5m", "15m", "1h", "4h", "1d"]


def test_analysis_timeframes_parses_csv_and_lowercases():
    s = Settings(**_base_env({"analysis_timeframes": "1D, 4H , 1h"}), _env_file=None)
    assert s.analysis_timeframes == ["1d", "4h", "1h"]


def test_analysis_timeframes_dedupes():
    s = Settings(**_base_env({"analysis_timeframes": "1h,1h,4h"}), _env_file=None)
    assert s.analysis_timeframes == ["1h", "4h"]


def test_analysis_timeframes_rejects_unknown():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"analysis_timeframes": "1h,2h"}), _env_file=None)


def test_primary_timeframe_appended_when_missing():
    s = Settings(
        **_base_env({"analysis_timeframe": "1h", "analysis_timeframes": "4h,1d"}),
        _env_file=None,
    )
    assert "1h" in s.analysis_timeframes


def test_invalid_interval_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"analysis_interval_minutes": "0"}), _env_file=None)


def test_invalid_candle_count_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"analysis_candle_count": "5"}), _env_file=None)


# ── Database pool settings ─────────────────────────────────────────────────


def test_database_pool_defaults():
    s = Settings(**_base_env(), _env_file=None)
    assert s.database_pool_size == 10
    assert s.database_max_overflow == 20
    assert s.database_pool_recycle_seconds == 1800
    assert s.database_echo is False


def test_database_pool_size_coerced_from_string():
    s = Settings(**_base_env({"database_pool_size": "25"}), _env_file=None)
    assert s.database_pool_size == 25


def test_database_pool_size_zero_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"database_pool_size": "0"}), _env_file=None)


def test_database_max_overflow_zero_allowed():
    """Zero is a valid value — it disables overflow but is still legal."""
    s = Settings(**_base_env({"database_max_overflow": "0"}), _env_file=None)
    assert s.database_max_overflow == 0


def test_database_pool_recycle_below_minimum_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"database_pool_recycle_seconds": "10"}), _env_file=None)


def test_database_echo_coerced_from_string():
    s = Settings(**_base_env({"database_echo": "true"}), _env_file=None)
    assert s.database_echo is True


# ── Iteration 3: AI / market-data / scheduler knobs ─────────────────────────


def test_iteration3_defaults():
    s = Settings(**_base_env(), _env_file=None)
    # AI
    assert s.ai_temperature == 0.2
    assert s.ai_max_tokens == 2048
    assert s.ai_timeout_seconds == 30.0
    # Market data
    assert s.twelve_data_base_url == "https://api.twelvedata.com"
    assert s.market_data_timeout_seconds == 15.0
    assert s.market_data_max_retries == 3
    # Scheduler
    assert s.scheduler_enabled is True
    assert s.scheduler_timezone == "UTC"
    assert s.scheduler_misfire_grace_seconds == 60


def test_ai_temperature_out_of_range_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"ai_temperature": "2.5"}), _env_file=None)


def test_ai_max_tokens_below_minimum_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"ai_max_tokens": "100"}), _env_file=None)


def test_ai_timeout_must_be_positive():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"ai_timeout_seconds": "0"}), _env_file=None)


def test_market_data_max_retries_negative_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"market_data_max_retries": "-1"}), _env_file=None)


def test_market_data_max_retries_zero_allowed():
    """Zero disables retries — a legal (if aggressive) choice."""
    s = Settings(**_base_env({"market_data_max_retries": "0"}), _env_file=None)
    assert s.market_data_max_retries == 0


def test_scheduler_enabled_coerced_from_string():
    s = Settings(**_base_env({"scheduler_enabled": "false"}), _env_file=None)
    assert s.scheduler_enabled is False


def test_scheduler_misfire_grace_below_minimum_rejected():
    with pytest.raises(ValidationError):
        Settings(**_base_env({"scheduler_misfire_grace_seconds": "0"}), _env_file=None)
