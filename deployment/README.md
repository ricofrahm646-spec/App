# JARVIS Deployment

## Local Docker stack

1. Copy `.env.example` to `.env`.
2. Set a real `ENCRYPTION_KEY`, Telegram token, TradingView secret and MT5 paths.
3. Start the stack:

```bash
docker compose up --build
```

Services:

- Backend: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>
- Frontend: <http://localhost:3000>
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## MT5 notes

MetaTrader 5 automation is environment-specific. The backend can generate and install `.mq5`
files into the configured data path. Compilation requires `MetaEditor.exe` or a compatible
compiler path on the host where MT5 is installed.

Live trading is disabled by default and requires `LIVE_TRADING_ENABLED=true`.
