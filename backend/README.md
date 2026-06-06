# ⚙️ Backend Setup - TradeSignal AI

## ✅ Goal
Build a scalable **FastAPI backend** with scheduler, indicator pipeline, AI provider abstraction, and PostgreSQL persistence.

## 📌 Latest Versions (verified on 2026-04-22)
- `fastapi`: `0.136.0`
- `uvicorn`: `0.45.0`
- `pydantic`: `2.13.3`
- `pydantic-settings`: `2.14.0`
- `sqlalchemy`: `2.0.49`
- `greenlet`: `3.3.0` (required by SQLAlchemy's async extension — pinned explicitly rather than relied on transitively)
- `alembic`: `1.18.4`
- `apscheduler`: `3.11.2`
- `asyncpg`: `0.31.0`
- `httpx`: `0.28.1`
- `python-dotenv`: `1.2.2`
- `groq`: `1.2.0`
- `anthropic`: `0.96.0`
- `pandas`: `3.0.2`
- `numpy`: `2.4.4`
- `pandas-ta-classic`: `0.4.47` (practical replacement for `pandas-ta` on current PyPI index)
- `pytest`: `9.0.3`
- `pytest-asyncio`: `1.3.0`
- `ruff`: `0.15.11`

## ⚡ Setup Commands
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

## 🧩 Iterations and Points

### Iteration 1 - Core API Skeleton (14 points) ✅ DONE
- [x] (3) Scaffold `app/main.py`, `config.py`, router registration
- [x] (3) Add health endpoint
- [x] (4) Add settings and env loading
- [x] (4) Add base schemas and common response models

### Iteration 2 - Data Layer (20 points) ✅ DONE
- [x] (5) Setup SQLAlchemy async engine/session
- [x] (5) Add models (`pair`, `signal`, `analysis_run`)
- [x] (5) Setup Alembic and first migration
- [x] (5) Implement repository layer

### Iteration 3 - Services + AI + Scheduler (21 points) ✅ DONE
- [x] (6) Implement market data service (Twelve Data)
- [x] (5) Implement indicators calculator
- [x] (5) Implement AI provider pattern (`groq` + `anthropic`)
- [x] (5) Add APScheduler job and startup wiring

### Iteration 4 - Business Logic + API Endpoints (18 points)
- [x] (6) Implement analysis controller
- [x] (5) Implement signal controller
- [x] (4) Implement signals/pairs/analysis routers
- [x] (3) Add validation and error-handling strategy

### Iteration 5 - Quality + Delivery (12 points)
- [x] (4) Unit tests for controllers/services
- [x] (3) Integration tests for core routes
- [x] (3) Lint and static checks
- [ ] (2) Docker polish + runtime docs *(deferred — revisited once the deployment target is settled)*

**Subtotal (Iterations 1-5): 85 points — complete** 🚀

---

## 🗺️ Planned Work (Iterations 6-12)

A product review on 2026-06-03 surfaced the core gap: the platform *generates*
signals but never *measures* them. A signal is drafted, fed back for keep/adjust,
then expires — nothing ever records whether price hit the take-profit or the stop.
Without that scoreboard there is no win-rate, no calibration, and no way to prove
the AI is any good. Iterations 7-12 turn the signal generator into a **measurable,
self-improving, real-time** trading platform; Iteration 6 comes first and sharpens
the signal *engine* itself — framing each style on its own timeframes and caching
the slow ones so a full multi-timeframe cycle fits the data-provider budget.

### Captured decisions
- **Signal-engine efficiency ships first (Iteration 6)** — per-style timeframes
  plus candle caching make a full multi-timeframe cycle affordable before more
  work is piled onto each run. **Outcome tracking is the keystone of the
  measurement work (Iteration 7)** — Iterations 8 and 9 build directly on the
  data it records.
- **Current trading focus is XAUUSD (Gold) only.** The Twelve Data free tier's
  per-minute limit is consumed by the multi-timeframe fetch for a single pair (see
  the rate-limit note in project memory; Iteration 6's candle caching relaxes this
  but does not remove the per-minute ceiling). The architecture stays fully
  multi-pair; only `ACTIVE_PAIRS` is narrowed. Nothing here hard-codes Gold.
- **Outcomes are evaluated from candles, never tick data** — one cheap fetch per
  cycle, which fits the tier. The evaluator is a pure function so it is fully
  back-testable without network or AI.
- **Docker is still deferred** (Iteration 5) until the deployment target is settled.

### Iteration 6 - Per-Style Timeframes + Candle Caching (efficiency) (18 points) ✅ DONE
Goal: frame each signal style on the timeframes that actually drive it, and stop
re-fetching slow candles that cannot have changed since the last run — so a full
multi-timeframe cycle fits inside the Twelve Data free-tier budget.
- [x] (4) Config: replace the single `analysis_timeframes` with per-style
  `scalp_timeframes` (default `5m,15m,1h,4h`) and `swing_timeframes`
  (default `4h,1d`); expose an ordered-unique `analysis_timeframes` *property*
  (their union) so the fetch loop and run ledger stay unchanged. Validate each set
  (known timeframes, deduped, non-empty) and keep `analysis_timeframe` (the
  primary/decision frame) inside the union.
- [x] (5) `services/market_data/cache.py` — a `CachingMarketDataProvider` that
  *wraps* the concrete provider and implements the same `MarketDataProvider` ABC,
  so the controller's `fetch_candles` call is unchanged. Cache keyed by
  `(symbol, timeframe)`, freshness aligned to **bar-close boundaries** (a series
  is reused only while `now` is in the same bar window as the fetch, so a 4h
  series is re-fetched at most once per 4h bar and a 1d series once a day —
  dropped the moment a new bar closes, not on a wall-clock timer); serve from
  cache while fresh *and* the cached count is sufficient, else fetch. A per-key
  `asyncio.Lock` prevents a fetch stampede when a manual run overlaps the
  scheduled one. `aclose()` delegates to the wrapped provider. Wired in the lifespan.
- [x] (4) Prompt: carry `scalp_timeframes`/`swing_timeframes` on `AnalysisContext`
  and label each timeframe block in `_build_user_prompt` with its role
  (`[SCALP frame]`/`[SWING frame]`/`[SCALP+SWING frame]`); extend the output
  contract so the model frames the scalp's levels on the scalp timeframes and the
  swing's on the swing timeframes, while still reading all of them for bias.
- [x] (3) Controller: drive the fetch loop from the union, record the scalp's
  timeframe as the lowest scalp frame and the swing's as the highest swing frame,
  and pass the two frame-sets into `AnalysisContext`.
- [x] (2) Tests + docs: `CachingMarketDataProvider` tests (same-bar hit, bar-close
  refetch, boundary-crossing refetch, insufficient-count-miss, lock), updated
  config/prompt/controller tests, and refreshed `.env.example` + this README.

### Iteration 7 - Signal Outcome Tracking (foundation) (20 points) ✅ DONE
Goal: record what actually happened to every signal, so the platform has a track record.
- [x] (5) Migration (`0004_signal_outcome`): add to `signals` an `outcome` native
  enum (`open|hit_tp1|hit_tp2|hit_tp3|hit_sl|expired|cancelled`), plus `closed_at`,
  `realized_r` (`Numeric(12,4)`), `mfe`/`mae` (max favourable/adverse excursion in
  R), and `last_evaluated_at`. `outcome` is `NOT NULL DEFAULT 'open'` so existing
  rows backfill atomically; indexed via `ix_signals_outcome`.
- [x] (5) `services/outcome/evaluator.py` — a **pure** `OutcomeEvaluator`: given an
  open position + the candles since `generated_at`, return the new outcome, the
  realized R, and MFE/MAE. Deterministic, no IO, unit-tested. Encodes the
  order-of-touch rule (a candle whose range spans both SL and a TP resolves
  conservatively to SL), furthest-TP-wins within a candle, and expiry
  mark-to-market. Speaks plain `Literal`s/value objects so it stays ORM-free.
- [x] (4) `tasks/outcome_job.py` + `controllers/outcome_controller.py` — the job is
  the thin error-isolating wrapper (exactly like `AnalysisJob`); the controller
  owns the work: snapshot active pairs → fetch the lowest-timeframe candles once
  per pair (no session across IO) → load open signals → evaluate → persist
  outcomes in one transaction. Per-pair fetch failures are isolated. Runs on its
  own cadence (`OUTCOME_INTERVAL_MINUTES`, default 5) wired into the scheduler at
  lifespan.
- [x] (3) `SignalRepository`: add `list_open`, `mark_outcome`, and an `outcome`
  filter on `list_paginated`/`count_filtered`.
- [x] (3) Surface `outcome`, `realized_r`, `closed_at` on `SignalResponse`; add an
  `?outcome=` filter to `GET /api/v1/signals`.

### Iteration 8 - Performance & Calibration API (16 points) ✅ DONE
Goal: aggregate the outcome data into a track record the frontend can chart.
- [x] (5) `PerformanceController` + repo aggregation surface: win-rate, profit
  factor, expectancy (avg R), total R and counts — overall and split by
  `signal_type`. The maths lives in a **pure** `PerformanceCalculator`
  (`services/performance/`) fed by `SignalRepository.list_closed_for_performance`,
  so it is unit-tested directly rather than inferred from SQL shape.
- [x] (5) Confidence calibration: bucket *closed, R-scored* signals by stated
  confidence (0-20 … 80-100) and report predicted (mean confidence) vs realised
  hit-rate per bucket — the "when the AI says 80%, is it right 80% of the time?"
  view. Always five ordered buckets for a stable chart axis.
- [x] (3) Equity-curve series: ordered cumulative `realized_r` over closed signals
  (oldest-close first, ready to plot).
- [x] (3) `GET /api/v1/performance` (filters: `pair`, `signal_type`, `from`/`to`)
  returning summary + per-style summaries + calibration buckets + equity series,
  in the response envelope.

### Iteration 9 - Smarter, Cheaper, More Reliable AI (18 points) ✅ DONE
Goal: close the learning loop and harden the model boundary.
- [x] (5) Feedback loop: inject a compact "recent performance on this pair/style
  (hit-rate, avg R, confidence bias)" block into `BaseAIProvider._build_user_prompt`
  so the model calibrates against its *own* real results, not a guess. The
  controller snapshots the recent closed signals per style
  (`SignalRepository.list_recent_closed`) and passes a `PriorPerformance` per style
  on `AnalysisContext`; the block is omitted entirely when there's no history.
- [x] (5) Structured output: the Anthropic provider now forces a single tool whose
  `input_schema` is the `DualSignalDraft` JSON schema (`tool_choice` = that tool),
  so the reply is schema-validated by the API; the tool input is serialised back to
  JSON so the base's tolerant `_extract_json` + Pydantic validation still runs as
  defence-in-depth (and as the fallback when no tool block is present). Groq keeps
  its `response_format=json_object` JSON-mode.
- [x] (4) Cost/usage tracking: `prompt_tokens`, `completion_tokens` and `cost_usd`
  (migration `0005`, all nullable, non-negative CHECKs) on `analysis_runs`, captured
  from each provider response and summed across the run; cost via a small per-model
  pricing table (`services/ai/pricing.py`, `None` for unpriced models).
- [x] (4) `_complete` returns a `CompletionResult` (text + optional `TokenUsage`)
  and `analyze` returns an `AnalysisResult` (dual draft + usage), so the controller
  persists usage and computes cost without the view or model importing any SDK type.

### Iteration 10 - Macro / Economic-Calendar Awareness (16 points) ✅ DONE
Goal: make Gold signals aware of the news that actually moves Gold (USD, Fed, CPI).
- [x] (3) `EconomicCalendarProvider` ABC + concrete providers behind a factory,
  mirroring the `MarketDataProvider` pattern (`services/calendar/`): a
  `NullEconomicCalendarProvider` (the disabled default) and a config-seeded
  `StaticEconomicCalendarProvider`, with a live HTTP feed as a future drop-in.
- [x] (4) Fetch upcoming high-impact events for a window — **one calendar call per
  run**, reused across every pair (filtered to the events that affect each
  instrument); a calendar outage degrades to "no events known" and never fails a
  pair or the run.
- [x] (5) Inject an "upcoming high-impact events" block into `AnalysisContext` and
  the prompt so the model can widen stops / lower confidence near a release, and
  feed news proximity into the **deterministic quality gate** (a high-impact event
  inside the blackout window vetoes new trades for the affected instrument).
- [x] (4) `GET /api/v1/calendar` endpoint for the frontend banner (`?within_hours=`,
  1..168, default 24); guarded by an `ECONOMIC_CALENDAR_ENABLED` config flag (off →
  the null provider, so the endpoint returns `enabled: false` with no events and the
  pipeline behaves exactly as today).

### Iteration 11 - Real-time Streaming + Notifications (20 points) ✅ DONE
Goal: push updates instead of being polled, and deliver signals off-platform.
- [x] (5) In-process event bus (`services/events/`): the analysis and outcome
  controllers publish `signal.created`, `signal.closed`, and `run.finished` events
  — always *after* the commit, so the stream never announces a signal/close that
  didn't land. An `EventPublisher` ABC is the producer seam (a `NullEventBus` for
  tests, a future Redis/NATS backend for multi-replica scale-out); the concrete
  `EventBus` fans out to bounded per-subscriber queues and keeps a ring buffer for
  resume. Publishing is synchronous, non-blocking, and can never fail a run.
