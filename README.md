# JARVIS — AI Trading Operating System

> **Professional AI-powered trading platform with automated bot generation, MT5 integration, backtesting, and real-time risk management.**

---

## Architecture Overview

```
jarvis/
├── backend/              # FastAPI Python backend
│   ├── app/
│   │   ├── main.py       # Application entry point
│   │   ├── config.py     # Pydantic settings
│   │   ├── api/routes/   # 75+ REST endpoints
│   │   ├── core/         # DB, security, WebSocket, logging
│   │   ├── models/       # SQLAlchemy ORM models
│   │   └── services/     # MT5, AI, Risk, Telegram, TradingView
├── frontend/             # Next.js 14 + React + Tailwind dashboard
│   └── src/
│       ├── app/          # App router pages
│       ├── components/   # Dashboard, Chat, Trading, Backtesting UI
│       ├── store/        # Zustand state management
│       └── lib/          # API client, WebSocket
├── ai/
│   └── agents/           # RL Strategy Learner, Market Analyzer, Optimizer
├── mql5/
│   ├── generator.py      # MQL5 EA/Indicator code generator
│   ├── installer.py      # Auto-install to MetaTrader 5
│   └── generated/        # Generated MQL5 files
├── backtesting/
│   └── engine.py         # Tick/bar backtest, Walk-Forward, Monte Carlo
├── strategies/           # Python trading strategy implementations
│   ├── base.py           # Abstract base class
│   ├── scalping.py       # RSI + Stoch scalping
│   ├── ict.py            # ICT: Order Blocks, FVGs, Liquidity Sweeps
│   ├── trend_following.py# EMA crossover + ADX
│   ├── mean_reversion.py # Bollinger Bands + RSI
│   └── registry.py       # Strategy factory
├── risk_management/
│   └── engine.py         # Position sizing, drawdown control, validation
├── tradingview/
│   └── pine_scripts/     # Pine Script v5 strategy templates
├── telegram/             # Telegram bot integration
├── database/
│   └── migrations/       # Alembic migration scripts
├── logging/
│   └── setup.py          # Loguru structured logging
└── deployment/
    ├── docker-compose.yml # Full Docker stack
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    └── nginx.conf         # Reverse proxy
```

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- (Optional) MetaTrader 5 on Windows for live trading
- OpenAI API key for AI chat features

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
nano .env
```

### 2. Start with Docker

```bash
chmod +x start.sh
./start.sh docker
```

### 3. Access JARVIS

| Service    | URL                         |
|------------|---------------------------  |
| Dashboard  | http://localhost:3000       |
| API        | http://localhost:8000       |
| API Docs   | http://localhost:8000/docs  |
| Flower     | http://localhost:5555       |

### Development Mode (hot reload)

```bash
./start.sh dev
```

---

## Core Features

### AI Chat Interface

Type natural language commands:

```
"Build a new Gold scalping bot"
"Create an ICT strategy for EURUSD"
"Optimize my current strategy"
"Add a news filter to the EA"
"Improve the winrate"
"Build a Telegram signal bot"
```

JARVIS will:
- Generate complete MQL5 Expert Advisor files
- Write Python strategy classes
- Create backtesting scripts
- Auto-install to MetaTrader 5

### MT5 Integration

```python
# Automatic connection
from backend.app.services.mt5_service import MT5Service

mt5 = MT5Service()
await mt5.connect(login=12345, password="pass", server="MetaQuotes-Demo")

# Place order (validates: max 1 trade, no opposing positions)
result = await mt5.place_order(
    symbol="XAUUSD",
    order_type="BUY",
    lot=0.01,
    sl=1900.00,
    tp=1950.00,
)

# Get account info
account = await mt5.get_account_info()
# {"balance": 10000, "equity": 10250, "margin": 85, ...}
```

### Risk Engine

```python
from risk_management.engine import RiskEngine, RiskSettings

engine = RiskEngine(RiskSettings(
    risk_per_trade_pct=2.0,
    max_total_drawdown_pct=20.0,
    max_concurrent_trades=1,
    min_risk_reward=1.5,
))

# Validate before placing
report = engine.validate_trade(
    symbol="XAUUSD",
    direction="BUY",
    entry_price=1920.0,
    sl_price=1910.0,
    tp_price=1945.0,
    account_balance=10000,
    account_equity=9800,
    open_trades=[],
)
# RiskReport(allowed=True, suggested_lot=0.05, risk_reward=2.5)
```

### Strategy System

```python
from strategies.registry import get_strategy
from strategies.base import StrategyConfig

config = StrategyConfig(symbol="XAUUSD", timeframe="M5", risk_percent=2.0)
strategy = get_strategy("SCALPING", config)

