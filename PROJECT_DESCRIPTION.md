# TradeSignal AI — Project Description

> An AI-driven trading-analysis platform that automatically analyzes the gold and
> Forex markets, generates professional trade signals (Entry, SL, TP1, TP2, TP3),
> and — going forward — **measures its own track record** so quality can be proven.

> **Status:** This document describes the *actual* implementation (backend
> Iterations 1-8, frontend Iterations 1-8) plus the *planned* build-out (backend
> Iterations 6-11, frontend Iterations 9-13). Planned fields and endpoints are
> clearly marked *(planned — Iteration X)*.

---

## 1. Project Overview

TradeSignal AI is a fullstack web application that automatically pulls market data
for a trading pair across **multiple timeframes** (5m, 15m, 1h, 4h, 1d), computes
technical indicators per timeframe, and sends it all to an AI model for a
**top-down, multi-timeframe analysis**.

Unlike a simple "buy/sell/neutral" system, the platform runs in an **always-on**
mode: for every run the AI produces *two* directional ideas per pair — a short-term
**scalp** (framed on the lower timeframes, tight stop, near targets) and a **swing**
(framed on the higher timeframes, wider stop, extended targets). Lack of conviction
is expressed as a **low confidence value**, never as a refusal to trade. Each open
signal is fed back into the next run so the model can **keep or adjust** the idea
against fresh data.

### Current focus: Gold only (XAUUSD)
Twelve Data's free tier has a per-minute limit that is consumed by the
multi-timeframe fetch for a single pair (five calls per pair per run). For now
`ACTIVE_PAIRS` is therefore narrowed to **XAUUSD**. The architecture remains fully
multi-pair — nothing hard-codes gold; only the active set is narrowed.

### Business goals
- **Phase 1:** A working product with automated signal generation *(done)*
- **Phase 1.5:** A measurable, self-improving, real-time platform *(in progress — see §14)*
- **Phase 2:** User registration and paid subscriptions
- **Phase 3:** Mobile app (React Native / Expo)

---

## 2. Tech Stack

### Frontend
| Component | Choice | Rationale |
|---|---|---|
| Framework | Next.js 16 (App Router) | SSR for SEO, file-based routing, Vercel deploy |
| Language | TypeScript | Type safety, code quality, auto-completion |
| Styling | Tailwind CSS 4 | Utility-first, fast development |
| Charts | Lightweight Charts (TradingView) | Professional financial charts |
| State | Zustand | Simple, scalable state management + `localStorage` persistence |
| HTTP client | Axios + React Query | Caching, loading states, auto-refresh, error handling |
| Forms | React Hook Form + Zod | Validation with TypeScript integration |
| Icons | lucide-react | Consistent icon set |
| Tests | Vitest + React Testing Library + Playwright | Unit/component + route smoke |

### Backend
| Component | Choice | Rationale |
|---|---|---|
| Framework | Python 3.12+ + FastAPI | Async, fast, automatic OpenAPI docs |
| Scheduling | APScheduler | Runs analysis + outcome jobs on cadence, no Redis required |
| Indicators | pandas-ta-classic | RSI, MACD, EMA/SMA, Bollinger, ATR |
| ORM | SQLAlchemy 2.0 (async) | Database-agnostic, async sessions |
| Migrations | Alembic | Schema version control |
| Validation | Pydantic v2 + pydantic-settings | Request/response validation, fail-fast config |

### AI layer
| Component | Choice | Rationale |
|---|---|---|
| Dev model | Groq API (Llama 3.3 70B) | Free during development, fast |
| Prod model | Claude Sonnet (Anthropic) | Strong reasoning, structured responses |
| Strategy | Provider Pattern + env-var switching | Swap models without code changes |

### Data source
| Component | Choice | Rationale |
|---|---|---|
| Market data | Twelve Data API | Supports XAUUSD and more, free tier |
| Format | OHLCV per timeframe | Multi-timeframe (5m → 1d) for scalp + swing |

### Database
| Component | Choice |
|---|---|
| Database | PostgreSQL 16 (JSONB, native enums) |
| Driver | asyncpg |

### DevOps
| Component | Choice |
|---|---|
| Frontend deploy | Vercel |
| Backend deploy | Railway / VPS *(target not yet settled)* |
| Environment | `.env` files per environment |
| Version control | GitHub (monorepo) |
| Containerization | Docker *(deferred until the deploy target is settled)* |

---

## 3. Project Structure (Monorepo — actual)

