# Local PostgreSQL Database Setup

These files create a local PostgreSQL database for the FastAPI backend.
The application schema is owned by Alembic, so the setup flow is:

1. Create the local database and login role.
2. Point `backend/.env` at that database.
3. Run `alembic upgrade head`.
4. Seed the default trading pairs.

## 1. Open PowerShell

From the repository root:

```powershell
cd .\backend
```

If `psql` is not found, add PostgreSQL 18 to your current terminal path:

```powershell
$env:Path += ";C:\Program Files\PostgreSQL\18\bin"
```

## 2. Create the Database and User

Run this as your PostgreSQL admin user. On a normal Windows install, that user
is `postgres`.

```powershell
psql -U postgres -d postgres -f .\db\create_local_database.sql
```

Default local credentials created by the script:

```text
database: tradesignal
user:     tradesignal_app
password: tradesignal_dev_password
```

To choose your own password:

```powershell
psql -U postgres -d postgres `
  -v app_user=tradesignal_app `
  -v app_password="your_strong_password" `
  -v app_db=tradesignal `
  -f .\db\create_local_database.sql
```

## 3. Create `backend/.env`

Copy the example file:

```powershell
Copy-Item .\.env.example .\.env
```

Set the database URL to match the local database:

```env
DATABASE_URL=postgresql+asyncpg://tradesignal_app:tradesignal_dev_password@localhost:5432/tradesignal
```

Also fill in `AI_API_KEY` and `TWELVE_DATA_API_KEY` when you want the scheduled
analysis job to run for real.

## 4. Install Backend Dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

## 5. Apply the Schema

```powershell
alembic upgrade head
```

This creates the current production schema:

- `pairs`
- `analysis_runs`
- `signals`
- Postgres enums: `analysis_run_status`, `analysis_run_trigger`, `signal_direction`
- all indexes, checks, unique constraints, and foreign keys

## 6. Seed Trading Pairs

```powershell
psql -U tradesignal_app -d tradesignal -f .\db\seed_pairs.sql
```

The backend currently monitors the same default symbols configured in
`ACTIVE_PAIRS`: `XAUUSD`, `GBPUSD`, and `EURUSD`.

## 7. Verify

```powershell
psql -U tradesignal_app -d tradesignal -f .\db\check_database.sql
alembic current
```

Then start the API:

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

- Swagger UI: http://localhost:8000/api/docs
- Health: http://localhost:8000/api/v1/health

## Notes

- PostgreSQL 18 is fine for local development. The project uses standard
  PostgreSQL features: native enums, `JSONB`, `NUMERIC`, indexes, checks, and
  foreign keys.
- Do not create tables manually. Use Alembic migrations so the database stays
  in lockstep with `app/models`.
- The `signals` table stores the full take-profit ladder: `take_profit` (TP1),
  `take_profit_2` (TP2), and `take_profit_3` (TP3), all nullable. The schema
  columns exist as of migration `0002`; the backend persistence layer currently
  still writes only TP1, so TP2/TP3 stay NULL until that code is updated.