signal = strategy.generate_signal(ohlcv_dataframe)
# Signal(action='BUY', entry=1920.0, sl=1913.5, tp=1930.2, confidence=0.82)
```

### MQL5 Generator

```python
from mql5.generator import MQL5Generator

gen = MQL5Generator()

# Generate Gold scalping EA
ea_code = gen.generate_scalping_ea("MyGoldScalper", symbol="XAUUSD")
path = gen.save_ea("MyGoldScalper", ea_code)

# Install to MT5 automatically
gen.install_to_mt5(path, mt5_path="C:/Program Files/MetaTrader 5")
```

### Backtesting

```python
from backtesting.engine import BacktestEngine, BacktestConfig

engine = BacktestEngine()
result = engine.run_backtest(
    strategy_fn=my_strategy_fn,
    config=BacktestConfig(
        symbol="EURUSD",
        timeframe="H1",
        start_date="2023-01-01",
        end_date="2024-01-01",
    ),
    data=ohlcv_df,
)
# BacktestResult(winrate=58.3, profit_factor=1.85, max_drawdown=8.2, sharpe=1.42)
```

---

## API Reference

### Trading Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/trading/account` | Account info |
| GET | `/api/trading/positions` | Open positions |
| POST | `/api/trading/order` | Place order |
| DELETE | `/api/trading/order/{ticket}` | Close order |
| POST | `/api/trading/connect` | Connect MT5 |

### AI Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/chat` | Chat with JARVIS |
| POST | `/api/ai/generate/bot` | Generate trading bot |
| POST | `/api/ai/generate/indicator` | Generate indicator |
| POST | `/api/ai/install/mt5` | Install to MT5 |

### MQL5 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/mql5/generate/ea` | Generate Expert Advisor |
| GET | `/api/mql5/files` | List generated files |
| POST | `/api/mql5/install/{filename}` | Install to MT5 |

### Backtesting Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/backtesting/run` | Run backtest |
| POST | `/api/backtesting/walkforward` | Walk-forward analysis |
| POST | `/api/backtesting/montecarlo` | Monte Carlo simulation |

---

## Telegram Setup

1. Create bot via [@BotFather](https://t.me/botfather)
2. Get your Chat ID from [@userinfobot](https://t.me/userinfobot)
3. Configure in dashboard or via API:

```bash
curl -X POST http://localhost:8000/api/telegram/configure \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_TOKEN", "chat_id": "YOUR_CHAT_ID"}'
```

JARVIS will send alerts for:
- 🟢 Buy/Sell signals
- 📊 Trade open/close notifications
- ⚠️ Risk warnings
- 📈 Daily P&L summary

---

## TradingView Webhook

1. Set your webhook URL in TradingView alerts:
   ```
   http://your-server.com/api/tradingview/webhook
   ```
2. Configure `TRADINGVIEW_WEBHOOK_SECRET` in `.env`
3. Use the Pine Script templates from `tradingview/pine_scripts/`

Alert message format:
```json
{
  "symbol": "EURUSD",
  "action": "BUY",
  "price": 1.0850,
  "sl": 1.0820,
  "tp": 1.0900,
  "strategy": "JARVIS_BASE"
}
```

---

## Supported Strategies

| Strategy | Description |
|----------|-------------|
| SCALPING | M5 RSI + Stochastic + EMA for Gold/Forex |
| ICT | Order Blocks, FVGs, Liquidity Sweeps, Kill Zones |
| TREND | EMA 50/200 crossover + ADX filter |
| MEAN_REVERSION | Bollinger Bands + RSI extremes |
| BREAKOUT | Range breakout with volume confirmation |
| MOMENTUM | Price momentum scoring |

---

## Risk Rules (Enforced)

- Maximum 1 trade open simultaneously
- No opposing Buy+Sell on same symbol
- Maximum 20% total account drawdown → emergency stop
- Maximum 2% risk per trade (configurable)
- Minimum 1.5:1 risk-reward ratio
- Maximum spread filter before entry
- Dynamic position sizing based on ATR

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| AI/ML | PyTorch, XGBoost, Optuna, scikit-learn |
| Database | PostgreSQL 16, Redis 7 |
| Backtesting | VectorBT, Backtrader, Pandas, NumPy |
| Deployment | Docker, Docker Compose, Nginx |
| Trading | MetaTrader 5, MQL5 |
| Notifications | Telegram Bot API |
| Charting | TradingView Webhooks, Pine Script v5 |

---

## Security

- All API keys encrypted with Fernet symmetric encryption
- JWT authentication for API access
- HMAC-SHA256 webhook signature validation
- Rate limiting on all endpoints
- No credentials stored in plain text
- Separate error logs with exception traces

---

## License

MIT License — For educational and personal use. **Not financial advice.**
Trading involves significant risk of loss. Use at your own risk.