- [x] (5) `GET /api/v1/stream` Server-Sent Events endpoint streaming those events to
  connected clients (keep-alive heartbeat + `Last-Event-ID` resume; a slow client
  is disconnected and resumes from the replay buffer rather than growing memory).
  SSE over WebSockets because the flow is one-way server→client. The streaming
  loop is factored out (takes a plain `is_disconnected` callable) so it is
  unit-testable without a live ASGI server.
- [x] (4) `Notifier` ABC + `TelegramNotifier` concrete (`services/notifications/`,
  bot token + chat id in config), plus a `NullNotifier` default and a background
  `NotificationDispatcher` that consumes the bus and delivers — every send isolated
  so a Telegram outage never disturbs the pipeline.
- [x] (3) Notification preferences (min confidence, styles, actionable-only, which
  events) — a *pure*, unit-tested policy applied before dispatch.
- [x] (3) Config + health: a `notifications` health component reporting
  enabled/not_configured/down like the existing provider components. Off by default
  (`NOTIFICATIONS_ENABLED=false`) — the null notifier, so the path is inert.

### Iteration 12 - Risk & Position Sizing (10 points) ✅ DONE
Goal: turn a signal into an exact, account-aware trade.
- [x] (4) Pure `services/risk/position_sizing.py`: given account balance, risk %,
  entry, SL and the instrument's contract spec, compute position size, risk amount,
  and R:R to each TP. No IO, unit-tested. Lots round **down** to the lot step so
  rounding can only reduce risk, never exceed the budget.
- [x] (3) `POST /api/v1/risk/position-size` — stateless; no account data is stored.
- [x] (3) Per-instrument contract metadata (pip value, min lot, contract size) for
  XAUUSD, via a small in-code spec lookup (`services/risk/contracts.py`) behind a
  `get_contract_spec` seam — no migration for a single instrument, promotable onto
  `Pair` later behind the same seam.

**Subtotal (Iterations 6-12): 118 points**

**New Total: 203 points** 🚀

---

## 🏗️ Architecture (Iteration 1 deliverable)

