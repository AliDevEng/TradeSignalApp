# TradeSignal AI — Projektbeskrivning

> En AI-driven handelsanalysplattform som automatiskt analyserar Forex- och guldmarknaden och genererar professionella trade-signaler med Entry, SL, TP1, TP2 och TP3.

---

## 1. Projektöversikt

TradeSignal AI är en fullstack webbapplikation som automatiskt hämtar marknadsdata för valutapar (XAUUSD, GBPUSD, EURUSD m.fl.), beräknar tekniska indikatorer och skickar dessa till en AI-modell för djupanalys. Systemet genererar strukturerade trade-signaler (BUY/SELL) med tydliga Entry-priser, Stop Loss och tre Take Profit-nivåer.

Plattformen är byggd för skalbarhet, separation of concerns och en flerlager-arkitektur som gör det enkelt att lägga till nya funktioner, valutapar, AI-modeller och betalningslösningar i framtiden.

### Affärsmål
- Fas 1: Fungerade produkt med automatisk signalgenerering (detta projekt)
- Fas 2: Användarregistrering och betalda prenumerationer
- Fas 3: Mobilapp (React Native / Expo)

---

## 2. Teknisk Stack

### Frontend
| Komponent | Val | Motivering |
|---|---|---|
| Framework | Next.js 14 (App Router) | SSR för SEO, filbaserad routing, Vercel-deploy |
| Språk | TypeScript | Typssäkerhet, kodkvalitet, auto-completion |
| Styling | Tailwind CSS | Utility-first, snabb utveckling |
| Charts | Lightweight Charts (TradingView) | Professionella finansiella charts |
| State | Zustand | Enkelt, skalbart state management |
| HTTP-klient | Axios + React Query | Caching, loading states, error handling |
| Formulär | React Hook Form + Zod | Validering med TypeScript-integration |

### Backend
| Komponent | Val | Motivering |
|---|---|---|
| Framework | Python + FastAPI | Async, snabb, OpenAPI-docs automatiskt |
| Språk | Python 3.12+ | AI/ML-ekosystemet lever i Python |
| Schemaläggning | APScheduler | Kör analysjobb var 15:e minut, ingen Redis krävs |
| Indikatorer | pandas-ta | Beräknar RSI, MACD, EMA, BB, ATR automatiskt |
| ORM | SQLAlchemy 2.0 | Async ORM, databasagnostisk |
| Migrationer | Alembic | Versionshantering av databasschema |
| Validering | Pydantic v2 | Request/response-validering, TypeScript-typer kan genereras |

### AI-lager
| Komponent | Val | Motivering |
|---|---|---|
| Dev-modell | Groq API (Llama 3.3 70B) | Gratis under utveckling, snabb |
| Prod-modell | Claude Sonnet 4.6 (Anthropic) | Stark reasoning, strukturerade svar |
| Strategi | Miljövariabel-styrning | Byta modell utan kodändring |

### Datakälla
| Komponent | Val | Motivering |
|---|---|---|
| Market data | Twelve Data API | Stödjer XAUUSD, GBPUSD, EURUSD, gratis tier |
| Format | OHLCV (1H candles) | Tillräcklig granularitet för swing/day trading |

### Databas
| Komponent | Val | Motivering |
|---|---|---|
| Databas | PostgreSQL 16 | Robust, skalbar, JSONB-stöd |
| Driver | asyncpg | Async PostgreSQL-driver |

### DevOps
| Komponent | Val |
|---|---|
| Containerisering | Docker + Docker Compose |
| Frontend deploy | Vercel |
| Backend deploy | Railway / VPS |
| Miljöhantering | .env filer per miljö |
| Versionshantering | GitHub (monorepo) |

---

## 3. Projektstruktur (Monorepo)

