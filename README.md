# 🚀 TradeSignal AI 🌍📈🤖

## ✨ Project Vibe
Welcome to **TradeSignal AI** - a fullstack platform that analyzes Forex + Gold markets and generates structured trade signals with:
- 🎯 Entry
- 🛡️ Stop Loss
- 🥇 TP1
- 🥈 TP2
- 🥉 TP3

Built for speed, scale, clean architecture, and future growth. 💪

## 🧱 Monorepo Structure
```text
TradeSignalApp/
├── PROJECT_DESCRIPTION.md
├── README.md
├── frontend/
│   ├── README.md
│   ├── package.json
│   └── src/
└── backend/
    ├── README.md
    ├── app/
    ├── migrations/
    └── tests/
```

## 🗺️ Product Roadmap
- ✅ Phase 1: Automated signal generation
- 🚧 Phase 1.5: Measurable, self-improving, real-time platform — outcome tracking, performance & calibration, macro awareness, real-time + notifications, risk sizing (see **Roadmap** below)
- 👥 Phase 2: Auth + paid subscriptions
- 📱 Phase 3: Mobile app (React Native / Expo)

## 🥇 Current Focus
Trading focus is **XAUUSD (Gold) only** for now — the Twelve Data free tier's
per-minute limit is consumed by the multi-timeframe fetch for a single pair. The
architecture stays fully multi-pair; only `ACTIVE_PAIRS` is narrowed.

## 📍 Current Status
- ✅ **Frontend Iterations 1-8 complete:** foundation → core UI → trading views →
  quality/delivery → navigation & IA → real data depth → live & interactive →
  quality & production (tests, a11y, SEO, monitoring, perf). **130 points.**
- ✅ **Backend Iterations 1-4 complete:** core API skeleton → data layer (async ORM,
  Alembic, repositories) → services + AI + scheduler → business logic + API
  endpoints. **Iteration 5** (quality: unit/integration tests, lint/static checks)
  done; Docker polish deferred until the deploy target is settled.
- 📊 Always-on **dual-signal** engine live: every run emits a **scalp** + a **swing**
  per pair from a **top-down multi-timeframe** read (5m → 1d), with a keep/adjust
  feedback loop on open signals.
- 🚧 **Next up — Phase 1.5 roadmap:** backend Iterations 6-11 / frontend 9-13. The
  keystone is **Iteration 6 (Signal Outcome Tracking)** — the platform generates
  signals but doesn't yet measure them.

## 🛠️ Core Stack
- 🎨 Frontend: Next.js 16 + React 19 + TypeScript + Tailwind 4 (Zustand, React Query, lightweight-charts)
- ⚙️ Backend: FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL 16 + APScheduler
- 🧠 AI: Groq (dev) / Anthropic (prod) — Provider Pattern, env-switched
- 📊 Data: Twelve Data API (multi-timeframe OHLCV)

## 🧭 Roadmap (Phase 1.5)
The signal generator becomes a measurable, self-improving, real-time platform. Full
task lists live in `backend/README.md` (Iterations 6-11) and `frontend/README.md`
(Iterations 9-13).

| # | Theme | Backend | Frontend |
|---|---|---|---|
| 1 | 🎯 Outcome tracking (track record) | It. 6 | It. 9 |
| 2 | 📊 Performance & calibration | It. 7 | It. 10 |
| 3 | 🧠 Smarter/cheaper AI (feedback loop, structured output, cost) | It. 8 | It. 13 |
| 4 | 📰 Macro / economic-calendar awareness | It. 9 | It. 13 |
| 5 | ⚡ Real-time (SSE) + notifications (Telegram) | It. 10 | It. 11 |
| 6 | 🛡️ Risk & position sizing | It. 11 | It. 12 |

## 🏁 Quick Start Order
1. 🗄️ Start PostgreSQL and make sure `backend/.env` points at it
2. 📦 Install backend dependencies and apply migrations
3. 🔌 Run the backend API on <http://localhost:8000>
4. 🌐 Install frontend dependencies
5. ▶️ Run the frontend on <http://localhost:3000>

## ▶️ Current Run Flow
Open two terminals from the repo root: one for the backend and one for the
frontend.

### ⚙️ Backend
Create `backend/.env` from `backend/.env.example`, then fill in at least
`DATABASE_URL`. Add `AI_API_KEY` and `TWELVE_DATA_API_KEY` when you want live
analysis instead of local/test-only flows.

#### Bash (Git Bash on Windows)
```bash
cd backend
[ -f .env ] || cp .env.example .env
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### PowerShell
```powershell
Set-Location backend
if (-not (Test-Path .\.env)) { Copy-Item .\.env.example .\.env }
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend checks:
- 🩺 Health: <http://localhost:8000/api/v1/health>
- 📚 Swagger UI: <http://localhost:8000/api/docs>

### 🌐 Frontend
The frontend reads the API URL from `frontend/.env.local`. For local development,
use `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`.

#### Bash
```bash
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

#### PowerShell
```powershell
Set-Location frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Frontend app:
- 🖥️ <http://localhost:3000>

## 🧪 Current Verification
- ✅ Frontend passes `npm run check` (typecheck + lint + Vitest + build); Playwright route-smoke in `e2e/`
- ✅ Frontend routes verified locally: `/`, `/dashboard`, `/signals`, `/analysis`, `/analysis/[runId]`, `/pairs/XAUUSD`, `/signals/[signalId]`
- ✅ Backend suite green: `pytest` → 274 passed, `ruff check`/`ruff format --check` clean (verified 2026-06-02)
- ✅ Backend health endpoint wired to `GET /api/v1/health` (reports DB, scheduler, market_data, ai_provider)
- ✅ `alembic upgrade head --sql` renders the full schema (pairs, analysis_runs, signals + native enums)
- ✅ Analysis pipeline live: scheduled `AnalysisJob` runs the real `AnalysisController` (no placeholder), emitting scalp + swing signals per pair
- ℹ️ Live-Postgres round-trips and real Twelve Data/Groq/Anthropic network calls are deferred; exercised via injected fakes, `httpx.MockTransport`, and `app.dependency_overrides`

## 📚 Detailed Setup
- 👉 Frontend plan: `frontend/README.md`
- 👉 Backend plan: `backend/README.md`

## 🎉 Mission
Ship a robust AI trading analysis platform with clean workflow, clear milestones, and production-ready foundations. Let's build it. 🔥