```
app/
├── __init__.py               # Single source of truth: __version__
├── main.py                   # create_app() factory + global exception handlers
├── config.py                 # Settings (typed, validated, fail-fast)
├── logging_config.py         # Centralised logging (dictConfig, idempotent)
├── dependencies.py           # Cross-cutting FastAPI dependencies (Pagination, …)
│
├── schemas/                  # Wire-format Pydantic models — transport-agnostic
│   ├── common.py             # APIResponse[T], ErrorResponse, PaginatedResponse[T]
│   └── health.py             # HealthResponse, ComponentStatus (Literal states)
│
├── views/                    # FastAPI routers (V in MVC)
│   ├── __init__.py           # api_v1_router — bundles all sub-routers under /api/v1
│   ├── health.py             # GET /api/v1/health
│   ├── signals.py            # placeholder (Iteration 4)
│   ├── pairs.py              # placeholder (Iteration 4)
│   └── analysis.py           # placeholder (Iteration 4)
│
├── controllers/              # Business logic (Iteration 4)
├── models/                   # SQLAlchemy models (Iteration 2)
├── database/                 # Engine, sessions, repositories (Iteration 2)
│
├── services/                 # External integrations + pure computation (Iteration 3)
│   ├── __init__.py           # ServiceError — single base for all service failures
│   ├── market_data/          # Candle value object, MarketDataProvider ABC, TwelveDataProvider, factory
│   ├── indicators/           # IndicatorCalculator (pure) → IndicatorSnapshot
│   └── ai/                   # AIProvider template + GroqProvider/AnthropicProvider, SignalDraft, factory
│
└── tasks/                    # Background scheduling (Iteration 3)
    ├── scheduler.py          # Scheduler adapter over APScheduler AsyncIOScheduler
    └── analysis_job.py       # AnalysisJob (error-isolating wrapper) + placeholder pipeline
```

### Layering rules

| Layer | May import | May NOT import |
|---|---|---|
| `schemas/` | `pydantic`, stdlib | `fastapi`, `sqlalchemy`, services |
| `dependencies.py` | `fastapi`, schemas, config | controllers, services |
| `views/` | dependencies, schemas, controllers | services directly, `database/` directly |
| `controllers/` | services, repositories, schemas | `views/`, `fastapi` |
| `services/` | stdlib, third-party SDKs, schemas | `views/`, controllers |

This is what keeps the project deployable in pieces and testable without spinning up the framework.

### Response envelopes

All v1 responses follow a consistent shape so the frontend never has to special-case errors:

```jsonc
// Success
{ "success": true, "data": <T> }

// Paginated success
{ "success": true, "data": [<T>], "pagination": { "total": 95, "page": 2, "per_page": 20, "pages": 5 } }

// Error (incl. structured field errors for 422)
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "1 validation error(s)",
    "fields": [{ "loc": ["query", "page"], "msg": "input must be >= 1", "type": "greater_than_equal" }]
  }
}
```

`/api/v1/health` is the only exception — it returns the health doc directly so external monitors can ingest it without unwrapping.

### Configuration

`Settings` is fail-fast: typo a value in `.env` and the process refuses to start.

| Field | Type | Constraint |
|---|---|---|
| `app_env` | `Literal["development","staging","production","test"]` | rejects unknown values |
| `app_port` | `int` | `1 ≤ port ≤ 65535` |
| `ai_provider` | `Literal["groq","anthropic"]` | rejects unknown providers |
| `analysis_timeframe` | `Literal["1m","5m","15m","30m","1h","4h","1d"]` | rejects unknown timeframes |
| `analysis_interval_minutes` | `int` | `1 ≤ value ≤ 1440` |
| `analysis_candle_count` | `int` | `20 ≤ value ≤ 5000` |
| `active_pairs` | `list[str]` | CSV in env, normalised to upper-case, must be non-empty |
| `cors_allowed_origins` | `list[str]` | CSV in env, empty disables CORS |
| `database_pool_size` | `int` | `1 ≤ value ≤ 200` (default 10) |
| `database_max_overflow` | `int` | `0 ≤ value ≤ 500` (default 20) |
| `database_pool_recycle_seconds` | `int` | `60 ≤ value ≤ 86400` (default 1800) |
| `database_echo` | `bool` | log every SQL statement — dev only |
| `ai_temperature` | `float` | `0.0 ≤ value ≤ 2.0` (default 0.2 — near-deterministic) |
| `ai_max_tokens` | `int` | `256 ≤ value ≤ 8192` (default 1024) |
| `ai_timeout_seconds` | `float` | `0 < value ≤ 300` (default 30) |
| `twelve_data_base_url` | `str` | default `https://api.twelvedata.com` |
| `market_data_timeout_seconds` | `float` | `0 < value ≤ 120` (default 15) |
| `market_data_max_retries` | `int` | `0 ≤ value ≤ 10` (default 3) |
| `scheduler_enabled` | `bool` | run the analysis job on this instance (default true) |
| `scheduler_timezone` | `str` | default `UTC` |
| `scheduler_misfire_grace_seconds` | `int` | `1 ≤ value ≤ 3600` (default 60) |
| `stream_heartbeat_seconds` | `int` | `1 ≤ value ≤ 300` (default 15) — SSE keep-alive cadence |
| `stream_max_queue` | `int` | `1 ≤ value ≤ 10000` (default 100) — per-client SSE buffer; overflow → reconnect |
| `stream_replay_buffer` | `int` | `0 ≤ value ≤ 10000` (default 200) — ring buffer for `Last-Event-ID` resume |
| `notifications_enabled` | `bool` | off → null notifier (default false) |
| `notification_provider` | `Literal["telegram"]` | rejects unknown providers |
| `telegram_bot_token` / `telegram_chat_id` | `str` | required (validated) when notifications enabled |
| `notification_min_confidence` | `float` | `0.0 ≤ value ≤ 1.0` (default 0.7) |
| `notification_signal_types` | `list[str]` | CSV; subset of `scalp,swing` (empty = no style filter) |
| `notification_only_actionable` | `bool` | only `should_trade` signals notify (default true) |
| `notification_on_signal_created` / `notification_on_signal_closed` | `bool` | per-event toggles (default true) |

### App factory

`create_app(settings: Settings | None = None)` builds an isolated FastAPI instance. Tests get a fresh app per fixture, so they can flip env vars (e.g. `app_env="production"`) and verify behaviour without mutating module state.

### Domain models (Iteration 2.2 deliverable)

ORM models live in `app/models/`. A single `Base` + `TimestampMixin`
(`app/models/base.py`) is shared by every entity, and the package
`__init__.py` re-exports all models so importing `app.models` is enough
to register the full schema on `Base.metadata` (this is what Alembic
autogenerate scans). A naming convention is bound to the metadata so
generated constraint and index names are deterministic.

| Table | Purpose | Notable fields / constraints |
|---|---|---|
| `pairs` | Lookup of tradable instruments (e.g. `EURUSD`, `XAUUSD`) | `symbol` unique + indexed, `is_active` (soft-disable) |
| `analysis_runs` | One row per scheduled/manual pipeline execution | `status` + `trigger` are native PG enums; check constraint forces `finished_at >= started_at`; AI provider/model snapshotted for traceability |
| `signals` | AI-generated trade signals | `direction` enum, `confidence` ∈ [0,1] (CHECK), `entry_price`/`stop_loss`/`take_profit` as `Numeric(20,8)`, `indicators_snapshot` as JSONB, composite index `(pair_id, generated_at)` for the "latest signals per pair" query, unique `(pair_id, analysis_run_id)` so a single run can't emit duplicate signals for a pair |

Foreign-key behaviour:
- `signals.pair_id → pairs.id` is `ON DELETE CASCADE`. Removing a pair
  removes its signals.
- `signals.analysis_run_id → analysis_runs.id` is `ON DELETE SET NULL`.
  Run records have a shorter retention than signals, so the signal
  must outlive the run.

Money columns use SQLAlchemy `Numeric(20, 8)`, never `Float`. Float
arithmetic is unsuitable for prices: rounding errors compound across
pip-level operations and can change a signal's reported entry/SL/TP
between writes.

### Database (Iteration 2.1 deliverable)

The async SQLAlchemy engine and session factory live behind a single `Database` adapter (`app/database/connection.py`). It is constructed once by `create_app()` (sync — engine creation only allocates a pool, no connections are opened) and disposed during the FastAPI lifespan shutdown.

Pulling sessions:

```python
from app.dependencies import DBSessionDep   # AsyncSession

@router.get("/example")
async def handler(session: DBSessionDep) -> ...:
    # rollback on exception is handled by the dependency
    # commits are explicit — controllers own transaction boundaries
    ...
```