```
tradesignal-ai/
├── README.md
├── .gitignore
├── docker-compose.yml              # Lokal dev: backend + postgres
│
├── frontend/                       # Next.js 14 + TypeScript
│   ├── public/
│   ├── src/
│   │   ├── app/                    # App Router (Next.js 14)
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Landningssida
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx        # Signal dashboard
│   │   │   └── signals/
│   │   │       └── [pair]/
│   │   │           └── page.tsx    # Detaljvy per par
│   │   ├── components/
│   │   │   ├── ui/                 # Generiska UI-komponenter
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Badge.tsx
│   │   │   │   └── LoadingSpinner.tsx
│   │   │   ├── charts/
│   │   │   │   ├── CandlestickChart.tsx
│   │   │   │   └── SignalOverlay.tsx
│   │   │   ├── signals/
│   │   │   │   ├── SignalCard.tsx
│   │   │   │   ├── SignalList.tsx
│   │   │   │   └── SignalBadge.tsx
│   │   │   └── layout/
│   │   │       ├── Navbar.tsx
│   │   │       └── Sidebar.tsx
│   │   ├── services/               # API-anrop till backend
│   │   │   ├── api.ts              # Axios-instans + interceptors
│   │   │   ├── signalService.ts
│   │   │   └── pairService.ts
│   │   ├── store/                  # Zustand stores
│   │   │   ├── signalStore.ts
│   │   │   └── uiStore.ts
│   │   ├── types/                  # TypeScript interfaces
│   │   │   ├── signal.ts
│   │   │   ├── pair.ts
│   │   │   └── api.ts
│   │   ├── hooks/                  # Custom React hooks
│   │   │   ├── useSignals.ts
│   │   │   └── usePairs.ts
│   │   └── lib/                    # Utilities
│   │       ├── formatters.ts
│   │       └── constants.ts
│   ├── .env.local
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── package.json
│
├── backend/                        # Python + FastAPI
│   ├── app/
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   │
│   │   ├── models/                 # SQLAlchemy datamodeller (M i MVC)
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base class för alla modeller
│   │   │   ├── signal.py           # Signal-modell
│   │   │   ├── pair.py             # TradingPair-modell
│   │   │   └── analysis_run.py     # Logg över varje analyskörning
│   │   │
│   │   ├── schemas/                # Pydantic schemas (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── signal.py
│   │   │   ├── pair.py
│   │   │   └── analysis.py
│   │   │
│   │   ├── controllers/            # Affärslogik (C i MVC)
│   │   │   ├── __init__.py
│   │   │   ├── signal_controller.py
│   │   │   └── analysis_controller.py
│   │   │
│   │   ├── views/                  # FastAPI routers = API-endpoints (V i MVC)
│   │   │   ├── __init__.py
│   │   │   ├── signals.py          # GET /signals, GET /signals/{id}
│   │   │   ├── pairs.py            # GET /pairs
│   │   │   └── health.py           # GET /health
│   │   │
│   │   ├── services/               # Externa integrationer
│   │   │   ├── __init__.py
│   │   │   ├── market_data/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py         # Abstract base class
│   │   │   │   └── twelve_data.py  # Twelve Data implementation
│   │   │   ├── ai/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py         # Abstract AI-provider base
│   │   │   │   ├── groq_provider.py
│   │   │   │   └── anthropic_provider.py
│   │   │   └── indicators/
│   │   │       ├── __init__.py
│   │   │       └── calculator.py   # pandas-ta beräkningar
│   │   │
│   │   ├── tasks/                  # APScheduler jobb
│   │   │   ├── __init__.py
│   │   │   └── analysis_job.py     # Schemalagd analyskörning
│   │   │
│   │   └── database/
│   │       ├── __init__.py
│   │       ├── connection.py       # Async SQLAlchemy engine
│   │       └── repository/         # Databasoperationer
│   │           ├── __init__.py
│   │           ├── base.py
│   │           ├── signal_repo.py
│   │           └── pair_repo.py
│   │
│   ├── migrations/                 # Alembic migrationer
│   │   ├── env.py
│   │   └── versions/
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── .env
│   ├── .env.example
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
│
└── docs/
    ├── PROJECT_DESCRIPTION.md      # Detta dokument
    └── api/                        # API-dokumentation
```

---

## 4. Databasschema

