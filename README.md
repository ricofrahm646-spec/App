# JARVIS - AI Trading Operating System

JARVIS is a modular AI-assisted trading platform scaffold built around FastAPI, Next.js,
PostgreSQL, Redis, MetaTrader 5, MQL5 generation, TradingView webhooks, Telegram alerts,
backtesting and centralized risk management.

> This project does not promise fixed winrates or guaranteed profitability. All strategy
> output must be validated with broker-quality data, walk-forward testing and conservative
> live-risk controls before real capital is used.

## Modules

```text
/backend         FastAPI API, WebSocket endpoints and service wiring
/frontend        Next.js, React, TypeScript and Tailwind dashboard
/ai              Chat orchestration and AI/ML capability coordination
/mt5             MetaTrader 5 connector and installer
/mql5            Expert Advisor and indicator code generator
/backtesting     Backtest, walk-forward and Monte Carlo facade
/strategies      Strategy registry and prompt-to-spec generation
/tradingview     Pine Script template and webhook validation
/telegram        Telegram notification client
/database        SQLAlchemy models and session helpers
/deployment      Docker/PostgreSQL deployment assets
/logging         Operational logging notes
/risk_management Centralized trading risk engine
```

## Start locally

```bash
cp .env.example .env
docker compose up --build
```

- Backend: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>
- Dashboard: <http://localhost:3000>

## Safety defaults

- Live trading is disabled by default.
- Paper-mode execution is available for development.
- The risk engine blocks more than one open trade.
- Buy and sell exposure at the same time is rejected.
- A forced-close path is available when configured loss thresholds are reached.
- Tokens are designed to be encrypted before persistence through `SecretVault`.

## Core API examples

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/dashboard/summary
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Baue einen neuen Gold-Scalping-Bot mit Trailing Stop","dry_run":true}'
```

## Current implementation status

This is the initial professional architecture and runnable scaffold. It includes:

- FastAPI backend routes for chat, dashboard, MT5, strategies, risk, backtesting, Telegram
  and TradingView;
- Next.js dashboard with live summary polling and internal AI chat interface;
- MQL5 Expert Advisor and indicator generator;
- MT5 installer abstraction for copying `.mq5` files and optional compiler execution;
- TradingView Forex-only webhook validation and Pine Script template;
- Telegram Bot API notifier;
- PostgreSQL schema bootstrap and Docker Compose stack.

Production hardening should connect real broker tick data, terminal-side MT5 chart automation,
database persistence for generated files, audit logs, CI, authentication and operator roles.
