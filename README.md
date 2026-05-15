# JARVIS - Full AI Trading Operating System

JARVIS is a modular trading operating system that combines:

- FastAPI backend services
- Next.js dashboard and operator console
- AI-assisted strategy generation workflows
- MT5 and MQL5 integration scaffolding
- Backtesting and risk management modules
- Telegram and TradingView integration points
- Docker-based local infrastructure with PostgreSQL and Redis

## Architecture Overview

```text
/backend            FastAPI API, orchestration, risk engine, chat workflows
/frontend           Next.js dashboard, command console, system status UI
/ai                 AI optimization and strategy improvement primitives
/mt5                MT5 connector and installation planner
/mql5               MQL5 template generation and EA/indicator blueprints
/backtesting        Backtesting orchestration and scenario definitions
/strategies         Strategy catalog, scoring and composition rules
/tradingview        Pine Script templates and webhook contracts
/telegram           Notification formatting and delivery abstractions
/database           SQL bootstrap and persistence design
/deployment         Dockerfiles and docker-compose stack
/logging            Central logging configuration helpers
/risk_management    Cross-module risk policy definitions
/docs               Additional architecture documentation
```

## Current Scope

This repository now contains a production-oriented scaffold for JARVIS:

- backend API surface for health, system overview and chat-driven build intents
- dashboard shell for monitoring the trading platform
- risk guardrails that enforce one trade at a time and force-close deep losers
- strategy, backtesting, MT5 and MQL5 generators as modular services
- Docker stack for backend, frontend, PostgreSQL and Redis

The scaffold does **not** claim profitable trading performance and intentionally avoids fake win rates or unrealistic promises.

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Full Stack with Docker

```bash
docker compose -f deployment/docker-compose.yml up --build
```

## Key Safety Rules

- never open buy and sell at the same time
- allow only one live trade at a time
- close trades when unrealized loss reaches 20 percent
- record actions and failures via structured logs
- keep tokens and credentials in environment variables only

## Next Implementation Steps

- connect real MT5 terminal automation on a Windows host or bridge service
- wire persistent chat history and job queue storage
- add live market data ingestion, WebSocket event streams and auth
- implement real compilation and deployment of MQL5 files inside MT5
- expand test coverage around strategy generation, order lifecycle and installers