```
TradeSignalApp/
├── PROJECT_DESCRIPTION.md
├── README.md
│
├── frontend/                       # Next.js 16 + React 19 + TypeScript
│   ├── README.md                   # Frontend plan + iterations
│   ├── package.json
│   ├── playwright.config.ts
│   ├── vitest.config.ts
│   ├── e2e/                         # Playwright route smoke
│   └── src/
│       ├── app/                    # App Router
│       │   ├── layout.tsx, page.tsx (dashboard), providers.tsx
│       │   ├── error.tsx, global-error.tsx, loading.tsx, not-found.tsx
│       │   ├── robots.ts, sitemap.ts
│       │   ├── dashboard/page.tsx
│       │   ├── signals/page.tsx + [signalId]/page.tsx
│       │   ├── pairs/[symbol]/page.tsx
│       │   └── analysis/page.tsx + [runId]/page.tsx
│       ├── components/             # ui/, charts/, signals/, analysis/,
│       │   │                       # dashboard/, layout/, health/, feedback/, common/
│       ├── hooks/                  # useTradeQueries, useHealthQuery, useNow
│       ├── lib/                    # formatters, trading, indicators, signalFilters,
│       │   │                       # signalMappers, analysisRun, analytics, monitoring
│       ├── services/               # api.ts, tradeService.ts, healthService.ts
│       ├── store/                  # signalStore, uiStore, notificationStore, toastStore
│       └── types/                  # signal, tradeApi, api, health
│
└── backend/                        # Python + FastAPI
    ├── README.md                   # Backend plan + iterations
    ├── alembic.ini
    ├── requirements.txt / requirements-dev.txt
    ├── db/                          # Local bootstrap SQL + README
    │   ├── create_local_database.sql, seed_pairs.sql, check_database.sql
    ├── migrations/                  # Alembic (env.py + versions/)
    ├── app/
    │   ├── __init__.py              # __version__
    │   ├── main.py                  # create_app() + lifespan
    │   ├── config.py                # Settings (typed, fail-fast)
    │   ├── dependencies.py          # FastAPI deps (sessions, repos, controllers)
    │   ├── error_handlers.py        # Central exception→envelope mapping
    │   ├── logging_config.py
    │   │
    │   ├── models/                  # SQLAlchemy: base, pair, signal, analysis_run
    │   ├── schemas/                 # Pydantic: common, health, pair, signal, analysis
    │   ├── controllers/             # analysis_controller, signal_controller,
    │   │                            # analysis_run_controller, pair_controller,
    │   │                            # results, exceptions
    │   ├── views/                   # Routers: health, signals, pairs, analysis
    │   ├── services/
    │   │   ├── market_data/         # Candle, MarketDataProvider ABC, TwelveDataProvider
    │   │   ├── indicators/          # IndicatorCalculator (pure) → IndicatorSnapshot
    │   │   └── ai/                  # AIProvider template + Groq/Anthropic,
    │   │       └── prompts/         # hedge_fund_analyst.md (editable persona)
    │   ├── tasks/                   # scheduler.py + analysis_job.py
    │   └── database/                # connection.py (Database adapter) + repository/
    └── tests/                       # unit/ + integration/
```

> **Planned additions** (see §14): `services/outcome/` (outcome evaluator),
> `services/calendar/` (economic calendar), `services/risk/` (position sizing),
> `services/notify/` (Telegram etc.), `tasks/outcome_job.py`, plus the router
> `views/performance.py` and the frontend route `app/performance/`.

---

## 4. Database Schema (actual + planned)

All money columns are `Numeric` (never `Float`) — float rounding compounds at the
pip level and can change a signal's reported Entry/SL/TP between writes.
`confidence` is stored as `Numeric(5,4)` in the range **0..1** (not 1-100). Status
and trigger fields are **native Postgres enums** so free-text writes are rejected at
the database layer.

### Table: `pairs`
```text
id              INTEGER PRIMARY KEY
symbol          VARCHAR(16) UNIQUE NOT NULL      -- "XAUUSD"
base_currency   VARCHAR(8)  NOT NULL             -- "XAU"
quote_currency  VARCHAR(8)  NOT NULL             -- "USD"
display_name    VARCHAR(64)                      -- "Gold / US Dollar"
is_active       BOOLEAN NOT NULL DEFAULT TRUE    -- soft-disable, preserves history
created_at / updated_at  TIMESTAMPTZ
-- (planned — Iteration 11) contract spec for position sizing:
--   pip_value, min_lot, contract_size
```

