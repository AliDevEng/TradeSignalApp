-- Local PostgreSQL bootstrap for TradeSignal AI.
--
-- Run this with psql while connected as a PostgreSQL admin user, usually:
--   psql -U postgres -d postgres -f db/create_local_database.sql
--
-- Optional psql variables:
--   -v app_user=tradesignal_app
--   -v app_password=your_password
--   -v app_db=tradesignal

\if :{?app_user}
\else
\set app_user tradesignal_app
\endif

\if :{?app_password}
\else
\set app_password tradesignal_dev_password
\endif

\if :{?app_db}
\else
\set app_db tradesignal
\endif

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :'app_user'
)
\gexec

SELECT format('CREATE DATABASE %I OWNER %I ENCODING %L TEMPLATE template0', :'app_db', :'app_user', 'UTF8')
WHERE NOT EXISTS (
    SELECT 1 FROM pg_catalog.pg_database WHERE datname = :'app_db'
)
\gexec

SELECT format('GRANT ALL PRIVILEGES ON DATABASE %I TO %I', :'app_db', :'app_user')
\gexec
