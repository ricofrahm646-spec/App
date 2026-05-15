create table if not exists strategy_runs (
    id bigserial primary key,
    strategy_name text not null,
    environment text not null default 'paper',
    status text not null,
    created_at timestamptz not null default now()
);

create table if not exists trade_events (
    id bigserial primary key,
    strategy_name text not null,
    symbol text not null,
    direction text not null,
    state text not null,
    risk_fraction numeric(10, 4) not null default 0.0,
    created_at timestamptz not null default now()
);