### Table: `analysis_runs`
```text
id              UUID PRIMARY KEY
status          ENUM analysis_run_status         -- pending|running|success|partial|failed
trigger         ENUM analysis_run_trigger        -- scheduler|manual
timeframe       VARCHAR(8) NOT NULL              -- primary (decision) timeframe
candle_count    INTEGER NOT NULL
started_at      TIMESTAMPTZ NOT NULL
finished_at     TIMESTAMPTZ                      -- CHECK: >= started_at
pairs_processed INTEGER NOT NULL DEFAULT 0       -- CHECK: >= 0
pairs_failed    INTEGER NOT NULL DEFAULT 0       -- CHECK: >= 0
ai_provider     VARCHAR(32)                      -- snapshot for traceability
ai_model        VARCHAR(64)
error_message   TEXT
created_at / updated_at  TIMESTAMPTZ
-- (planned — Iteration 8) AI cost/tokens:
--   prompt_tokens, completion_tokens, cost_usd
```
`status = partial` is deliberately distinct from `failed`: a run that succeeded for
some pairs but failed on others should not be reported as a total miss.

### Table: `signals`
```text
id                 UUID PRIMARY KEY
pair_id            INTEGER REFERENCES pairs(id) ON DELETE CASCADE
analysis_run_id    UUID REFERENCES analysis_runs(id) ON DELETE SET NULL
direction          ENUM signal_direction          -- buy|sell|neutral
signal_type        ENUM signal_type               -- scalp|swing
confidence         NUMERIC(5,4) NOT NULL          -- CHECK: 0..1
entry_price        NUMERIC(20,8) NOT NULL         -- CHECK: > 0
stop_loss          NUMERIC(20,8)
take_profit        NUMERIC(20,8)                  -- TP1
take_profit_2      NUMERIC(20,8)                  -- TP2
take_profit_3      NUMERIC(20,8)                  -- TP3
timeframe          VARCHAR(8) NOT NULL            -- timeframe the signal was framed on
rationale          TEXT                           -- the AI's desk note
indicators_snapshot JSONB                         -- indicators per timeframe, for back-test
generated_at       TIMESTAMPTZ NOT NULL
expires_at         TIMESTAMPTZ                    -- drives freshness badge + retention
ai_provider        VARCHAR(32)
ai_model           VARCHAR(64)
created_at / updated_at  TIMESTAMPTZ

-- (planned — Iteration 6) outcome tracking:
--   outcome          ENUM signal_outcome   -- open|hit_tp1|hit_tp2|hit_tp3|hit_sl|expired|cancelled
--   closed_at        TIMESTAMPTZ
--   realized_r       NUMERIC               -- actual R multiple (+2.3 / -1.0)
--   mfe / mae        NUMERIC               -- max favourable / adverse excursion
--   last_evaluated_at TIMESTAMPTZ
```
Key constraints:
- `UNIQUE(pair_id, analysis_run_id, signal_type)` — a run produces at most one
  scalp + one swing per pair.
- Indexes `(pair_id, generated_at)` and `(pair_id, signal_type, generated_at)` serve
  "latest signal(s) for pair X (per style)".

---

## 5. MVC Architecture and Data Flow

### Layering rules
| Layer | May import | May NOT import |
|---|---|---|
| `schemas/` | pydantic, stdlib | fastapi, sqlalchemy, services |
| `dependencies.py` | fastapi, schemas, config | controllers, services |
| `views/` | dependencies, schemas, controllers | services/database directly |
| `controllers/` | services, repositories, schemas | views, fastapi |
| `services/` | stdlib, SDKs, schemas | views, controllers |

### Analysis flow (automatic, every 15 minutes)
```
APScheduler → AnalysisJob (error-isolating wrapper)
    │
    ▼
AnalysisController.run_analysis()
    │  Phase 1 (short transaction): open a RUNNING row + snapshot the active pairs
    │          and their open scalp/swing signals (keep/adjust context)
    │
    ├─ Phase 2 (no DB, all network IO) — per pair:
    │     for each timeframe (5m,15m,1h,4h,1d):
    │        MarketDataProvider.fetch_candles()  → Twelve Data
    │        IndicatorCalculator.compute()       → IndicatorSnapshot (pure)
    │     AIProvider.analyze(AnalysisContext)    → DualSignalDraft (scalp + swing)
    │
    └─ Phase 3 (one transaction): write signals (scalp + swing per pair) +
            stamp the run's terminal status (SUCCESS/PARTIAL/FAILED)
```
No transaction is held open across network IO; per-pair failures are isolated (one
pair's provider timeout doesn't deprive the others of their signals).

