-- JARVIS — initial Postgres bootstrap. Tables are created by SQLAlchemy on
-- backend startup; this file just provides extensions + sensible defaults.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