The health endpoint round-trips a `SELECT 1` to surface DB reachability:
- `database.status == "ok"` → pool reachable
- `database.status == "down"` → connect/select failed → overall status downgrades to `down`

For a local PostgreSQL-on-Windows setup, use the project-owned bootstrap files
in `db/`:

```powershell
cd backend
psql -U postgres -d postgres -f .\db\create_local_database.sql
alembic upgrade head
psql -U tradesignal_app -d tradesignal -f .\db\seed_pairs.sql
psql -U tradesignal_app -d tradesignal -f .\db\check_database.sql
```

Full step-by-step instructions are in `db/README.md`.

### Migrations (Iteration 2.3 deliverable)

Alembic owns the schema lifecycle. The configuration lives at the
backend root (`alembic.ini`, `migrations/`) and is wired to share two
things with the running application:

1. **`Settings.database_url`** — `migrations/env.py` resolves the URL
   via `get_settings()` rather than re-declaring it in `alembic.ini`,
   so a typo in `.env` is rejected by Pydantic instead of producing a
   confusing connect failure mid-migration.
2. **`Base.metadata`** — `target_metadata` points at the same registry
   the ORM models populate, which is the contract autogenerate relies
   on. Importing `app.models` registers every table; `compare_type`
   and `compare_server_default` are enabled so type/default drift is
   surfaced rather than silently ignored.

`env.py` runs migrations through an **async** engine
(`async_engine_from_config` + `connection.run_sync`) because the
application URL is `postgresql+asyncpg://…`. Maintaining a parallel
sync URL was rejected — every duplicated config field is a future
incident.

Common workflows (run from the `backend/` directory with the venv
active):

```bash
# Apply all pending migrations to the live database
alembic upgrade head

# Roll back the most recent migration (development only — production
# rollbacks are reviewed and applied through the deploy pipeline)
alembic downgrade -1

# Generate a new migration from model changes
alembic revision --autogenerate -m "describe the change"

# Render SQL without touching the database — useful for review and for
# DBAs who want to apply migrations through their own tooling
alembic upgrade head --sql > /tmp/upgrade.sql

# Inspect the revision graph
alembic history --verbose
alembic current
```

The first migration (`0001_initial_schema`) creates `pairs`,
`analysis_runs`, `signals`, the three native enums
(`analysis_run_status`, `analysis_run_trigger`, `signal_direction`),
and every check / unique / foreign-key / index named by the metadata
naming convention. Constraint names are deterministic (driven by the
convention bound on `Base.metadata`) so cross-database downgrades and
diff-driven autogenerate runs produce stable output.

### Repositories (Iteration 2.4 deliverable)

Persistence access goes through repositories
(`app/database/repository/`). Each ORM model has its own repository
class with a narrow, named query surface — controllers depend on those
named methods rather than building `select(...)` statements at the
call site, so query churn stays contained when the schema evolves.

| Repository | Notable methods |
|---|---|
| `BaseRepository[ModelT]` | `get`, `add`, `add_all`, `delete`, `delete_where`, `list`, `count`, `exists`, `flush` — generic primitives |
| `PairRepository` | `get_by_symbol` (case-insensitive), `list_active`, `list_all`, `upsert_by_symbol` (idempotent seed) |
| `SignalRepository` | `latest_for_pair`, `list_paginated` (with optional `selectinload(pair)`), `count_filtered`, `list_for_run`, `delete_expired` |
| `AnalysisRunRepository` | `list_recent`, `list_paginated`, `count_filtered`, `get_latest_successful` |

**Transaction boundaries are not the repository's concern.** Repos
stage work on the session (`session.add`, `session.execute(...)`) but
never commit and never roll back. The controller that owns the unit
of work decides when to commit, which is what lets one controller
batch multiple repository calls into a single atomic transaction.

Repos are wired into FastAPI via dependencies in
`app/dependencies.py`:

```python
from app.dependencies import PairRepositoryDep, SignalRepositoryDep

@router.get("/pairs/{symbol}")
async def get_pair(symbol: str, pairs: PairRepositoryDep):
    return await pairs.get_by_symbol(symbol)
```

Each `*RepositoryDep` resolves the request-scoped session, so multiple
repositories injected into the same handler share one session and
participate in the same transaction.

### Services + scheduler (Iteration 3 deliverable)

Iteration 3 builds the *analysis pipeline ingredients* — fetch data, compute
indicators, ask an AI — and the scheduler that will drive them. The
orchestration that strings them together (and persists signals) is the
analysis controller in Iteration 4; the service layer here deliberately knows
nothing about the database or FastAPI.

Every service failure derives from a single base, `ServiceError`
(`app/services/__init__.py`), so the future controller can catch one type and
record a failed `AnalysisRun` without importing `httpx`/`groq`/`anthropic`
exception types.

**Market data** (`app/services/market_data/`). A `Candle` value object
(immutable, `Decimal` OHLC, self-validating so a corrupt bar can't poison the
indicators) is the single shape the pipeline speaks. `MarketDataProvider` is
the ABC; `TwelveDataProvider` is the concrete adapter that hides Twelve Data's
quirks — symbol mapping (`EURUSD → EUR/USD`), interval mapping (`1h → 1h`,
`1d → 1day`), errors-in-HTTP-200 bodies, and newest-first ordering. Transient
failures (timeouts, 5xx, 429) retry with exponential backoff; deterministic
ones (unknown symbol, malformed payload) raise immediately so the rate-limit
budget isn't wasted. `build_market_data_provider(settings)` is the factory.

**Indicators** (`app/services/indicators/`). `IndicatorCalculator.compute()` is
**pure** — candles in, an `IndicatorSnapshot` out, no IO. It reports numbers
(RSI, MACD, EMA/SMA, ATR, Bollinger) and leaves interpretation to the AI, so
the math is back-testable without an AI key. Each indicator is gated on having
enough history for its window (no NaN, no noisy library warnings), non-finite
floats collapse to `None`, and `to_storage_dict()` yields the JSON that lands
in `signals.indicators_snapshot`.

**AI providers** (`app/services/ai/`). A Template Method split: `BaseAIProvider`
owns prompt construction, JSON extraction (tolerant of code fences and
surrounding prose), validation into a `SignalDraft`, and the "a directional
call needs an entry" rule — *once*. Each concrete provider (`GroqProvider`,
`AnthropicProvider`) implements only `_complete()` and translates its SDK's
errors into `AIRequestError`. A `SignalDraft` is **not** a persisted `Signal`:
it carries no identity, and supports up to three take-profits (TP1/TP2/TP3) to
match the product. `build_ai_provider(settings)` is the factory.

**Scheduler** (`app/tasks/`). `Scheduler` wraps APScheduler's
`AsyncIOScheduler` with safe defaults: `max_instances=1` (an overrunning cycle
never doubles up), `coalesce=True` (missed slots collapse to one run), and a
misfire grace window. `AnalysisJob` wraps the pipeline with error containment —
a crashing cycle is logged, never propagated, so one failure can't kill the
schedule. `scheduler_enabled` lets you run the job on exactly one instance in a
horizontally-scaled deployment (running it everywhere would duplicate signals
and multiply provider cost). Until the Iteration-4 controller exists, a
`pipeline_not_configured` placeholder runs on cadence and announces itself.

**Lifecycle + DI.** External clients (market data, AI) and the scheduler are
constructed in the FastAPI **lifespan** (not `create_app`), so lightweight
unit tests never spin up real SDK/HTTP clients. They are stashed on
`app.state` and exposed via `MarketDataProviderDep`, `AIProviderDep`, and
`SchedulerDep` for the Iteration-4 controllers. Shutdown stops the scheduler
and `aclose()`s each provider. The health endpoint now reports `scheduler`,
`market_data`, and `ai_provider` components (the scheduler distinguishes
"enabled but not running" → `down` from "disabled by config" → `not_configured`).

### Analysis controller (Iteration 4.1 deliverable)

