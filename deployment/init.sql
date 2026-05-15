-- JARVIS PostgreSQL Initialization Script

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
SET timezone = 'UTC';

-- Create indexes after table creation (handled by SQLAlchemy Alembic)
-- This script runs once on first container start

SELECT 'JARVIS database initialized' AS status;