### Tabell: trading_pairs
```sql
CREATE TABLE trading_pairs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol      VARCHAR(20) UNIQUE NOT NULL,  -- "XAUUSD", "GBPUSD"
    name        VARCHAR(100) NOT NULL,         -- "Gold / US Dollar"
    is_active   BOOLEAN DEFAULT TRUE,
    timeframe   VARCHAR(10) DEFAULT '1h',      -- Analysgranularitet
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabell: signals
```sql
CREATE TABLE signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pair_id         UUID REFERENCES trading_pairs(id),
    direction       VARCHAR(4) NOT NULL,        -- "BUY" | "SELL"
    entry_price     DECIMAL(18, 5) NOT NULL,
    stop_loss       DECIMAL(18, 5) NOT NULL,
    take_profit_1   DECIMAL(18, 5) NOT NULL,
    take_profit_2   DECIMAL(18, 5),
    take_profit_3   DECIMAL(18, 5),
    confidence      INTEGER,                    -- 1-100, AI:ns självskattning
    reasoning       TEXT,                       -- AI:ns motivering
    status          VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE | HIT_TP1 | HIT_SL | EXPIRED
    raw_ai_response JSONB,                      -- Hela AI-svaret för debugging
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,                -- När signalen anses inaktuell
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabell: analysis_runs
```sql
CREATE TABLE analysis_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pair_id         UUID REFERENCES trading_pairs(id),
    status          VARCHAR(20) NOT NULL,       -- SUCCESS | FAILED | SKIPPED
    ai_provider     VARCHAR(50),                -- "groq" | "anthropic"
    ai_model        VARCHAR(100),               -- Modellnamn
    indicators_used JSONB,                      -- Snapshot av indikatorer
    error_message   TEXT,
    duration_ms     INTEGER,                    -- Analystid i millisekunder
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. MVC-arkitektur och Dataflöde

### Analysflöde (automatiskt, var 15:e minut)

```
APScheduler (tasks/analysis_job.py)
    │
    ▼
AnalysisController.run_analysis(pair)
    │
    ├─► MarketDataService.fetch_ohlcv(symbol, timeframe)
    │       └─► Twelve Data API → returnerar 200 OHLCV-stearinljus
    │
    ├─► IndicatorCalculator.calculate(df)
    │       └─► pandas-ta → RSI, MACD, EMA20/50/200, BB, ATR, Volume
    │
    ├─► AIProvider.analyze(indicators, pair)
    │       └─► Groq/Anthropic API → strukturerat JSON-svar
    │
    ├─► SignalController.create_signal(ai_response, pair)
    │       └─► Validerar, sparar till PostgreSQL via SignalRepository
    │
    └─► AnalysisRunRepository.log(run_details)
```

### API-anropsflöde (frontend → backend)

```
Next.js Frontend
    │
    ├─► GET /api/v1/signals?pair=XAUUSD&limit=10
    │       └─► signals router → SignalController → SignalRepository → PostgreSQL
    │
    ├─► GET /api/v1/signals/{id}
    │       └─► Enskild signal med full motivering
    │
    └─► GET /api/v1/pairs
            └─► Alla aktiva valutapar
```

---

## 6. AI-analysprompt (Systemprompt)

Följande systemprompt skickas till AI-modellen vid varje analyskörning:

```
Du är en erfaren institutionell Forex- och råvaruanalytiker med 15 års erfarenhet 
från ett globalt Hedge Fund. Du specialiserar dig på teknisk analys av XAUUSD, 
GBPUSD och EURUSD på H1-timeframe.

Din uppgift är att analysera de tekniska indikatorerna nedan och ge en 
välmotiverad trade-rekommendation.

Analysregler:
- Identifiera den dominerande trenden (bullish/bearish/sideways)
- Bedöm momentum och eventuella divergenser
- Basera SL på marknadsstruktur (senaste swing high/low), inte på pip-avstånd
- TP1 = konservativt mål (risk/reward minst 1:1.5)
- TP2 = moderat mål (nästa strukturnivå)
- TP3 = ambitiöst mål (om trenden fortsätter)
- Ge ALDRIG en signal om conviction < 60%
- Om markanden är oklar, returnera direction: "NEUTRAL"

