-- JARVIS Trading OS Database Schema

CREATE TABLE IF NOT EXISTS strategies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(100) NOT NULL DEFAULT 'custom',
    description TEXT DEFAULT '',
    parameters JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    winrate FLOAT DEFAULT 0.0,
    profit_factor FLOAT DEFAULT 0.0,
    total_trades INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    volume FLOAT NOT NULL,
    open_price FLOAT NOT NULL,
    close_price FLOAT,
    sl FLOAT,
    tp FLOAT,
    open_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    close_time TIMESTAMP WITH TIME ZONE,
    profit FLOAT DEFAULT 0.0,
    commission FLOAT DEFAULT 0.0,
    swap FLOAT DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'open',
    strategy_name VARCHAR(255) DEFAULT 'manual',
    magic_number INTEGER DEFAULT 0,
    comment TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    strategy_name VARCHAR(255) NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    timeframe VARCHAR(10) DEFAULT 'H1',
    entry_price FLOAT,
    sl FLOAT,
    tp FLOAT,
    executed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS account_snapshots (
    id SERIAL PRIMARY KEY,
    balance FLOAT NOT NULL,
    equity FLOAT NOT NULL,
    margin FLOAT DEFAULT 0.0,
    free_margin FLOAT DEFAULT 0.0,
    margin_level FLOAT DEFAULT 0.0,
    drawdown FLOAT DEFAULT 0.0,
    open_trades INTEGER DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    strategy_id INTEGER REFERENCES strategies(id),
    symbol VARCHAR(20) NOT NULL DEFAULT 'EURUSD',
    timeframe VARCHAR(10) NOT NULL DEFAULT 'H1',
    is_active BOOLEAN DEFAULT false,
    parameters JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades(open_time);
CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at);
CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON account_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_messages(created_at);

-- Insert default strategies
INSERT INTO strategies (name, type, description, parameters) VALUES
    ('EMA Scalper', 'scalping', 'EMA crossover with RSI filter for scalping', '{"fast_ema": 9, "slow_ema": 21, "rsi_period": 14}'),
    ('ICT Strategy', 'ict', 'ICT order block and liquidity sweep strategy', '{"htf_period": 200, "fvg_min_size": 0.0005}'),
    ('Smart Money Concepts', 'smart_money', 'BOS/CHoCH with supply demand zones', '{"swing_lookback": 10, "zone_touches_max": 3}'),
    ('Trend Follower', 'trend_following', 'Multi-MA trend following with ADX filter', '{"fast_ma": 20, "mid_ma": 50, "slow_ma": 200, "adx_threshold": 25}')
ON CONFLICT (name) DO NOTHING;
