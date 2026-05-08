from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # Database
    database_url: str

    # AI Provider
    ai_provider: str = "groq"
    ai_model: str = "llama-3.3-70b-versatile"
    ai_api_key: str

    # Market Data
    market_data_provider: str = "twelve_data"
    twelve_data_api_key: str

    # Analysis schedule
    analysis_interval_minutes: int = 15
    analysis_candle_count: int = 200
    analysis_timeframe: str = "1h"

    # Comma-separated in .env (e.g. ACTIVE_PAIRS=XAUUSD,GBPUSD,EURUSD).
    # pydantic-settings JSON-decodes list fields before validators run, so we
    # store as str and parse to a list via the .pairs property.
    active_pairs: str = "XAUUSD,GBPUSD,EURUSD"

    @property
    def pairs(self) -> list[str]:
        return [p.strip() for p in self.active_pairs.split(",") if p.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
