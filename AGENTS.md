# AGENTS.md

## Cursor Cloud specific instructions

### Repository structure

The `main` branch contains only a README. All application code lives on feature branches:

| Branch | Description |
|--------|-------------|
| `copilot/enhance-crypto-trading-bot` | Full autonomous crypto trading bot (modular: scanner, trader, notifier, logger) with tests |
| `copilot/create-python-trading-bot` | Simpler trading bot with technical indicators and comprehensive unit tests |
| `copilot/add-ai-ranking-trading-system` | Enhanced trading bot with AI ranking and live trading |
| `cursor/jarvis-ai-os-core-2bee` | Multi-agent orchestration system (JARVIS AI OS) |

To work on a branch, check out its files: `git checkout origin/<branch> -- .`

### Development environment

- **Python**: 3.12+ (system Python on Ubuntu 24.04)
- **Virtual env**: `/workspace/.venv` (created by update script)
- **Activate**: `source /workspace/.venv/bin/activate`
- **Dependencies**: `ccxt`, `pandas`, `numpy`, `python-dotenv`, `requests`, `pytest`, `flake8`

### Running tests

Each feature branch has its own test file(s). After checking out branch files:

- `copilot/enhance-crypto-trading-bot`: `pytest tests/ -v` (20 tests)
- `copilot/create-python-trading-bot`: `pytest test_trading_bot.py -v` (45 tests)

### Running lint

```
flake8 --max-line-length=100 --exclude=.venv .
```

### Running the bot

The `enhance-crypto-trading-bot` and `create-python-trading-bot` branches can run without API keys for read-only market scanning:

```
python bot.py          # enhance branch
python trading_bot.py  # create branch
```

Live trading requires `API_KEY` and `API_SECRET` env vars (see `.env.example` on each branch).

### Key caveats

- The bot connects to public exchange APIs (Kraken by default) for market data. No API keys are needed for scanning/testing.
- Telegram notifications are gracefully disabled when `TELEGRAM_TOKEN`/`TELEGRAM_CHAT_ID` are not set.
- The bot's scan cycle takes 20-30s per iteration due to fetching OHLCV data for ~600 pairs.
- All state persistence is file-based (CSV/JSON in `data/` directory).
- Feature branches have incompatible `config.py` files; do not mix files across branches.
