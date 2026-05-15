# JARVIS — AI-assisted trading control plane

JARVIS is a modular **control and research stack** (FastAPI + Next.js) for MetaTrader 5 workflows, alerting, and guarded execution policies. It is **not** a guaranteed profit system: metrics and model outputs must be validated on your own data.

## Layout

- `backend/` — FastAPI control plane, risk engine, chat orchestrator, MT5/Telegram/TradingView hooks, WebSocket metrics fan-out.
- `frontend/` — Next.js dashboard and internal chat UI (Tailwind).
- `ai/` — Optional research entrypoints (heavy deps isolated in `backend/requirements-ai.txt`).
- `backtesting/` — Local research helpers; HTTP API under `/api/v1/backtest`.
- `strategies/` — Python strategy stubs and registry.
- `mql5/` — Templates and generated `.mq5` output (`mql5/generated/`).
- `mt5/` — Host bridge notes (MT5 is Windows-oriented).
- `telegram/` — Sample payloads.
- `tradingview/` — Pine script samples for Forex webhooks.
- `database/` — PostgreSQL init script.
- `deployment/` — Docker Compose, autostart helper desktop entry.
- `risk_management/` — JSON policy mirror of runtime defaults.
- `logging/` — Reserved for centralized logging agents.

## Quick start (Docker)

```bash
docker compose -f deployment/docker-compose.yml up --build
```

- API: `http://localhost:8000/docs`
- UI: `http://localhost:3000`
- WebSocket: `ws://localhost:8000/ws/v1/stream`

## MetaTrader 5

Install `backend/requirements-mt5.txt` on the **Windows workstation** that runs MT5. Containers on Linux will not host the terminal runtime; use the host bridge described in `mt5/host_bridge.txt`.

## Environment

See `.env.example`. Set `TRADINGVIEW_WEBHOOK_SECRET` and send the same value as the `X-TV-SECRET` header from TradingView alert webhooks.

## Autostart (Linux desktop)

Copy `deployment/autostart/jarvis-dashboard.desktop` into `~/.config/autostart/` and adjust the URL if needed.

## Safety

- Risk engine defaults: max **one** concurrent position, block opposite-side hedges on the same symbol, emergency evaluation when floating loss vs. equity crosses **20%** (configurable in code and `risk_management/default_policy.json`).
- Never expose trading APIs or webhook secrets publicly without TLS and authentication hardening.
