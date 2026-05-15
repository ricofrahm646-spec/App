# JARVIS — AI Trading Operating System

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**JARVIS** is a professional AI-powered Trading Operating System that combines automated trade execution, real-time market analysis, AI-driven predictions, and comprehensive risk management into a unified platform. Built for forex traders who demand institutional-grade tooling.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NGINX REVERSE PROXY                         │
│                     (SSL · Gzip · Rate Limit)                      │
├────────────────────────────┬────────────────────────────────────────┤
│           :80 /            │          :80 /api/ · /ws/              │
│            ▼               │               ▼                       │
│  ┌─────────────────┐       │    ┌──────────────────────┐           │
│  │    FRONTEND      │       │    │      BACKEND          │           │
│  │    Next.js 16    │       │    │    FastAPI + Uvicorn   │           │
│  │    React 19      │◄──────┼───►│    Python 3.11         │           │
│  │    Tailwind CSS  │  WS   │    │                        │           │
│  │    :3000         │       │    │    :8000                │           │
│  └─────────────────┘       │    └───────┬──────┬─────────┘           │
│                            │            │      │                     │
│                            │            ▼      ▼                     │
│                            │    ┌───────┐  ┌───────┐                │
│                            │    │ Redis │  │Postgre│                │
│                            │    │  :6379│  │SQL    │                │
│                            │    │ Cache │  │ :5432 │                │
│                            │    └───────┘  └───────┘                │
└────────────────────────────┴────────────────────────────────────────┘
                                      │
            ┌─────────────────────────┼──────────────────────────┐
            │                         │                          │
            ▼                         ▼                          ▼
   ┌─────────────────┐    ┌────────────────────┐    ┌──────────────────┐
   │   MetaTrader 5   │    │   Telegram Bot      │    │  TradingView     │
   │   Trade Exec     │    │   Notifications     │    │  Webhooks        │
   │   Market Data    │    │   Commands          │    │  Pine Scripts    │
   │   Account Mon.   │    │   Daily Reports     │    │  Signal Recv.    │
   └─────────────────┘    └────────────────────┘    └──────────────────┘
            │
            ▼
   ┌─────────────────────────────────────────────┐
   │            AI / ML PIPELINE                  │
   │  ┌──────────┐ ┌───────────┐ ┌────────────┐  │
   │  │  LSTM    │ │  Regime   │ │ Strategy   │  │
   │  │ Predictor│ │ Detector  │ │ Optimizer  │  │
   │  └──────────┘ └───────────┘ └────────────┘  │
   │  ┌──────────┐ ┌───────────┐ ┌────────────┐  │
   │  │ Ensemble │ │Confidence │ │ RL Trainer │  │
   │  │ Engine   │ │  Scorer   │ │            │  │
   │  └──────────┘ └───────────┘ └────────────┘  │
   └─────────────────────────────────────────────┘
