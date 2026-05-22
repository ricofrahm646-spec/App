CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    entry_price DECIMAL(18, 5),
    sl DECIMAL(18, 5),
    tp DECIMAL(18, 5),
    status VARCHAR(20) DEFAULT 'open',
    strategy_name VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_configurations (
    id SERIAL PRIMARY KEY,
    bot_name VARCHAR(50) UNIQUE NOT NULL,
    config_json JSONB,
    active BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS performance_logs (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(50),
    metric_value DECIMAL(18, 5),
    logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
