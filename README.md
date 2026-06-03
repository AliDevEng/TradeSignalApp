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
1. 📦 Set up backend dependencies and env
2. 🗄️ Start PostgreSQL
3. 🔌 Run backend API
4. 🌐 Set up frontend dependencies and env
5. 🧪 Build features iteration by iteration

## ▶️ Current Run Flow
### ⚙️ Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### 🌐 Frontend
```bash
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

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
