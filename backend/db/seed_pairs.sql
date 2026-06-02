-- Seed the tradable instruments used by local development.
--
-- Run after Alembic has created the schema:
--   psql -U tradesignal_app -d tradesignal -f db/seed_pairs.sql

INSERT INTO pairs (symbol, base_currency, quote_currency, display_name, is_active)
VALUES
    ('EURUSD', 'EUR', 'USD', 'Euro / US Dollar', true),
    ('GBPUSD', 'GBP', 'USD', 'British Pound / US Dollar', true),
    ('XAUUSD', 'XAU', 'USD', 'Gold / US Dollar', true)
ON CONFLICT (symbol) DO UPDATE
SET
    base_currency = EXCLUDED.base_currency,
    quote_currency = EXCLUDED.quote_currency,
    display_name = EXCLUDED.display_name;
