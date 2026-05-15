CREATE TABLE IF NOT EXISTS strategy_runs (
    id SERIAL PRIMARY KEY,
    strategy_id VARCHAR(100) NOT NULL,
    mode VARCHAR(30) NOT NULL,
    result_json JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trade_events (
    id SERIAL PRIMARY KEY,
    ticket BIGINT NOT NULL,
    symbol VARCHAR(30) NOT NULL,
    side VARCHAR(10) NOT NULL,
    volume NUMERIC(12,4) NOT NULL,
    pnl_percent NUMERIC(8,3),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