### Outcome flow *(planned — Iteration 6)*
```
APScheduler → OutcomeJob (own cadence, OUTCOME_INTERVAL_MINUTES)
    │
    ├─ one cheap candle fetch for the active pair
    ├─ load open signals
    ├─ OutcomeEvaluator (pure): SL/TP touch + realized R per signal
    └─ persist outcomes in one transaction
```

### API request flow (frontend → backend)
```
Next.js  →  GET /api/v1/signals?pair=XAUUSD&page=1&per_page=20[&outcome=...]
         →  GET /api/v1/signals/{id}
         →  GET /api/v1/pairs/{symbol}/signals
         →  GET /api/v1/analysis/runs[/{id}[/signals]]
         →  GET /api/v1/performance        (planned — Iteration 7)
         →  GET /api/v1/stream  (SSE)        (planned — Iteration 10)
```

---

## 6. AI Analysis (multi-timeframe, dual signal)

The persona, method, and risk rules live in an **editable Markdown file**
(`app/services/ai/prompts/hedge_fund_analyst.md`) so prompt tuning requires no code
change. The strict JSON **output contract**, by contrast, is built in code
(`BaseAIProvider._build_system_prompt`) so the documented keys can never drift from
the `DualSignalDraft` schema they must satisfy.

**System prompt (summary):** a senior portfolio manager on a macro/FX & precious-
metals desk. Reads the tape **top-down** across timeframes (highest = context,
lowest = timing). Runs **always-on**: always produces two directional ideas (scalp +
swing), never sits flat, and expresses uncertainty as a low `confidence`. Never
invents levels that aren't in the input. Keeps/adjusts open signals.

**User prompt (per analysis, built in `_build_user_prompt`):**
- Instrument + primary (decision) timeframe.
- Per timeframe (presented highest → lowest): indicator snapshot (rounded) + the
  most recent ~30 candles.
- The pair's currently-open scalp/swing signals (KEEP/ADJUST context).
- *(planned — Iteration 8)* a compact "recent performance" block (hit-rate, avg R,
  confidence bias) so the model calibrates against its own track record.
- *(planned — Iteration 9)* upcoming high-impact USD events (CPI/FOMC/NFP).

**Output contract (strict JSON):**
```jsonc
{
  "scalp": {
    "direction": "buy" | "sell",          // never "neutral"
    "confidence": 0.0-1.0,
    "entry": number,
    "stop_loss": number,
    "take_profits": [number, ...],        // 1..3, ordered TP1..TP3
    "rationale": "short desk note"
  },
  "swing": { ... same shape ... }
}
```
The response is validated into a `DualSignalDraft`; each signal must be directional
(buy/sell) with an entry price, otherwise *that pair* fails for *that run* (per-pair
isolation). *(planned — Iteration 8)* the parsing is replaced with the provider's
native structured output (Anthropic tool-use / Groq JSON-mode), with today's regex
extraction as a fallback.

---

## 7. Provider Strategy (env switching)

The backend chooses its AI and market-data providers via environment variables — no
code change to swap models. Each external integration implements an abstract base
class and is constructed by a factory.

```env
# Development
AI_PROVIDER=groq
AI_MODEL=llama-3.3-70b-versatile

# Production
AI_PROVIDER=anthropic
AI_MODEL=claude-sonnet-4-6
```

`BaseAIProvider` (Template Method) owns prompt building, JSON extraction, validation,
and the "a directional signal needs an entry" rule — *once*. Each concrete provider
(Groq, Anthropic) implements only `_complete()` and translates its SDK errors into
`AIRequestError`. Adding a third provider is a ~20-line file.

---

## 8. API Endpoints (v1)

Every response follows a shared envelope (`{"success": true, "data": ...}` or
`{"success": false, "error": {...}}`), except `/health`, which returns the health
document directly so external monitors can ingest it unwrapped.

### Signals
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/signals` | Paginated list; filters `?pair=`, `?run_id=`, `?signal_type=` *(and `?outcome=` — Iteration 6)* |
| GET | `/api/v1/signals/{signal_id}` | Single signal with full rationale (404 if unknown) |

### Pairs
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/pairs` | All pairs; `?include_inactive=` |
| GET | `/api/v1/pairs/{symbol}` | Info about a specific pair (404 if unknown) |
| GET | `/api/v1/pairs/{symbol}/signals` | Latest signals for the pair; `?limit=` |

