# JARVIS - AI Trading Operating System

JARVIS is a modular AI-assisted trading platform skeleton for research,
strategy generation, backtesting, MetaTrader 5 automation, Telegram alerts,
TradingView webhooks and an internal chat-driven operator interface.

> Important: this repository does not promise profits, win rates or risk-free
> trading. All generated strategies must be validated with realistic data,
> slippage, spreads and live risk controls before any real-money use.

## Modules

- `backend` - FastAPI API, WebSocket status stream and orchestration services
- `frontend` - Next.js, React, TypeScript and Tailwind dashboard/chat UI
- `ai` - strategy generation, optimization and model-service abstractions
- `mt5` - MetaTrader 5 connector and installer helpers
- `mql5` - generated Expert Advisor/indicator templates
- `backtesting` - vectorized and event-driven backtesting engines
- `strategies` - strategy catalog and generated strategy specifications
- `tradingview` - Pine Script templates and webhook payload handling
- `telegram` - notification service integration
- `database` - PostgreSQL schema/bootstrap scripts
- `deployment` - Dockerfiles and startup assets
- `logging` - runtime log directory
- `risk_management` - risk policy documentation and engine contracts

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Backend: <http://localhost:8000/docs>

Frontend: <http://localhost:3000>

## Safety defaults

The runtime risk engine enforces the requested conservative constraints:

- maximum one open trade at a time
- no simultaneous buy and sell exposure on the same symbol
- automatic lot sizing based on account risk
- emergency-close signal once an open position reaches a 20% loss threshold
- secret values are stored through an encryption helper instead of plaintext APIs

## Development notes

This is the first complete architecture pass. The platform contains real
interfaces, validators, generators and service boundaries, while broker-specific
actions that require a local MetaTrader terminal are implemented as auditable
command plans and filesystem operations.

Optional AI/MT5 dependencies are split from the core backend image:

```bash
pip install -r backend/requirements-ai.txt
pip install -r backend/requirements-mt5.txt
```
