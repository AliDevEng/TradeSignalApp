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

**Total: 85 points** 🚀

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

### ✅ Verification status (Iterations 1–5)
Last verified on 2026-06-02:
- `pytest` — **274 passed** (208 from Iterations 1–3, +66 added in Iteration 5:
  controller unit tests, route integration tests, and the DB-connection-error
  normalisation tests — covering Iteration 4's controllers/routes)
- `ruff check .` — clean
- `ruff format --check .` — clean (78 files)
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
