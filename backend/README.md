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
- [ ] (5) Add models (`pair`, `signal`, `analysis_run`)
- [ ] (5) Setup Alembic and first migration
- [ ] (5) Implement repository layer

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