Returnera EXAKT detta JSON-format och inget annat:
{
  "direction": "BUY" | "SELL" | "NEUTRAL",
  "entry_price": float,
  "stop_loss": float,
  "take_profit_1": float,
  "take_profit_2": float | null,
  "take_profit_3": float | null,
  "confidence": int (1-100),
  "reasoning": "Kort motivering på engelska (max 3 meningar)",
  "trend": "BULLISH" | "BEARISH" | "SIDEWAYS",
  "key_levels": [float]
}
```

### Användarprompt-mall (skickas per analys)

```
Analysera {SYMBOL} på {TIMEFRAME} timeframe.
Aktuellt pris: {CURRENT_PRICE}
Senaste {N} stearinljus OHLCV: {OHLCV_JSON}

Beräknade tekniska indikatorer:
- RSI(14): {RSI}
- MACD Line: {MACD_LINE}, Signal: {MACD_SIGNAL}, Histogram: {MACD_HIST}
- EMA20: {EMA20}, EMA50: {EMA50}, EMA200: {EMA200}
- Bollinger Bands: Upper {BB_UPPER}, Middle {BB_MIDDLE}, Lower {BB_LOWER}
- ATR(14): {ATR}
- Volym (relativt 20-perioder snitt): {VOLUME_RATIO}x

Ge din analys och trade-rekommendation.
```

---

## 7. AI-providerstrategi (Miljöväxling)

Backend väljer AI-provider baserat på miljövariabler. Ingen kodändring krävs för att byta modell.

### .env (development)
```env
AI_PROVIDER=groq
AI_MODEL=llama-3.3-70b-versatile
AI_API_KEY=gsk_xxxxxxxxxxxx
```

### .env (production)
```env
AI_PROVIDER=anthropic
AI_MODEL=claude-sonnet-4-6
AI_API_KEY=sk-ant-xxxxxxxxxxxx
```

### Abstract AI Provider (services/ai/base.py)
```python
from abc import ABC, abstractmethod
from app.schemas.analysis import AIAnalysisResult

class BaseAIProvider(ABC):
    @abstractmethod
    async def analyze(self, prompt: str, system_prompt: str) -> AIAnalysisResult:
        pass
```

Varje provider (Groq, Anthropic) implementerar `BaseAIProvider`. `AnalysisController` väljer provider baserat på `AI_PROVIDER`-variabeln vid startup.

---

## 8. API-endpoints (v1)

### Signals
| Method | Endpoint | Beskrivning |
|---|---|---|
| GET | `/api/v1/signals` | Hämta senaste signaler, filtrera på pair |
| GET | `/api/v1/signals/{id}` | Hämta enskild signal med full motivering |
| GET | `/api/v1/signals/latest` | Senaste aktiva signalen per par |

### Pairs
| Method | Endpoint | Beskrivning |
|---|---|---|
| GET | `/api/v1/pairs` | Alla aktiva valutapar |
| GET | `/api/v1/pairs/{symbol}` | Info om specifikt par |

### System
| Method | Endpoint | Beskrivning |
|---|---|---|
| GET | `/api/v1/health` | Hälsostatus för API och databas |
| GET | `/api/v1/analysis/runs` | Logg över senaste analyskörningar |
| POST | `/api/v1/analysis/trigger` | Manuell trigger av analys (dev/admin) |

Alla endpoints är prefixade med `/api/v1/` för framtida versionshantering.

---

## 9. Frontend Sidor och Komponenter

### Sidor
| Sida | Route | Innehåll |
|---|---|---|
| Dashboard | `/dashboard` | Översikt av alla aktiva signaler |
| Signal Detail | `/signals/[id]` | Fullständig signal med chart och AI-motivering |
| Pair View | `/dashboard/[pair]` | Chart + signalhistorik för ett specifikt par |
| Landing | `/` | Marknadsföringssida (SEO-optimerad via SSR) |

### Nyckelkomponenter

**SignalCard** — Visar en signal kompakt:
- Par-symbol och riktning (BUY/SELL badge i grönt/rött)
- Entry, SL, TP1/TP2/TP3 priser
- Confidence-procent
- Tidsstämpel och status

**CandlestickChart** — TradingView Lightweight Charts:
- OHLCV-stearinljus på H1
- Overlay med signallinjer (Entry, SL, TP1, TP2, TP3)
- Automatisk skalning

**SignalList** — Lista av SignalCards med filter på par och status.

---

## 10. Konfiguration och Miljövariabler

### Backend (.env)
```env
# App
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true

