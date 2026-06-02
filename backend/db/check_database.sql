-- Quick local verification script.
--
-- Run after migrations and optional seeding:
--   psql -U tradesignal_app -d tradesignal -f db/check_database.sql

SELECT current_database() AS database_name, current_user AS connected_user;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

SELECT typname AS enum_name
FROM pg_type
WHERE typname IN ('analysis_run_status', 'analysis_run_trigger', 'signal_direction')
ORDER BY typname;

SELECT symbol, base_currency, quote_currency, display_name, is_active
FROM pairs
ORDER BY symbol;
