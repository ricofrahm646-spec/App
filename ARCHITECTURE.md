# JARVIS Architekturuebersicht

## 1) Control Plane (Chat-Driven)

1. Nutzer sendet Prompt an `/api/chat/message`
2. `ChatOrchestrator` mappt Intents auf Aktionen
3. Aktionen triggern Module:
   - Strategie-Registry
   - AI-Optimierer
   - MQL5 Generator
   - Risiko-Engine
   - Integrationen (Telegram/TradingView)

## 2) Trading Plane

- TradingView/Signal Inputs -> Backend Validierung
- Risiko-Engine erzwingt Hard Rules
- MT5 Connector fuehrt Trades aus
- Trade Events werden persistiert (Postgres) und gestreamt (Redis/WebSocket geplant)

## 3) Strategy/AI Plane

- Strategien im `strategies/` Verzeichnis
- Backtesting Pipeline (VectorBT/Backtrader Integrationspunkt)
- AI Orchestrator fuer RL/Optuna/ML

## 4) MQL5 Automation Plane

- `.mq5` Erzeugung via API
- `.ex5` Compile Hook (Stub)
- Installer kopiert Dateien in MT5-Datenpfad

## 5) Security & Operations

- Secrets via `.env`
- Strukturiertes Logging
- Exception Handling in API
- Emergency Stop Regelung in Risk Engine