```

---

## Features

### Trading Engine
- **MetaTrader 5 Integration** — Direct connection for order execution, market data, and account monitoring
- **Safety Rules** — Max 1 trade at a time, no simultaneous buy/sell, mandatory stop-loss on every order
- **Auto Loss Control** — Positions auto-close at 20% loss threshold
- **Auto-reconnect** — Resilient connection with configurable retry logic

### AI & Machine Learning
- **LSTM Market Predictor** — Multi-timeframe price direction forecasting
- **Market Regime Detection** — Automatic identification of trending, ranging, and volatile conditions
- **Ensemble Inference** — Weighted model averaging with confidence scoring
- **Reinforcement Learning** — Strategy optimization through reward-based training
- **AI Chat Assistant** — Conversational trading analysis powered by GPT-4o / Claude

### Strategy Framework
- **8 Built-in Strategies** — Trend following, mean reversion, breakout, scalping, momentum, ICT, session trading
- **Strategy Evaluator** — Automated ranking and performance scoring
- **Walk-Forward Analysis** — Out-of-sample validation for strategy robustness

### Risk Management
- **Position Sizing** — Kelly-criterion-inspired dynamic sizing
- **Drawdown Control** — Real-time monitoring with configurable circuit breakers
- **Daily Loss Limits** — Automatic trading halt when daily loss thresholds are breached
- **Kill Switch** — Emergency halt for all trading activity

### Backtesting
- **VectorBT Engine** — High-performance vectorized backtesting
- **Tick-Level Engine** — Granular simulation with realistic fills
- **Monte Carlo Analysis** — Statistical robustness testing
- **Performance Analytics** — Sharpe ratio, Sortino, max drawdown, win rate, and 30+ metrics

### Notifications & Integrations
- **Telegram Bot** — Trade signals, risk warnings, daily P&L reports, and command interface
- **TradingView Webhooks** — Receive and auto-execute Pine Script alerts
- **MQL5 Code Generator** — Auto-generate Expert Advisors and indicators

### Dashboard
- **Real-time WebSocket** — Live account metrics, trade updates, and heartbeat monitoring
- **REST API** — Full CRUD for strategies, backtests, settings, and trading operations
- **Next.js Frontend** — Modern, responsive trading dashboard

---

## Prerequisites

- **Docker** >= 24.0 and **Docker Compose** >= 2.20
- **Git** >= 2.30

For local development without Docker:
- **Python** 3.11+
- **Node.js** 20+
- **PostgreSQL** 15+
- **Redis** 7+

---

## Quick Start

### Docker Deployment (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/jarvis-trading-os.git
cd jarvis-trading-os

# 2. Configure environment
cp deployment/.env.example deployment/.env
# Edit deployment/.env with your credentials

# 3. Build and start all services
make build
make up

# 4. Verify services are running
make status

# 5. View logs
make logs
```

The application will be available at:
- **Frontend Dashboard**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Manual Development Setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev

# PostgreSQL & Redis (separate terminal)
docker compose -f deployment/docker-compose.yml up postgres redis
```

---

## Configuration

All configuration is managed through environment variables. See `deployment/.env.example` for the complete reference.

| Category | Key Variables | Description |
|---|---|---|
| **Application** | `ENVIRONMENT`, `DEBUG`, `SECRET_KEY` | App mode and security |
| **Database** | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` | PostgreSQL connection |
| **Cache** | `REDIS_URL` | Redis connection string |
| **MT5** | `MT5_ACCOUNT`, `MT5_PASSWORD`, `MT5_SERVER` | Broker connection |
| **Telegram** | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Notification bot |
| **TradingView** | `TRADINGVIEW_WEBHOOK_SECRET` | Webhook authentication |
| **AI** | `OPENAI_API_KEY`, `AI_PROVIDER` | LLM provider config |
| **Risk** | `RISK_MAX_DRAWDOWN`, `RISK_MAX_DAILY_LOSS_PERCENT` | Risk thresholds |

---

## Project Structure

```
jarvis-trading-os/
├── backend/                    # FastAPI application server
│   ├── app/
│   │   ├── api/routes/         # REST API endpoints
│   │   ├── core/               # Settings, security, logging
│   │   ├── middleware/         # Error handling, CORS
│   │   ├── models/             # Pydantic schemas
│   │   ├── services/           # Service orchestration
│   │   └── main.py             # App factory & WebSocket
│   └── requirements.txt
│
├── ai/                         # AI/ML pipeline
│   ├── models/                 # LSTM, regime detector, optimizer
│   ├── training/               # Model training & RL
│   ├── chat/                   # AI chat engine
│   └── inference/              # Real-time prediction engine
│
├── mt5/                        # MetaTrader 5 integration
│   ├── connector/              # Client, trade executor, market data
│   └── utils/                  # Helpers & utilities
│
├── strategies/                 # Trading strategy framework
│   ├── implementations/        # 8 built-in strategies
│   └── evaluation/             # Strategy evaluator & ranking
│
├── risk_management/            # Risk engine & portfolio risk
├── backtesting/                # Backtesting engines & analysis
│   ├── engines/                # VectorBT & tick-level engines
│   └── analysis/               # Monte Carlo, walk-forward, perf
│
├── database/                   # Database models & migrations
├── telegram/                   # Telegram bot integration
├── tradingview/                # TradingView webhooks & Pine scripts
├── mql5/                       # MQL5 code generation
│   ├── generators/             # EA & indicator generators
│   ├── templates/              # Base templates
│   └── compiler/               # MQL5 compiler interface
│
├── logging/                    # Trade logger
├── frontend/                   # Next.js dashboard
│
├── deployment/                 # Docker & deployment configs
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── nginx.conf
│   └── .env.example
│
├── Makefile                    # Common commands
├── .dockerignore
├── .gitignore
└── README.md
```