### Analysis & system
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Health status (DB, scheduler, market_data, ai_provider) |
| GET | `/api/v1/analysis/runs` | Paginated run ledger; `?status=` |
| GET | `/api/v1/analysis/runs/{run_id}` | Single run (404 if unknown) |
| GET | `/api/v1/analysis/runs/{run_id}/signals` | Signals per run |
| POST | `/api/v1/analysis/runs` | Manual trigger → `202` + background job |

### Planned endpoints
| Method | Endpoint | Iteration |
|---|---|---|
| GET | `/api/v1/performance` | 7 — track record, calibration, equity curve |
| GET | `/api/v1/calendar` | 9 — upcoming high-impact events |
| GET | `/api/v1/stream` (SSE) | 10 — real-time events to the frontend |
| POST | `/api/v1/risk/position-size` | 11 — position sizing (stateless) |

---

## 9. Frontend — Pages and Components

### Pages (actual routes)
| Page | Route | Content |
|---|---|---|
| Dashboard | `/` and `/dashboard` | Luxury fintech ops dashboard, live signal endpoints |
| Signals | `/signals` | Browse all signals, URL-synced filters + pagination |
| Signal detail | `/signals/[signalId]` | Full signal: level map, indicators panel, rationale |
| Pair detail | `/pairs/[symbol]` | Latest signals + levels for a pair |
| Analysis runs | `/analysis` | Run ledger (status filter, pagination) |
| Run detail | `/analysis/[runId]` | A run's signals + metadata |
| **Performance** | `/performance` | *(planned — Iteration 10)* win-rate, equity curve, calibration |

### Key components (actual)
- **SignalCard / SignalList / SignalBadge** — compact signal view (direction, Entry,
  SL, TP1-3, confidence, freshness badge, entry→SL/TP distance in %).
  *(planned — Iteration 9)* outcome badge (`✓ TP2 +2.1R` / `✗ SL −1R`).
- **SignalLevelMap / SignalOverlay** — %-positioned level map driven by signal levels
  + indicators (no OHLCV feed, so inherently responsive).
- **IndicatorsPanel** — RSI/MACD/EMA/BB/ATR from `indicators_snapshot`.
- **CommandPalette (Cmd/Ctrl+K)**, **NotificationBell**, **Toaster** — global search,
  notification feed, toasts. *(planned — Iteration 11)* fed by real-time SSE events.
- **AppShell / DashboardShell** — navigation shell, breadcrumbs, active route.

State: Zustand (`signalStore`, `uiStore`, `notificationStore`, `toastStore`) with
`localStorage` persistence for UI preferences. Data: React Query with
`refetchInterval` (auto-refresh) and "updated X ago" timestamps.

---

## 10. Configuration and Environment Variables

### Backend (`.env`) — actual
```env
# App
APP_ENV=development                 # development|staging|production|test
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
CORS_ALLOWED_ORIGINS=http://localhost:3000   # CSV; empty = CORS off

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tradesignal
# DATABASE_POOL_SIZE=10 / DATABASE_MAX_OVERFLOW=20 / DATABASE_POOL_RECYCLE_SECONDS=1800

# AI
AI_PROVIDER=groq                    # groq|anthropic
AI_MODEL=llama-3.3-70b-versatile
AI_API_KEY=...
# AI_TEMPERATURE=0.2 / AI_MAX_TOKENS=2048 / AI_TIMEOUT_SECONDS=30

# Market data
MARKET_DATA_PROVIDER=twelve_data
TWELVE_DATA_API_KEY=...
# MARKET_DATA_TIMEOUT_SECONDS=15 / MARKET_DATA_MAX_RETRIES=3

# Analysis (multi-timeframe)
ANALYSIS_INTERVAL_MINUTES=15
ANALYSIS_CANDLE_COUNT=200
ANALYSIS_TIMEFRAME=1h               # primary decision timeframe
ANALYSIS_TIMEFRAMES=5m,15m,1h,4h,1d # CSV; all fed to the AI top-down
ACTIVE_PAIRS=XAUUSD                 # Gold only for now (tier limit)

# Signal lifetime (freshness + retention)
SIGNAL_SCALP_TTL_MINUTES=240        # 4h
SIGNAL_SWING_TTL_MINUTES=4320       # 3d

# Scheduler
SCHEDULER_ENABLED=true              # run the job on exactly one instance
# SCHEDULER_TIMEZONE=UTC / SCHEDULER_MISFIRE_GRACE_SECONDS=60
```
> **Planned variables:** `OUTCOME_INTERVAL_MINUTES` (Iteration 6),
> `ECONOMIC_CALENDAR_ENABLED` (Iteration 9), `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`
> (Iteration 10).

