# JARVIS - Full AI Trading Operating System

JARVIS is a modular trading operating system built to orchestrate strategy design, AI-assisted optimization, backtesting, MT5 automation, notification delivery, and operator control through a chat-first interface.

## Core capabilities

- AI chat interface for strategy and bot requests
- FastAPI backend for orchestration and integrations
- Next.js dashboard for live system visibility
- Risk engine with hard trading safety constraints
- MT5 connector abstraction with safe trade rules
- MQL5 file generator and installer pipeline
- Telegram notification integration
- TradingView webhook and alert integration
- Backtesting service blueprint for walk-forward and Monte Carlo evaluation
- PostgreSQL and Redis infrastructure via Docker Compose

## Architecture overview

```text
/backend            FastAPI application and orchestration logic
/frontend           Next.js dashboard and chat UI
/ai                 Training and optimization blueprints
/mt5                MT5 integration notes and scripts
/mql5               MQL5 templates and generated files
/backtesting        Backtesting engine blueprint
/strategies         Strategy registry and metadata
/tradingview        TradingView integration assets
/telegram           Telegram integration assets
/database           SQL bootstrap files
/deployment         Dockerfiles and deployment notes
/logging            Logging configuration
/risk_management    Central risk rules and policy files
```

## Safety model

JARVIS intentionally avoids unrealistic profit claims and enforces strict guardrails:

- Never open Buy and Sell simultaneously on the same managed account
- Never hold more than one active trade at a time
- Close trades when loss exceeds the configured maximum threshold
- Require explicit risk calculation before order execution
- Separate strategy generation from trade execution through reviewed modules

## Getting started

1. Copy `.env.example` to `.env`
2. Start infrastructure with Docker Compose
3. Run the backend:

   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Run the frontend:

   ```bash
   cd frontend
   npm run dev
   ```

## Current scope

This repository now contains the production-oriented foundation for JARVIS: architecture, API contracts, dashboard scaffolding, MT5 integration interfaces, MQL5 generation templates, risk rules, and deployment assets. Strategy alpha generation, broker-side compilation, and live automation still require environment-specific credentials, MT5 terminal access, and staged testing before production use.
