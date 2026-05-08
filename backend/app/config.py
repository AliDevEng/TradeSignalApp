from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

Environment = Literal["development", "staging", "production", "test"]
AIProvider = Literal["groq", "anthropic"]
MarketDataProvider = Literal["twelve_data"]
Timeframe = Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── App ────────────────────────────────────────────────────────────────
    app_env: Environment = "development"
    app_host: str = "0.0.0.0"
    app_port: int = Field(default=8000, ge=1, le=65535)
    debug: bool = False

    # Comma-separated list of allowed CORS origins (e.g. https://app.example.com).
    # Empty/unset disables CORS entirely. Defaults are dev-friendly only.
    # NoDecode keeps pydantic-settings from JSON-decoding the raw env value so
    # our validator can do CSV splitting instead.
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    # ── Database ───────────────────────────────────────────────────────────
    # Pool sizing is exposed so it can be tuned per environment without code
    # changes. Defaults target a single backend instance hitting Postgres on
    # the same network — bump pool_size + max_overflow for higher concurrency.
    database_url: str
    database_pool_size: int = Field(default=10, ge=1, le=200)
    database_max_overflow: int = Field(default=20, ge=0, le=500)
    # Recycle connections older than this to dodge silently-dropped sockets
    # (NAT timeouts, PG idle_in_transaction_session_timeout, …).
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    # SQLAlchemy will emit every SQL statement at INFO level when True.
    # Useful for local debugging; never enable in production.
    database_echo: bool = False

    # ── AI Provider ────────────────────────────────────────────────────────
    ai_provider: AIProvider = "groq"
    ai_model: str = "llama-3.3-70b-versatile"
    ai_api_key: str

    # ── Market Data ────────────────────────────────────────────────────────
    market_data_provider: MarketDataProvider = "twelve_data"
    twelve_data_api_key: str

    # ── Analysis schedule ──────────────────────────────────────────────────
    analysis_interval_minutes: int = Field(default=15, ge=1, le=1440)
    analysis_candle_count: int = Field(default=200, ge=20, le=5000)
    analysis_timeframe: Timeframe = "1h"

    # Comma-separated in .env (ACTIVE_PAIRS=XAUUSD,GBPUSD,EURUSD).
    # The validator normalises to list[str] so the rest of the codebase has a
    # single, properly typed source of truth.
    active_pairs: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["XAUUSD", "GBPUSD", "EURUSD"]
    )

    @field_validator("active_pairs", "cors_allowed_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("active_pairs")
    @classmethod
    def _require_pairs(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("active_pairs must contain at least one trading pair")
        return [p.upper() for p in value]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Annotated dependency for use in FastAPI route signatures:
#   def my_route(settings: SettingsDep) -> ...:
SettingsDep = Annotated[Settings, Depends(get_settings)]
