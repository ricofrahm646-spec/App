# JARVIS — Full AI Trading Operating System

JARVIS is a modular AI trading platform that can design, generate, backtest, optimise and live-trade strategies on MetaTrader 5, while integrating TradingView and Telegram, and exposing a modern chat-driven web dashboard.

> ⚠️ JARVIS is a research and engineering platform. It makes **no guarantees of profitability**. Trade only with capital you can afford to lose. The default risk profile is conservative and the system is built to *prevent* losses rather than promise gains.

## Capabilities

- **AI Chat Cockpit** – plain-language commands such as *"Build a gold scalping bot"*, *"Add a trailing stop"* or *"Improve drawdown"* generate code, MQL5 files and new modules automatically.
- **MetaTrader 5 control** – open / close / modify orders, position sizing, equity & drawdown analytics. Includes a mock connector so the system runs end-to-end without MT5 installed.
- **MQL5 file generator + auto-installer** – produces `.mq5` Expert Advisors and indicators from Jinja2 templates and copies them into the correct MT5 data folders.
- **Strategy library** – Scalping, ICT, Smart Money, Liquidity Sweeps, Orderblocks, Trend Following, Mean Reversion, Breakouts, Momentum, Session Trading.
- **Backtesting** – vectorised tick / OHLC backtests, Monte Carlo, Walk-Forward, slippage + spread simulation, multi-timeframe.
- **Reinforcement learning & optimisation** – PyTorch / XGBoost / Optuna / Genetic Algorithm optimisers.
- **Risk Engine** – single-position rule, no opposing-direction trades, hard 20% loss cut, dynamic lot sizing.
- **Dashboard** – Next.js + Tailwind + WebSockets, real-time balance / equity / margin / winrate / open trades / KI status.
- **Telegram bot** – live signal & trade notifications.
- **TradingView integration** – webhook receiver, Pine Script generator, alerts mapped to MT5 orders (Forex only).
- **Production stack** – FastAPI + PostgreSQL + Redis + Docker Compose.

## Repository layout

```
backend/            FastAPI service: API, websockets, orchestration
frontend/           Next.js + Tailwind dashboard & chat UI
ai/                 AI chat engine, LLM router, RL & optimisation
mt5/                MetaTrader 5 connector (real + mock)
mql5/               MQL5 generator, templates, auto-installer
backtesting/        Vectorised backtests, Monte Carlo, Walk-Forward
strategies/         Strategy library (base + concrete strategies)
tradingview/        Webhook receiver, Pine Script generator
telegram/           Telegram bot
database/           SQLAlchemy models, Alembic migrations, init SQL
deployment/         Docker, compose, nginx, systemd, autostart
logging/            Loguru config, log sinks
risk_management/    Risk engine, position sizer, kill switch
tests/              Pytest suite
scripts/            Dev / ops helpers
```

## Quick start (Docker)

```bash
cp .env.example .env
docker compose -f deployment/docker-compose.yml up --build
```

- Backend API: <http://localhost:8000/docs>
- Frontend dashboard: <http://localhost:3000>
- Postgres: `localhost:5432` (user/pass in `.env`)
- Redis: `localhost:6379`

## Local development

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## AI chat examples

```
Build a new gold-scalping bot
Create an ICT bot for EURUSD M5
Optimise the current strategy
Add a trailing stop
Improve the winrate of the trend follower
Build a Telegram signal bot
Reduce drawdown on the breakout strategy
Generate a custom RSI divergence indicator
```

Each command is parsed into a structured intent and dispatched to the relevant generator (strategy / indicator / EA / module).

## Safety rules

- Never opens Buy and Sell on the same symbol simultaneously.
- Hard cap of **1 open trade** at any time (configurable).
- Auto-closes any trade as soon as floating loss exceeds **20%** of margin.
- Emergency kill switch flattens all positions and pauses the AI.

## Configuration

See `.env.example`. Secrets (LLM keys, Telegram token, MT5 credentials) are encrypted at rest using `cryptography.Fernet`.

## License

MIT