The `AnalysisController` (`app/controllers/analysis_controller.py`) is the
orchestration the Iteration-3 services were built for: for each active pair it
fetches candles → computes indicators → asks the AI → drafts a signal, then
records the run ledger and the signals it produced. It replaces the
`pipeline_not_configured` placeholder as the scheduled job's pipeline, and is
constructed once in the lifespan and stashed on `app.state` (exposed via
`AnalysisControllerDep` for the upcoming manual-trigger endpoint).

Load-bearing design decisions:

- **The controller owns transaction boundaries; services and repositories do
  not.** It composes repositories (which only stage work) and decides when a
  unit of work commits.
- **No transaction is held open across network IO.** A run is split into three
  short transactions — open the `RUNNING` ledger row → *(fan out across pairs:
  market-data + AI calls, owning no DB connection)* → persist signals and stamp
  the terminal status — so a minutes-long cycle never pins a pooled connection
  while waiting on third parties. Signals and the final ledger update share one
  transaction, so the reported counts can never disagree with the rows
  committed.
- **Per-pair failures are isolated.** Each pair is analysed defensively; an
  expected `ServiceError` (provider down, insufficient candles, unparseable AI
  reply) fails just that pair, an unexpected exception is contained too but
  logged with a traceback. The run's terminal status reflects the mix —
  `SUCCESS` (all analysed, or no active pairs), `PARTIAL` (some failed), or
  `FAILED` (all failed) — which is exactly the distinction `AnalysisRun.status`
  carved out `PARTIAL` to express.
- **It manages its own sessions via the `Database` adapter**, not a
  request-scoped one, because a run is a background unit of work with no HTTP
  request behind it — which is also what keeps it reusable from a future
  manual-trigger endpoint that dispatches it as a background task.

Two boundary decisions worth calling out: only **directional** (`buy`/`sell`)
drafts become `Signal` rows — a `neutral` draft is a successful "no trade this
cycle" analysis, not a signal, and the `signals` table enforces
`entry_price NOT NULL` for actionable trades. And because the current schema
has a single `take_profit` column, only **TP1** is persisted; surfacing
TP1/TP2/TP3 is a deliberate schema-change follow-up rather than silent data
loss.

### Signal controller (Iteration 4.2 deliverable)

The `SignalController` (`app/controllers/signal_controller.py`) is the read-side
counterpart: it serves the signal queries the frontend paginates over
(`list_signals`, `get_signal`, `list_latest_for_pair`, `list_for_run`). Two
deliberate contrasts with the analysis controller make the layering legible:

- **Request-scoped, not session-owning.** A read lives entirely inside one HTTP
  request, so the controller takes already-constructed, session-sharing
  repositories (composed in `app/dependencies.py` as `SignalControllerDep`) and
  borrows the request transaction — it does *not* take the `Database` adapter.
  The analysis controller owns sessions precisely because it has no request.
- **It returns wire schemas, not ORM rows.** The ORM `Signal` is mapped to
  `schemas.signal.SignalResponse` **inside the open session**, so reading the
  eagerly-loaded `pair` (the relationship is `lazy="joined"`) is free and never
  risks a lazy load against a closed session. The view layer therefore touches
  no ORM objects.

