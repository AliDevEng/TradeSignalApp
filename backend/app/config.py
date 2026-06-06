from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends
from pydantic import Field, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.timeframes import timeframe_minutes

Environment = Literal["development", "staging", "production", "test"]
AIProvider = Literal["groq", "anthropic"]
MarketDataProvider = Literal["twelve_data"]
NotificationProvider = Literal["telegram"]
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
    # Low temperature: signal generation should be near-deterministic. A high
    # temperature makes back-tests irreproducible and confidence scores noisy.
    ai_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    # Each analysis returns *two* signals (scalp + swing), each with a level
    # ladder and a rationale, so the budget is wider than a single-signal reply
    # needs — a truncated reply is an unparseable reply.
    ai_max_tokens: int = Field(default=2048, ge=256, le=8192)
    # Per-request budget. A hung provider must never stall an analysis cycle
    # past this; the cycle records the failure and moves on.
    ai_timeout_seconds: float = Field(default=30.0, gt=0.0, le=300.0)

    # ── Market Data ────────────────────────────────────────────────────────
    market_data_provider: MarketDataProvider = "twelve_data"
    twelve_data_api_key: str
    twelve_data_base_url: str = "https://api.twelvedata.com"
    market_data_timeout_seconds: float = Field(default=15.0, gt=0.0, le=120.0)
    # Transient failures (timeouts, 5xx, rate limits) are retried with
    # exponential backoff up to this many additional attempts.
    market_data_max_retries: int = Field(default=3, ge=0, le=10)

    # ── Analysis schedule ──────────────────────────────────────────────────
    analysis_interval_minutes: int = Field(default=15, ge=1, le=1440)
    analysis_candle_count: int = Field(default=200, ge=20, le=5000)
    # How many pairs a single run analyses concurrently. Each pair costs a few
    # market-data calls + one AI call (tens of seconds), so a run's wall-clock
    # time is ``ceil(pairs / this) * per-pair`` — without it, run time grows
    # linearly with the pair count and can overrun the schedule. Kept modest by
    # default to respect the market-data plan's per-minute budget (the candle
    # cache + provider retries make a small burst safe); raise it once on a
    # higher-tier data plan. ``1`` restores fully-sequential behaviour.
    analysis_max_concurrency: int = Field(default=3, ge=1, le=32)
    # The primary (decision) timeframe: the one a generated signal is framed on
    # and recorded against. Must be one of the analysed timeframes (the union of
    # the per-style frames below); appended automatically if omitted from both.
    analysis_timeframe: Timeframe = "1h"
    # Per-style timeframe frames. Each signal style is framed on — and the model
    # is shown — its own set: the scalp leans on fast timeframes (tight stop,
    # near targets), the swing on slow ones (wide stop, extended targets). The
    # *union* of the two (see the ``analysis_timeframes`` property) is what gets
    # fetched per run, so overlapping a timeframe across styles costs nothing
    # extra. Each timeframe in the union costs at most one market-data call per
    # pair per run (slow ones are served from the candle cache between bars).
    # Comma-separated in .env (SCALP_TIMEFRAMES=5m,15m,1h,4h / SWING_TIMEFRAMES=4h,1d).
    scalp_timeframes: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["5m", "15m", "1h", "4h"]
    )
    swing_timeframes: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["4h", "1d"])

    # ── Outcome tracking ─────────────────────────────────────────────────────
    # Cadence of the outcome job, which re-checks open signals against fresh
    # candles to see whether price hit a target/stop. Independent of the
    # analysis cadence: outcomes want timely detection (a tighter loop), while
    # analysis is heavier. One market-data fetch per active pair per outcome
    # cycle (the lowest configured timeframe, for the finest fills), so keep this
    # in line with the data plan's per-minute budget.
    outcome_interval_minutes: int = Field(default=5, ge=1, le=1440)

    # ── Signal quality gate ──────────────────────────────────────────────────
    # The product always emits a directional bias per style, but a bias is only
    # marked *actionable* (``should_trade``) when the deterministic gate agrees.
    # ``min_reward_risk`` is the reward:risk-to-TP1 floor below which a setup is
    # vetoed outright (the most common reason a tidy-looking trade loses over
    # time); ``quality_trade_threshold`` is the blended-quality score a surviving
    # bias must clear to be actionable. Both are deliberately conservative.
    min_reward_risk: float = Field(default=1.5, ge=0.0, le=10.0)
    quality_trade_threshold: float = Field(default=0.5, ge=0.0, le=1.0)

    # ── Economic calendar (news awareness) ───────────────────────────────────
    # Off by default: when disabled the pipeline behaves exactly as if no events
    # existed. When enabled, high-impact events inside ``news_blackout_minutes``
    # of now cause the gate to veto new trades for the affected instrument (and
    # the prompt to widen caution). ``economic_calendar_events_json`` seeds the
    # static provider — a JSON array of {title,currency,impact,scheduled_at}.
    economic_calendar_enabled: bool = False
    economic_calendar_events_json: str = ""
    news_blackout_minutes: int = Field(default=60, ge=0, le=1440)

    # ── Signal lifetime ────────────────────────────────────────────────────
    # How long each style's signal stays "fresh" before ``expires_at`` lapses.
    # A scalp ages out in hours; a swing lives for days. These drive the frontend
    # freshness badge and the outcome evaluator's mark-to-market on expiry, and
    # are bounded so a typo can't create an effectively-immortal or instantly-
    # stale signal.
    signal_scalp_ttl_minutes: int = Field(default=240, ge=1, le=10080)  # 4h .. 7d cap
    signal_swing_ttl_minutes: int = Field(default=4320, ge=1, le=43200)  # 3d .. 30d cap

    # ── Performance / track record ───────────────────────────────────────────
    # Default window for the performance API when the caller passes no explicit
    # from/to: only signals closed within the last N days are aggregated, so the
    # query and in-memory roll-up stay bounded as history accumulates. Callers
    # can still request any window explicitly. ``0`` disables the default
    # (all-time), which is fine for a young dataset but not as it grows.
    performance_default_lookback_days: int = Field(default=90, ge=0, le=3650)
    # Hard cap on equity-curve points returned. Cumulative R is computed over
    # *every* closed signal in the window; the resulting curve is then
    # downsampled to at most this many points (the final point always kept) so
    # the JSON payload can't balloon — a line chart can't resolve more anyway.
    performance_equity_max_points: int = Field(default=500, ge=2, le=10000)

    # ── Real-time streaming (SSE) ──────────────────────────────────────────────
    # The ``GET /api/v1/stream`` endpoint pushes signal/run events to connected
    # browsers instead of being polled. A keep-alive comment is sent every
    # ``stream_heartbeat_seconds`` so idle proxies don't drop the connection.
    # ``stream_max_queue`` bounds each connected client's in-memory buffer — a
    # client that can't keep up is disconnected (it reconnects and resumes via
    # ``Last-Event-ID``) rather than being allowed to grow memory unbounded.
    # ``stream_replay_buffer`` is the ring of recent events retained for that
    # resume; a client offline longer than this many events resumes from the
    # oldest retained.
    stream_heartbeat_seconds: int = Field(default=15, ge=1, le=300)
    stream_max_queue: int = Field(default=100, ge=1, le=10000)
    stream_replay_buffer: int = Field(default=200, ge=0, le=10000)

    # ── Notifications ──────────────────────────────────────────────────────────
    # Off by default: when disabled the notifier is a no-op, so the whole path is
    # inert (exactly as if the feature did not exist). When enabled, a background
    # dispatcher consumes the same events the stream serves and pushes the ones
    # that pass the preferences below to the configured channel. ``telegram`` is
    # the only provider today; it needs a bot token and a chat id (the "chatbot
    # id" an operator supplies) — both validated at startup when enabled.
    notifications_enabled: bool = False
    notification_provider: NotificationProvider = "telegram"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    notification_timeout_seconds: float = Field(default=10.0, gt=0.0, le=60.0)
    # Preferences — the pure filter applied before dispatch. Defaults are
    # conservative: only reasonably-confident, *actionable* new signals and any
    # close, for both styles.
    notification_min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    notification_signal_types: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["scalp", "swing"]
    )
    notification_only_actionable: bool = True
    notification_on_signal_created: bool = True
    notification_on_signal_closed: bool = True

    # ── Scheduler ──────────────────────────────────────────────────────────
    # Disable on API-only replicas so the analysis job runs on exactly one
    # instance in a horizontally-scaled deployment (running it everywhere
    # would generate duplicate signals and multiply provider cost).
    scheduler_enabled: bool = True
    scheduler_timezone: str = "UTC"
    # How late a missed run may fire before it is skipped — guards against a
    # backlog of catch-up runs after a pause (deploy, suspend, clock skew).
    scheduler_misfire_grace_seconds: int = Field(default=60, ge=1, le=3600)

    # Comma-separated in .env (ACTIVE_PAIRS=XAUUSD,GBPUSD,EURUSD).
    # The validator normalises to list[str] so the rest of the codebase has a
    # single, properly typed source of truth.
    active_pairs: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["XAUUSD", "GBPUSD", "EURUSD"]
    )

    @field_validator(
        "active_pairs",
        "cors_allowed_origins",
        "scalp_timeframes",
        "swing_timeframes",
        "notification_signal_types",
        mode="before",
    )
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("notification_signal_types")
    @classmethod
    def _validate_notification_styles(cls, value: list[str]) -> list[str]:
        """Normalise + validate the styles a notification may fire for.

        Each entry must be a known signal style; an empty list means "no style
        filter" (any style notifies). Failing fast on a typo (``scal``) is far
        easier to diagnose than silently never notifying.
        """
        allowed = {"scalp", "swing"}
        deduped: list[str] = []
        for style in (s.strip().lower() for s in value):
            if not style:
                continue
            if style not in allowed:
                raise ValueError(f"invalid signal style {style!r}; allowed: {sorted(allowed)}")
            if style not in deduped:
                deduped.append(style)
        return deduped

    @field_validator("active_pairs")
    @classmethod
    def _require_pairs(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("active_pairs must contain at least one trading pair")
        return [p.upper() for p in value]

    @field_validator("scalp_timeframes", "swing_timeframes")
    @classmethod
    def _validate_timeframes(cls, value: list[str], info: ValidationInfo) -> list[str]:
        """Normalise, validate, and de-duplicate one per-style timeframe list.

        Each entry must be a supported ``Timeframe`` literal; an unknown value
        is a configuration error (the market-data provider would reject it
        anyway, but failing fast at startup is far easier to diagnose).
        """
        allowed = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
        normalised = [tf.strip().lower() for tf in value]
        if not normalised:
            raise ValueError(f"{info.field_name} must contain at least one timeframe")
        deduped: list[str] = []
        for tf in normalised:
            if tf not in allowed:
                raise ValueError(f"invalid timeframe {tf!r}; allowed: {sorted(allowed)}")
            if tf not in deduped:
                deduped.append(tf)
        return deduped

    @model_validator(mode="after")
    def _primary_timeframe_in_frames(self) -> "Settings":
        """The decision timeframe must be one of the analysed timeframes.

        Otherwise a signal would be recorded against a timeframe the model was
        never shown. Append it to the scalp frame rather than reject, so a
        minimal config still works without listing it in either set.
        """
        if self.analysis_timeframe not in (*self.scalp_timeframes, *self.swing_timeframes):
            self.scalp_timeframes = [*self.scalp_timeframes, self.analysis_timeframe]
        return self

    @property
    def analysis_timeframes(self) -> list[str]:
        """Ordered-unique union of the per-style frames — the set fetched per run.

        Ordered low→high (by bar duration) so the fetch order and the run ledger
        read naturally; presentation order (e.g. high→low for the prompt) is the
        caller's concern. Computed, not stored, so the two style lists stay the
        single source of truth.
        """
        merged = [*self.scalp_timeframes, *self.swing_timeframes]
        union: list[str] = []
        for tf in sorted(merged, key=timeframe_minutes):
            if tf not in union:
                union.append(tf)
        return union

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
