# ⚙️ Backend Setup - TradeSignal AI

## ✅ Goal
Build a scalable **FastAPI backend** with scheduler, indicator pipeline, AI provider abstraction, and PostgreSQL persistence.

## 📌 Latest Versions (verified on 2026-04-22)
- `fastapi`: `0.136.0`
- `uvicorn`: `0.45.0`
- `pydantic`: `2.13.3`
- `pydantic-settings`: `2.14.0`
- `sqlalchemy`: `2.0.49`
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

### Iteration 2 - Data Layer (20 points)
- [x] (5) Setup SQLAlchemy async engine/session
- [x] (5) Add models (`pair`, `signal`, `analysis_run`)
- [x] (5) Setup Alembic and first migration
- [x] (5) Implement repository layer

### Iteration 3 - Services + AI + Scheduler (21 points)
- [ ] (6) Implement market data service (Twelve Data)
- [ ] (5) Implement indicators calculator
- [ ] (5) Implement AI provider pattern (`groq` + `anthropic`)
- [ ] (5) Add APScheduler job and startup wiring

### Iteration 4 - Business Logic + API Endpoints (18 points)
- [ ] (6) Implement analysis controller
- [ ] (5) Implement signal controller
- [ ] (4) Implement signals/pairs/analysis routers
- [ ] (3) Add validation and error-handling strategy

### Iteration 5 - Quality + Delivery (12 points)
- [ ] (4) Unit tests for controllers/services
- [ ] (3) Integration tests for core routes
- [ ] (3) Lint and static checks
- [ ] (2) Docker polish + runtime docs

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
├── services/                 # External integrations (Iteration 3)
└── tasks/                    # APScheduler jobs (Iteration 3)
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
# health DB-probe behaviour, and end-to-end app wiring.
pytest

# Lint + format
ruff check .
ruff format --check .
```

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

MARKET_DATA_PROVIDER=twelve_data
TWELVE_DATA_API_KEY=your_key_here

ANALYSIS_INTERVAL_MINUTES=15
ANALYSIS_CANDLE_COUNT=200
ANALYSIS_TIMEFRAME=1h
ACTIVE_PAIRS=XAUUSD,GBPUSD,EURUSD
```