Supporting types, both transport-agnostic so the view owns the HTTP mapping:
`controllers.results.Page[T]` (a page slice + total count, no presentation
concerns) and `controllers.exceptions.ResourceNotFoundError` (raised when a
signal id or pair symbol doesn't resolve — mapped to a 404 in one place). Money
fields cross the wire as JSON **strings** (`Decimal`), keeping the "never float
for prices" discipline all the way out to the client.

### Routers (Iteration 4.3 deliverable)

The v1 API surface (`app/views/`). Routers are deliberately thin: they translate
HTTP (path/query params, pagination, status codes) and wrap controller output in
the shared response envelope — every line of business logic stays in the
controllers. A view imports controllers and schemas only; it never reaches into
a repository or the database (the layering rule that keeps the HTTP layer
swappable and the logic framework-free).

| Method + path | Backed by | Returns |
|---|---|---|
| `GET /api/v1/signals` | `SignalController.list_signals` | `PaginatedResponse[SignalResponse]` — `?pair=` and `?run_id=` filters |
| `GET /api/v1/signals/{signal_id}` | `SignalController.get_signal` | `APIResponse[SignalResponse]` (404 if unknown) |
| `GET /api/v1/pairs` | `PairController.list_pairs` | `APIResponse[list[PairResponse]]` — `?include_inactive=` |
| `GET /api/v1/pairs/{symbol}` | `PairController.get_pair` | `APIResponse[PairResponse]` (404 if unknown) |
| `GET /api/v1/pairs/{symbol}/signals` | `SignalController.list_latest_for_pair` | `APIResponse[list[SignalResponse]]` — `?limit=` |
| `GET /api/v1/analysis/runs` | `AnalysisRunController.list_runs` | `PaginatedResponse[AnalysisRunResponse]` — `?status=` |
| `GET /api/v1/analysis/runs/{run_id}` | `AnalysisRunController.get_run` | `APIResponse[AnalysisRunResponse]` (404 if unknown) |
| `GET /api/v1/analysis/runs/{run_id}/signals` | `SignalController.list_for_run` | `APIResponse[list[SignalResponse]]` |
| `POST /api/v1/analysis/runs` | `AnalysisController.run_manual` | `202` + `APIResponse[AnalysisRunAccepted]` |
| `GET /api/v1/performance` | `PerformanceController.get_performance` | `APIResponse[PerformanceResponse]` — `?pair=`/`?signal_type=`/`?from=`/`?to=` filters |
| `GET /api/v1/calendar` | `CalendarController.get_upcoming` | `APIResponse[CalendarResponse]` — upcoming high-impact events; `?within_hours=` (1..168, default 24) |
| `GET /api/v1/stream` | `EventBus` (via the SSE view) | `text/event-stream` — live `signal.created`/`signal.closed`/`run.finished` events; `Last-Event-ID` header (or `?last_event_id=`) resumes |
| `POST /api/v1/risk/position-size` | `RiskController.size_position` | `APIResponse[PositionSizeResponse]` — stateless sizing (lots, real risk, R:R + profit per TP); `404` for an unknown instrument |

Two read controllers were added so the pairs and analysis routers stay
layering-compliant: `PairController` (pairs are small and enumerable, so its
list is unpaginated) and `AnalysisRunController` (the *query* companion to the
write-side `AnalysisController`, splitting reads of the run ledger from the
orchestrator that writes it).

`POST /analysis/runs` dispatches the pipeline as a **background task** and
returns `202` immediately — a full cycle spans every pair's market-data and AI
calls and would otherwise pin the request open for minutes; the client polls
`GET /analysis/runs` to observe it. It intentionally bypasses the scheduler's
single-instance guard (an operator-initiated run may overlap a scheduled one);
each run is its own ledger row and the `(pair_id, analysis_run_id)` constraint
still prevents duplicate signals within a run.

Not-found is handled centrally (see below): controllers raise the
framework-agnostic `ResourceNotFoundError` and one handler maps it to a `404`.

### Validation + error handling (Iteration 4.4 deliverable)

**Validation is layered**, each layer owning what it can prove:

1. **Edge (FastAPI + pydantic).** Path/query/body are validated before a handler
   runs — bad types, out-of-range pagination (`page ≥ 1`, `per_page ≤ 100`),
   malformed UUIDs, unknown `?status=` values. Failures become a `422` with one
   structured entry per field, so the frontend can render per-field messages.
2. **Domain invariants (models/services).** `Settings` is fail-fast at boot;
   `Candle` and `SignalDraft` self-validate so a corrupt bar or an out-of-range
   confidence can't propagate. These are enforced once, where the data is born.
3. **Controller resolution.** Inputs that name a concrete resource (a signal id,
   a pair symbol) raise `ResourceNotFoundError` when they don't resolve.

**Error handling is centralised** in `app/error_handlers.py` —
`register_exception_handlers(app)` is the single place that maps every failure
to the shared `ErrorResponse` envelope, so the policy is auditable in one file
rather than scattered across handlers. Domain and service errors stay
framework-agnostic (no HTTP status leaks into controllers/services); this module
is the boundary that translates them, with a stable client-facing code
vocabulary (`ErrorCode`):

| Raised | HTTP | `code` | Client sees |
|---|---|---|---|
| `RequestValidationError` | 422 | `VALIDATION_ERROR` | per-field `fields[]` |
| `ResourceNotFoundError` | 404 | `NOT_FOUND` | the identifier it supplied |
| `RateLimitError` | 429 | `RATE_LIMITED` | generic "retry shortly" |
| `ServiceError` (other) | 503 | `SERVICE_UNAVAILABLE` | generic; cause logged |
| `OperationalError` (DB) | 503 | `SERVICE_UNAVAILABLE` | generic; cause logged |
| `DatabaseConnectionError` | 503 | `SERVICE_UNAVAILABLE` | generic; cause logged |
| `HTTPException` | as-is | `HTTP_{code}` | framework detail |
| any other `Exception` | 500 | `INTERNAL_ERROR` | message **only in dev** |

The split between "expected" and "infrastructure" errors is deliberate:
not-found echoes the caller's own identifier (safe, useful), while upstream and
database failures return a generic message and log the real cause — provider
error text and SQL never reach the client. `OperationalError` (couldn't reach
the database) is surfaced as a retryable `503` rather than a blanket `500`, and
unexpected exceptions only reveal their message in development.

Database-unreachable comes in two shapes, and both must land on the same `503`.
SQLAlchemy's `OperationalError` covers the *wrapped*, driver-agnostic case, but
asyncpg can also raise its own `PostgresConnectionError` **unwrapped** when a
pooled connection dies mid-operation — that is neither a SQLAlchemy
`OperationalError` nor even a `DBAPIError`, so a handler keyed on those alone
would let it fall through to a misleading `500`. Rather than teach the HTTP layer
about the driver, the `Database` adapter (the one module that owns asyncpg)
normalises connection-level failures to a framework-agnostic
`DatabaseConnectionError`; the error layer maps that to `503` with a driver-free
import. Query/programming errors are deliberately *not* normalised — they are
bugs, not transient outages, and must keep their `500`.

### Quality: controller/route tests (Iteration 5 deliverable)

Iteration 5 closes the test gap the earlier iterations left for the business
layer, and pins the HTTP contract end-to-end — without ever requiring a live
Postgres or a real provider network call. The strategy mirrors the layering:
test each layer against the seam below it.

* **Read controllers — unit, mocked repositories.** `SignalController`,
  `PairController` and `AnalysisRunController` are exercised against `AsyncMock`
  repositories. Their job is orchestration (resolve a symbol → id, drive the
  repos, map ORM → wire, raise `ResourceNotFoundError` for unknown ids), all of
  which is observable through the calls they make and the schemas they return.
  Tests assert the empty-page short-circuit, the status-literal → ORM-enum cast,
  unknown-resource 404 semantics, and that `Decimal` money survives the mapping.

* **`AnalysisController` — unit, in-memory persistence.** The orchestrator is the
  hardest to test (three transactions wrapped around fan-out network IO), so the
  three repository classes are swapped at the module boundary for in-memory fakes
  backed by a shared store, and the `Database`/providers are injected fakes. This
  pins the contract that actually matters: which terminal status each outcome mix
  yields (`SUCCESS`/`PARTIAL`/`FAILED`), that a `neutral` draft is a successful
  no-signal, that one pair's failure (expected *or* unexpected) never discards
  the others' signals, that only TP1 is persisted, and that a finalisation blip
  stamps the stuck run `FAILED` and re-raises.

* **Routes — integration, stubbed controllers.** Every v1 route is driven through
  the real ASGI app (envelope shaping, pagination meta, the central
  `ResourceNotFoundError` → 404 and `DatabaseConnectionError` → 503 mapping, the
  `202` + background-task dispatch for the manual trigger) with the controllers
  overridden via `app.dependency_overrides`. This tests the view layer's actual
  responsibility — HTTP translation — without re-testing business logic or
  touching a database.

Test doubles live in `tests/_stubs.py` (the `FakeDatabase`) and
`tests/_factories.py` (transient ORM builders); both are underscored so pytest
does not collect them. **Live-Postgres round-trips and real provider network
calls remain deliberately deferred** (see the note under the verification
status) — these tests deepen confidence in the logic and the wire contract, not
the infrastructure bindings.

### Per-style timeframes + candle cache (Iteration 6 deliverable)

Two changes sharpen the signal engine without touching its shape. First, each
style is framed on its own timeframe set: `scalp_timeframes` (default
`5m,15m,1h,4h`) and `swing_timeframes` (default `4h,1d`). `Settings` exposes an
ordered-unique `analysis_timeframes` *property* — the union of the two — so the
controller's fetch loop and the run ledger are unchanged, and overlapping a frame
across styles (the shared `4h`) costs nothing. The AI prompt now labels each
timeframe block with its role (`[SCALP frame]`/`[SWING frame]`/`[SCALP+SWING
frame]`) and instructs the model to anchor each style's levels to its own frame
while still reading every timeframe for bias.

Second, `CachingMarketDataProvider` (`services/market_data/cache.py`) wraps the
concrete provider behind the same `MarketDataProvider` ABC — so the controller is
oblivious — and serves candles from memory until a new bar closes. Freshness is
**bar-boundary aligned**, not a wall-clock TTL: a series is reused only while
`now` is in the same bar window as the fetch (windows are epoch-aligned, which —
since every timeframe divides a day — coincides with the UTC-midnight boundaries
the provider closes on). A per-`(symbol, timeframe)` `asyncio.Lock` collapses
fetch stampedes when a manual run overlaps the scheduled one. Net effect: a
typical cycle re-fetches only the fast frames (`5m`, `15m`) and reuses `1h`/`4h`/
`1d` between bars — well inside the free-tier ceiling.

### Signal outcome tracking (Iteration 7 deliverable)

This is the keystone of the measurement work: every signal now records what price
*did*, not just what the AI *said*. The model gains an `outcome` native enum
(`open` → one of `hit_tp1`/`hit_tp2`/`hit_tp3`/`hit_sl`/`expired`/`cancelled`),
plus `closed_at`, `realized_r`, `mfe`/`mae` (in R), and `last_evaluated_at`
(migration `0004`).

The verdict comes from a **pure** `OutcomeEvaluator` (`services/outcome/`): feed
it an open position (plain values, not an ORM row) and the candles since
generation, and it returns the outcome plus R figures, deterministically and
without IO — so it is fully back-testable. It models a bracket held to its ladder,
scanned oldest→newest: the position closes on the first candle to reach the stop
or a take-profit; a candle that spans **both** resolves conservatively to the stop
(the track record never claims an unprovable win); a candle reaching several TPs
at once records the furthest; an untouched-but-expired signal is marked to market.
R requires a stop (to define risk) — a stop-less signal is still classified but
its R fields stay `None`. `mfe`/`mae` update every cycle, even while open.

Persistence mirrors the analysis side exactly. `OutcomeController` owns the
sessions and transaction boundaries — snapshot the active pairs, fetch the lowest
configured timeframe once per pair (finest fills, one call) **owning no session**,
then load open signals, evaluate, and `mark_outcome` in a single committed
transaction — with per-pair fetch failures isolated. The thin `OutcomeJob`
(`tasks/outcome_job.py`) wraps `run_scheduled` with error containment just like
`AnalysisJob`, and runs on its own `OUTCOME_INTERVAL_MINUTES` cadence (default 5,
tighter than analysis so closes are detected promptly). `SignalRepository` gains
`list_open`, `mark_outcome`, and an `outcome` filter; `SignalResponse` surfaces
`outcome`/`realized_r`/`closed_at`, and `GET /api/v1/signals` accepts `?outcome=`.

### Performance & calibration API (Iteration 8 deliverable)

This turns the outcome records into a **track record the frontend can chart**.
The arithmetic lives in a **pure** `PerformanceCalculator`
(`services/performance/calculator.py`) — the aggregation counterpart to the
`OutcomeEvaluator`: feed it a set of `ClosedSignal` value objects and it returns
the summary, calibration table, and equity curve, deterministically and without
IO, so the maths is unit-tested directly rather than inferred from SQL shape.

A signal counts toward the record only once it is **closed with a defined R**
(terminal outcome *and* `realized_r` set) — open signals have no result, and a
stop-less signal has no risk to denominate R in. A "win" is `realized_r > 0`
(closed in profit), so win-rate, profit factor and calibration all share one
honest, R-based denominator. The calculator reports:

- **Summary** (overall and per `signal_type`): total, wins/losses, win-rate,
  total R, expectancy (avg R), gross profit/loss, and profit factor (`null` when
  there is no losing R — an infinite ratio the frontend labels rather than fakes).
- **Calibration**: five fixed 20-point confidence buckets, each with the mean
  *stated* confidence (the prediction) beside the realised hit-rate. All five are
  always returned for a stable chart x-axis.
- **Equity curve**: cumulative `realized_r` over the closed signals, oldest-close
  first.

`SignalRepository.list_closed_for_performance` is the lean query surface (terminal
+ R-scored rows, filtered by `pair`/`signal_type`/close-time window, ordered by
`closed_at`). The request-scoped `PerformanceController` resolves the pair symbol,
casts the wire `signal_type` to the ORM enum, maps the rows onto `ClosedSignal`
(reading scalar columns only — no lazy load), runs the calculator, and maps the
result onto `PerformanceResponse`. `GET /api/v1/performance` wraps it in the
shared envelope. In-memory aggregation is the deliberate choice: the closed set
for the current single-pair focus is small, and a pure calculator is far cheaper
to trust than hand-rolled aggregate SQL.

### Smarter, cheaper, more reliable AI (Iteration 9 deliverable)

Three changes close the learning loop and harden the model boundary, all without
leaking an SDK type past the service layer.

**Feedback loop.** The model is now shown its *own* recent results so it can
calibrate against reality rather than its priors. In the opening transaction the
controller snapshots each pair's recent closed signals per style
(`SignalRepository.list_recent_closed`) and folds them into a `PriorPerformance`
(closed count, win-rate, avg R, and a confidence *bias* = mean stated confidence −
realised win-rate). These ride on `AnalysisContext` and render as a compact "your
recent track record on this pair" block in the user prompt — omitted entirely when
there's no closed history, so the prompt is unchanged for a cold start.

**Structured output.** The provider boundary now returns a `CompletionResult`
(text + optional `TokenUsage`) from `_complete`, and `analyze` returns an
`AnalysisResult` (the dual draft + usage). The Anthropic provider forces a single
tool whose `input_schema` is the `DualSignalDraft` JSON schema, so the API
validates structure before we ever see the reply; the tool input is serialised
back to JSON so the base's tolerant extraction + Pydantic validation still runs
(defence-in-depth, and the fallback when a reply somehow carries no tool block).
Groq keeps JSON-mode. An unparseable signal is now near-impossible.

**Cost/usage tracking.** Each provider maps its SDK's token counts onto the
neutral `TokenUsage`; the controller sums them across the run and estimates a USD
cost via a small per-model pricing table (`services/ai/pricing.py`, fail-soft to
`None` for an unpriced model or missing usage). The totals land on
`analysis_runs.prompt_tokens`/`completion_tokens`/`cost_usd` (migration `0005`,
`cost_usd` is `Numeric(12, 6)` — money is never Float) and are surfaced on
`AnalysisRunResponse`. The controller only ever touches `TokenUsage` and a
`Decimal`, so no provider type reaches persistence or the view.

### Macro awareness + signal-quality gating (Iteration 10 deliverable)

This iteration makes a signal aware of the news that moves it and — just as
important — separates a directional **bias** from an **actionable trade**. Four
pure, independently-tested pieces, all additive (the news feature is off by
default, so an unconfigured deployment behaves exactly as before):

**Richer evidence.** The indicator calculator now reports *trajectory* and
*regime*, not just frozen levels: `rsi_14_prev` / `macd_histogram_prev` (so the
model sees momentum *turning*), `adx_14` + a `regime` label
(`trending`/`ranging`/`transitional`), and an `rsi_divergence` flag
(`bullish`/`bearish`). A new pure `StructureAnalyzer` (`services/structure/`)
computes the actual levels a trader anchors to — swing highs/lows, nearest
support/resistance to the last close, and the range — and the prompt hands them
to the model so "anchor to structure" stops contradicting "don't invent levels".

**Quality gate (bias vs. actionable).** A pure `SignalGate`
(`services/signal_quality/`) turns each bias into a verdict: it computes the
reward:risk to TP1, raises **hard vetoes** for the textbook traps (reward:risk
below the configurable floor, fighting a *trending* higher-timeframe market, a
high-impact event inside the news blackout), and blends a `quality_score` ∈ [0,1].
The verdict lands on three new `signals` columns (migration `0006`):
`should_trade` (the actionable flag, indexed), `quality_score`, and an explainable
`quality_snapshot` (reward:risk, the gate's reasons, and the model's own
self-reported `risks`). All surfaced on `SignalResponse`.

**Trap-check.** `SignalDraft` gains a `risks` array and the prompt requires the
model to name how each trade could fail. The *enforcement* is the deterministic
gate, not the self-report — a single LLM call (no second round-trip), so it adds
no cost or failure mode while the veto can't be talked out of by an overconfident
model.

**News awareness.** An `EconomicCalendarProvider` family (`services/calendar/`)
mirrors the market-data pattern: ABC + null + static + factory, behind
`ECONOMIC_CALENDAR_ENABLED`. The analysis controller fetches upcoming events
**once per run**, filters them to each instrument, renders them into the prompt,
and feeds news proximity into the gate. `GET /api/v1/calendar` exposes them for the
frontend banner (`enabled` distinguishes "feature off" from "nothing scheduled").

### Real-time streaming + notifications (Iteration 11 deliverable)

The platform stops being purely *polled*: the pipelines now **push** what they
do, both to open browsers and off-platform. One in-process event bus is the spine;
two independent consumers hang off it.

**Event bus** (`services/events/`). The analysis and outcome controllers publish
domain events — `signal.created`, `signal.closed`, `run.finished` — and crucially
do so **only after the commit** (the finalise transaction returns the persisted
rows, which are then projected to JSON-serialisable payloads), so the stream can
never announce a signal or close that didn't actually land. Publishing is a plain
synchronous call wrapped so a bus error can never undo a committed run. The
`EventPublisher` ABC is the producer seam — a `NullEventBus` keeps controllers
testable and publishing inert where streaming is irrelevant, and is the single
point a future Redis/NATS backend slots into for multi-replica scale-out (the same
provider-swap pattern as market data/calendar). The concrete `EventBus` fans each
event out to **bounded** per-subscriber queues (a slow consumer is *dropped*, not
allowed to apply backpressure to the pipeline) and retains a ring buffer of recent
events for `Last-Event-ID` resume. Ids are a process-local monotonic counter.

**Streaming** (`GET /api/v1/stream`). A Server-Sent-Events endpoint — SSE not
WebSockets, because the flow is strictly one-way server→client, rides plain HTTP,
and reconnects + resumes natively. Each connection subscribes, replays anything
missed since its `Last-Event-ID` (header, or `?last_event_id=` for non-browsers),
then streams live events with a keep-alive comment every
`STREAM_HEARTBEAT_SECONDS` so idle proxies don't hang up. A client that overflows
its bounded queue is sent a `reconnect` nudge and disconnected; it reconnects and
resumes from the replay buffer rather than the server growing memory for it. The
streaming loop is a free function taking a plain `is_disconnected` callable, so the
whole lifecycle (replay → heartbeat → live → slow-consumer reconnect) is
unit-tested without a live server.

**Notifications** (`services/notifications/`). The off-platform sink mirrors the
other provider families: a `Notifier` ABC behind `build_notifier`, with a
`NullNotifier` default (the whole path inert unless enabled) and a
`TelegramNotifier` that posts to the Bot API `sendMessage` (bot token + chat id —
the "chatbot id" an operator drops in to go live; HTML-escaped, error-mapped to
`NotificationError`, `httpx.MockTransport`-tested). A pure, unit-tested
`NotificationPreferences` decides *which* events notify (min confidence, styles,
actionable-only, per-event toggles) and `render` projects an event onto a
channel-agnostic `NotificationMessage`. The `NotificationDispatcher` is the thin
bus→notifier bridge: a single background task started in the lifespan (only when
enabled), subscribing **synchronously in `start()`** so no post-start event is
missed, with every delivery isolated so a Telegram outage never disturbs the
pipeline or stops later notifications. Health gains a `notifications` component
(enabled+running → `ok`, enabled-but-stopped → `down`, disabled/absent →
`not_configured`), exactly like the scheduler.

Everything is **off by default and additive**: with `NOTIFICATIONS_ENABLED=false`
the notifier is the null one and no dispatcher runs; the event bus is always
constructed (cheap, inert without subscribers) so `GET /api/v1/stream` always
works — it simply has nothing to push until a run completes.

### Risk & position sizing (Iteration 12 deliverable)

This turns a signal into an **exact, account-aware order**, and like the other
calculation services it is pure and IO-free — so the endpoint built on it is
stateless and stores no account data.

**Contract metadata** (`services/risk/contracts.py`). A small in-code
`ContractSpec` lookup (`get_contract_spec`) holds what sizing needs that the
signal can't supply: how a price move maps to money. For XAUUSD: a 100-oz standard
lot (so a $1 move is $100/lot), a 0.01 min lot / lot step, a $0.01 pip, and USD as
the quote currency. Adding columns + a migration to `pairs` for a single
instrument wasn't worth it; the lookup sits behind a seam it can be promoted onto
later without the controller changing. An unknown symbol returns `None` (the
controller raises the standard `ResourceNotFoundError` → 404) rather than guessing
a spec and mis-sizing.

**Sizer** (`services/risk/position_sizing.py`). A pure `compute_position_size`:
given balance, risk %, entry, stop and the spec, it returns the lot size whose
loss at the stop is at most the risk budget, plus units, real risk, notional,
per-pip value, and the R:R + projected profit to each take-profit. Two safety
properties are baked in and unit-tested: **lots round down** to the lot step (so
rounding can only ever risk *less*, and a trade too small to place rounds to zero
rather than over-risking), and `Decimal` is used throughout (never float for money
or prices). Distances are absolute, so the same maths serves long and short. The
P&L-in-quote-currency = account-currency assumption (true for XAUUSD→USD) is
documented; a cross-currency account is a future FX-factor extension, not silently
wrong.

**Controller + endpoint.** `RiskController` is the thinnest in the project — no
session, no repositories: resolve the spec, run the sizer, map value objects onto
the wire schema. `POST /api/v1/risk/position-size` validates the body at the edge
(positive balance/risk/prices, `stop ≠ entry` → 422), wraps the result in the
shared envelope, and persists nothing.

## 🧪 Run
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs in development:
- Swagger UI: <http://localhost:8000/api/docs>
- ReDoc: <http://localhost:8000/api/redoc>
- OpenAPI JSON: <http://localhost:8000/api/openapi.json>

(Disabled in production.)

## 🧪 Tests + Lint
```bash
# Tests cover config validation, schemas, dependencies, the Database adapter,
# health DB-probe behaviour, end-to-end app wiring; Iteration 2's ORM models,
# repository query surface (SQL compiled with literal binds), and Alembic
# migration rendering; and Iteration 3's market-data provider (httpx
# MockTransport: retries, error mapping, symbol/interval mapping), indicator
# calculator (structure, NaN handling, determinism), AI providers (prompt,
# JSON extraction, validation, SDK error wrapping), scheduler lifecycle, and
# the lifespan service wiring; and Iteration 5's controller unit tests
# (read controllers + the analysis orchestrator) and route integration tests.
pytest

# Lint + format
ruff check .
ruff format --check .

# Static type check (basic mode; config in pyrightconfig.json)
pyright
```

### ✅ Verification status (Iterations 1–12)
Last verified on 2026-06-06:
- `pytest` — **531 passed** (514 through Iteration 11, then Iteration 12's pure
  position sizer (clean size, short via absolute distances, round-down-keeps-risk,
  unaffordable→zero-lots, invalid-input guards), the contract-spec lookup
  (case-insensitivity, unknown→`None`, derived pip value), the `RiskController`
  mapping + unknown-pair 404, and the `POST /risk/position-size` route tests
  (success envelope, money-as-strings, 404, and the 422s for `stop == entry` and a
  non-positive balance))
- `ruff check .` — clean
- `ruff format --check .` — clean (135 files)
- `alembic upgrade head --sql` renders cleanly through `0006_signal_quality`
  (single linear head); the new quality-gate columns carry their convention names
  (`ck_signals_quality_score_in_unit_interval`, `ix_signals_should_trade`) and
  `should_trade` ships `NOT NULL DEFAULT true` so existing rows backfill atomically
- `pyright` — clean except one documented Anthropic-SDK stub friction (a plain
  `dict` tool definition vs the SDK's strict `ToolParam` union); the enforced gate
  remains `pytest` + `ruff`
- `create_app()` boots and registers `GET /api/v1/health`
- `alembic upgrade head --sql` renders the full schema with the three native
  enums created before the tables that reference them
- Lifespan integration test: scheduler starts, providers construct, health
  reports all components `ok`, and shutdown stops the scheduler and closes
  every client
- **Live smoke test (no database running):** the server boots, the scheduler
  starts, `GET /api/v1/health` returns `200` with `database: down`, request
  validation returns structured `422`s, an unknown route returns the `404`
  envelope, and a request that needs the database returns a retryable **`503`**
  (`SERVICE_UNAVAILABLE`) — the regression fixed this iteration, where a raw
  unwrapped asyncpg connection error previously surfaced as a misleading `500`

> **Deferred to later iterations on purpose:** live-Postgres round-trips and
> real Twelve Data / Groq / Anthropic network calls. The AI and market-data
> integrations are exercised with injected fake SDK clients and
> `httpx.MockTransport`; controller and route logic is tested against mocked
> repositories, in-memory persistence fakes, and `app.dependency_overrides` (see
> "Quality: controller/route tests" above). With no database reachable,
> `Database.healthcheck()` degrades gracefully to `False` rather than raising,
> and a request that reaches the database returns `503` rather than `500` —
> both confirmed at runtime.
>
> `pyright` runs in `basic` mode for editor/CI type feedback; the enforced
> green gate is `pytest` + `ruff` (a handful of known FastAPI
> `add_exception_handler` and SQLAlchemy/pandas typing-stub frictions remain in
> pre-existing code).

## 🔐 Env
Copy `.env.example` to `.env` and fill in the values:
```env
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
CORS_ALLOWED_ORIGINS=http://localhost:3000

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tradesignal
# DATABASE_POOL_SIZE=10
# DATABASE_MAX_OVERFLOW=20
# DATABASE_POOL_RECYCLE_SECONDS=1800
# DATABASE_ECHO=false

AI_PROVIDER=groq
AI_MODEL=llama-3.3-70b-versatile
AI_API_KEY=your_api_key_here
# AI_TEMPERATURE=0.2
# AI_MAX_TOKENS=1024
# AI_TIMEOUT_SECONDS=30

MARKET_DATA_PROVIDER=twelve_data
TWELVE_DATA_API_KEY=your_key_here
# TWELVE_DATA_BASE_URL=https://api.twelvedata.com
# MARKET_DATA_TIMEOUT_SECONDS=15
# MARKET_DATA_MAX_RETRIES=3

ANALYSIS_INTERVAL_MINUTES=15
ANALYSIS_CANDLE_COUNT=200
ANALYSIS_TIMEFRAME=1h
ACTIVE_PAIRS=XAUUSD,GBPUSD,EURUSD

# Scheduler — disable on API-only replicas so the analysis job runs on
# exactly one instance in a horizontally-scaled deployment.
# SCHEDULER_ENABLED=true
# SCHEDULER_TIMEZONE=UTC
# SCHEDULER_MISFIRE_GRACE_SECONDS=60
```