---

## Module Descriptions

### `backend/` — API Server
The FastAPI application serves as the central hub. It exposes RESTful endpoints for trading operations, strategy management, backtesting, AI chat, and system configuration. WebSocket support enables real-time dashboard updates with heartbeat monitoring.

### `ai/` — AI/ML Pipeline
Houses the LSTM-based market predictor, market regime detector (trending/ranging/volatile), strategy optimizer, and reinforcement learning trainer. The inference engine supports model ensembles with weighted averaging, voting, and confidence-calibrated predictions.

### `mt5/` — MetaTrader 5 Connector
Thread-safe client with built-in safety rules: mandatory stop-loss, max 1 trade, no opposing positions, and automatic 20% loss closure. Includes auto-reconnect, account monitoring, and OHLCV/tick data retrieval.

### `strategies/` — Strategy Framework
Eight production strategies with a common base class. The evaluator scores strategies across multiple metrics and supports walk-forward analysis for out-of-sample validation.

### `risk_management/` — Risk Engine
Enforces position sizing via dynamic Kelly-criterion adjustment, daily loss limits, drawdown circuit breakers, and an emergency kill switch. All trades pass through pre-trade risk checks.

### `backtesting/` — Backtesting Suite
VectorBT engine for fast vectorized backtests and a tick-level engine for granular simulation. Monte Carlo analysis provides statistical confidence intervals on strategy performance.

### `telegram/` — Notification Bot
Async Telegram bot with rate limiting and retry logic. Sends formatted trade signals, open/close confirmations, risk warnings, and daily performance reports.

### `tradingview/` — TradingView Integration
Webhook receiver for TradingView alerts with signature validation. Pine Script generator creates custom indicators and alert conditions.

### `mql5/` — MQL5 Code Generator
Generates Expert Advisors and custom indicators from strategy definitions. Includes template engine and compiler interface for the MQL5 toolchain.

---

## API Documentation

Once the backend is running, interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check |
| `GET` | `/api/v1/dashboard/summary` | Account summary & metrics |
| `POST` | `/api/v1/trading/order` | Place a trade order |
| `GET` | `/api/v1/trading/positions` | List open positions |
| `POST` | `/api/v1/strategies/evaluate` | Evaluate a strategy |
| `POST` | `/api/v1/backtesting/run` | Run a backtest |
| `POST` | `/api/v1/ai/chat` | Chat with AI assistant |
| `POST` | `/api/v1/tradingview/webhook` | TradingView alert receiver |
| `POST` | `/api/v1/mql5/generate` | Generate MQL5 code |
| `GET/PUT` | `/api/v1/settings` | System configuration |
| `WS` | `/ws/{client_id}` | Real-time WebSocket feed |

---

## Development

### Running Tests

```bash
# All tests
make test

# Backend only
cd backend && python -m pytest tests/ -v

# With coverage
cd backend && python -m pytest tests/ --cov=app --cov-report=html
```

### Code Quality

```bash
# Linting
ruff check .

# Type checking
mypy backend/app

# Frontend lint
cd frontend && npm run lint
```

### Database Migrations

```bash
# Generate a new migration
make migrate-create MSG="add_trade_history_table"

# Apply migrations
make migrate

# Rollback last migration
cd backend && alembic downgrade -1
```

---

## Security Considerations

- **Never commit `.env` files** — Use `.env.example` as a template
- **Rotate `SECRET_KEY`** regularly in production
- **Enable SSL/TLS** via the nginx configuration before exposing to the internet
- **API rate limiting** is enforced at the nginx layer (30 req/s for API, 60 req/s general)
- **MT5 credentials** are stored only in environment variables, never in code
- **Telegram bot token** should have restricted permissions (no admin rights)
- **TradingView webhooks** are validated against a shared secret and IP allowlist
- All containers run as **non-root users**
- Database passwords must be changed from defaults before production deployment

---

## License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2024 JARVIS Trading OS

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