### Frontend (`.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=TradeSignal AI
NEXT_PUBLIC_SITE_URL=http://localhost:3000   # for SEO/robots/sitemap
```

---

## 11. Local Run

### Database (PostgreSQL on Windows)
```powershell
cd backend
psql -U postgres -d postgres -f .\db\create_local_database.sql
alembic upgrade head
psql -U tradesignal_app -d tradesignal -f .\db\seed_pairs.sql
```

### Backend
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# API docs (dev): /api/docs, /api/redoc, /api/openapi.json
```

### Frontend
```bash
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

> **Docker** (`docker-compose` for backend + postgres) is *deferred* until the
> deploy target is settled — see backend README, Iteration 5.

---

## 12. Scalability Principles

- **Provider Pattern** — AI, market data (and planned: calendar, notifier) behind
  abstract base classes. New provider = new file, zero change in controllers.
- **Repository Pattern** — all database logic lives in the repository layer;
  controllers own transaction boundaries, repos only stage work.
- **API versioning** — everything under `/api/v1/`; breaking changes → `/api/v2/`.
- **Configuration via environment variables** — fail-fast `Settings`; a single
  mistyped line stops the process from starting.
- **JSONB for the indicator snapshot** — the full indicator set is stored per signal
  so models can be back-tested against historical inputs without re-fetching data.
- **Modular frontend** — `services/`, `hooks/`, `types/` are isolated and reusable
  for a future React Native app.

---

## 13. Quality and Verification

- **Backend:** `pytest` (274 tests green at last verification), `ruff check`/`ruff
  format --check` clean, `pyright` (basic). Tests cover config, schemas,
  repositories (SQL with literal binds), market data (httpx MockTransport),
  indicators, AI providers (prompt/parse/SDK error mapping), scheduler lifecycle,
  controllers (unit + in-memory), and routes (integration via
  `app.dependency_overrides`).
- **Frontend:** Vitest + React Testing Library (unit/component) and Playwright
  (route smoke); `npm run check` runs typecheck + lint + vitest + build.
- **Deliberately deferred:** live-Postgres round-trips and real
  Twelve Data/Groq/Anthropic network calls are exercised via injected fakes/mocks.

---

## 14. Roadmap — Iterations 6-11 (backend) / 9-13 (frontend)

A product review on 2026-06-03 identified the core gap: the platform *generates*
signals but never *measures* them. The following iterations make it measurable,
self-improving, and real-time. The full task list lives in each README.

| # | Theme | Backend | Frontend | Value |
|---|---|---|---|---|
| 1 | **Outcome tracking** (track record) | It. 6 | It. 9 | Win-rate & R become possible — the product's credibility |
| 2 | **Performance & calibration** | It. 7 | It. 10 | "When the AI says 80% — is it right?" Equity curve. |
| 3 | **Smarter/cheaper AI** | It. 8 | It. 13 | Track-record feedback in the prompt, structured output, cost tracking |
| 4 | **Macro/news awareness** | It. 9 | It. 13 | Gold is driven by USD/CPI/Fed — the AI stops trading blind |
| 5 | **Real-time + notifications** | It. 10 | It. 11 | SSE push + Telegram — signals delivered instantly |
| 6 | **Risk & position sizing** | It. 11 | It. 12 | "How big a position?" — turns an idea into a concrete trade |

**Sequencing:** Iteration 6 (outcome tracking) is the keystone and is built first —
Iterations 7 and 8 rest directly on its data. On a Gold-only setup it costs almost
no extra API calls (one candle fetch per cycle).

### Later phases (not in this roadmap)
- User authentication (JWT + refresh tokens) — Phase 2
- Subscription management (Stripe) — Phase 2
- Backtesting module (validate signal quality historically on real data)
- Mobile app (React Native + Expo)
- Admin dashboard for pairs/signals/runs
- Docker/containerization (deferred until the deploy target is settled)

---

*Project description version 2.0 — TradeSignal AI (updated 2026-06-03)*
