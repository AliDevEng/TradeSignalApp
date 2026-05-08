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
- 🚧 Phase 1: Automated signal generation
- 👥 Phase 2: Auth + paid subscriptions
- 📱 Phase 3: Mobile app (React Native / Expo)

## 📍 Current Status
- ✅ Frontend Iteration 1 is complete: Next.js foundation, strict TypeScript, Tailwind, typed API client, and React Query provider
- ✅ Frontend Iteration 2 is complete: shared UI primitives, dashboard shell, signal list, signal cards, and Zustand filters
- ✅ Frontend Iteration 3 is complete: candlestick charts, signal overlays, pair detail pages, and signal reasoning views
- 🚧 Frontend Iteration 4 remains: form validation, richer loading/empty/error states, responsive QA, and final cleanup
- ✅ Backend Iteration 1 is complete: FastAPI app factory, settings, health endpoint, and response envelopes
- ✅ Backend Iteration 2 is complete: database layer, models, Alembic migration, and repository layer
- 🚧 Backend Iteration 3 is next: market data service, indicators, AI providers, and scheduler wiring

## 🛠️ Core Stack
- 🎨 Frontend: Next.js + React + TypeScript + Tailwind
- ⚙️ Backend: FastAPI + SQLAlchemy + PostgreSQL + APScheduler
- 🧠 AI: Groq (dev) / Anthropic (prod)
- 📊 Data: Twelve Data API

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
- ✅ Frontend passes `npm run check`
- ✅ Frontend routes verified locally: `/`, `/pairs/XAUUSD`, `/signals/sig-xauusd-1`
- ✅ Backend health endpoint is wired to `GET /api/v1/health`

## 📚 Detailed Setup
- 👉 Frontend plan: `frontend/README.md`
- 👉 Backend plan: `backend/README.md`

## 🎉 Mission
Ship a robust AI trading analysis platform with clean workflow, clear milestones, and production-ready foundations. Let's build it. 🔥
