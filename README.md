# JARVIS — AI Trading Operating System

JARVIS is a modular AI trading operating system designed for **professional strategy research, controlled execution, and iterative optimization**.

## Mission

Build a production-oriented foundation that can:

- generate and evolve trading strategies,
- backtest and stress-test them,
- operate with strict risk controls,
- integrate with MetaTrader 5, TradingView, and Telegram,
- and expose everything through a modern dashboard and AI chat interface.

> Important: JARVIS does **not** promise unrealistic returns. The platform emphasizes risk management, transparency, and responsible automation.

---

## High-Level Architecture

- **Backend**: FastAPI (Python) orchestrating AI, trading, generation, and integrations.
- **Frontend**: Next.js + React + Tailwind dashboard with real-time UI modules.
- **Data**: PostgreSQL for persistent state, Redis for low-latency caching/events.
- **Infra**: Docker Compose for local multi-service orchestration.
- **MT5/MQL5 Tooling**: Automated code generation and deployment helpers.

---

## Repository Structure

```text
/backend
/frontend
/ai
/mt5
/mql5
/backtesting
/strategies
/tradingview
/telegram
/database
/deployment
/logging
/risk_management
```

---

## Quick Start

1. Copy environment values:

   ```bash
   cp .env.example .env
   ```

2. Start stack:

   ```bash
   docker compose up --build
   ```

3. Open:
   - Backend: `http://localhost:8000/docs`
   - Frontend: `http://localhost:3000`

---

## Core Safety Rules (Current Foundation)

- Never open Buy and Sell simultaneously on the same strategy instance.
- Maximum one concurrent trade (global risk lock).
- Forced risk intervention when loss threshold reaches configured guardrail (default 20%).
- All trade commands pass through risk validation before execution.

---

## Current Status

This commit provides a **production-grade foundation scaffold**:

- modular folder layout,
- backend service contracts and orchestration,
- frontend dashboard/chat skeleton,
- MT5/MQL5 generation and installer helpers,
- backtesting engine interfaces,
- Dockerized environment with PostgreSQL and Redis.

Feature depth (advanced strategy logic, full RL training, live broker execution hardening) is intentionally staged for iterative expansion.
