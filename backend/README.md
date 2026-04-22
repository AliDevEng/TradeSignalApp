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
pip install fastapi==0.136.0 uvicorn[standard]==0.45.0 pydantic==2.13.3 pydantic-settings==2.14.0 sqlalchemy==2.0.49 alembic==1.18.4 apscheduler==3.11.2 asyncpg==0.31.0 httpx==0.28.1 python-dotenv==1.2.2 groq==1.2.0 anthropic==0.96.0 pandas==3.0.2 numpy==2.4.4 pandas-ta-classic==0.4.47
pip install pytest==9.0.3 pytest-asyncio==1.3.0 ruff==0.15.11
```

## 🧩 Iterations and Points

### Iteration 1 - Core API Skeleton (14 points)
- [ ] (3) Scaffold `app/main.py`, `config.py`, router registration
- [ ] (3) Add health endpoint
- [ ] (4) Add settings and env loading
- [ ] (4) Add base schemas and common response models

### Iteration 2 - Data Layer (20 points)
- [ ] (5) Setup SQLAlchemy async engine/session
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

## 🧪 Run
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔐 Env
Create `.env`:
```env
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tradesignal

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