# Databas
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/tradesignal

# AI Provider
AI_PROVIDER=groq                        # groq | anthropic
AI_MODEL=llama-3.3-70b-versatile
AI_API_KEY=your_api_key_here

# Market Data
MARKET_DATA_PROVIDER=twelve_data
TWELVE_DATA_API_KEY=your_key_here

# Analys
ANALYSIS_INTERVAL_MINUTES=15           # Hur ofta analysen körs
ANALYSIS_CANDLE_COUNT=200              # Antal stearinljus som hämtas
ANALYSIS_TIMEFRAME=1h                  # H1 default

# Aktiva par (kommaseparerat)
ACTIVE_PAIRS=XAUUSD,GBPUSD,EURUSD
```

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_NAME=TradeSignal AI
```

---

## 11. Docker Compose (lokal utveckling)

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: tradesignal
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://user:password@postgres:5432/tradesignal
    depends_on:
      - postgres
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

volumes:
  postgres_data:
```

---

## 12. Installationsordning för Claude Code

Följande ordning ska följas vid bygge:

1. **Projektstruktur** — Skapa alla mappar och tomma filer enligt trädet i sektion 3
2. **Databas** — Sätt upp PostgreSQL-anslutning, SQLAlchemy models, Alembic-migrationer
3. **Repository-lager** — Implementera CRUD i `database/repository/`
4. **Services** — Implementera `market_data/twelve_data.py` och `indicators/calculator.py`
5. **AI-lager** — Implementera `ai/base.py`, `ai/groq_provider.py`, `ai/anthropic_provider.py`
6. **Controllers** — Implementera `analysis_controller.py` och `signal_controller.py`
7. **API-routes** — Implementera FastAPI routers i `views/`
8. **Schemaläggning** — Sätt upp APScheduler i `tasks/analysis_job.py`
9. **main.py** — Koppla ihop allt, starta scheduler vid app-start
10. **Frontend** — Next.js setup, TypeScript-typer, API-service, komponenter, sidor
11. **Docker** — Docker Compose för lokal dev
12. **Tester** — Unit tests för controllers och services

---

## 13. Skalbarhetsprinciper

- **Provider Pattern** — Alla externa integrationer (AI, market data) implementerar en abstract base class. Ny provider = ny fil, noll kodändring i controllers.
- **Repository Pattern** — All databaslogik isolerad i repository-lagret. Byta databas påverkar bara repository-filerna.
- **Versionshantering av API** — Alla endpoints under `/api/v1/`. Framtida breaking changes → `/api/v2/`.
- **Konfiguration via miljövariabler** — Inget hårdkodat. Byta AI-modell, lägga till par, ändra intervall — allt via `.env`.
- **JSONB för AI-svar** — Hela råsvaret lagras i `raw_ai_response`. Framtida analys eller omstrukturering av data möjlig utan förlorad information.
- **Modular frontend** — Komponenter är isolerade och återanvändbara. React Native-övergången kan återanvända logik i `services/`, `hooks/` och `types/`.

---

## 14. Framtida Features (ej i Fas 1)

Dessa ska inte byggas nu men arkitekturen ska inte förhindra dem:

- Användarautentisering (JWT + refresh tokens)
- Prenumerationshantering (Stripe)
- Push-notifikationer vid ny signal
- Backtesting-modul (validera signalkvalitet historiskt)
- Mobilapp (React Native + Expo, delar types/ och services/)
- Makroekonomisk kalender-integration (NFP, CPI, räntebeslut)
- Admin-dashboard för att hantera par, signaler och analyskörningar
- WebSocket för realtidsuppdatering av signaler i frontend

---

*Projektbeskrivning version 1.0 — TradeSignal AI*
