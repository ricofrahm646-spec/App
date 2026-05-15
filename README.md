# JARVIS - Full AI Trading Operating System

JARVIS ist eine modulare Trading-Plattform fuer:

- KI-gestuetzte Strategie-Generierung und Optimierung
- Backtesting und Risiko-Management
- MT5/MQL5 Automatisierung
- TradingView- und Telegram-Integration
- Live-Dashboard und internes Chat-Interface

> Hinweis: Dieses Repository liefert eine produktionsnahe Grundarchitektur mit klaren Erweiterungspunkten. Es gibt **keine** unrealistischen Gewinnversprechen.

## Projektstruktur

```text
/backend            FastAPI API + Trading Core
/frontend           Next.js Dashboard + Chat UI
/ai                 AI Orchestrierung + Optimierungs-Interfaces
/mt5                MT5 Integrationsdokumentation
/mql5               MQL5 Templates und Build-Ordner
/backtesting        Backtesting-Module
/strategies         Strategiedefinitionen
/tradingview        Pine Script + Webhook-Flows
/telegram           Telegram Bot/Signal Integration
/database           SQL Migrationen/Initialisierung
/deployment         Docker und Betriebs-Skripte
/logging            Logging-Strategie
/risk_management    Risiko-Richtlinien und Regeln
```

## Schnellstart

1. Umgebung vorbereiten:

```bash
cp .env.example .env
```

2. Services starten:

```bash
docker compose up --build
```

3. Wichtige Endpunkte:

- API Docs: `http://localhost:8000/docs`
- Frontend Dashboard: `http://localhost:3000`

## Sicherheits- und Risiko-Prinzipien

- Maximal ein Trade gleichzeitig
- Kein gleichzeitiges Buy/Sell
- Emergency-Exit bei 20% Positionsverlust
- Strukturierte Logs, Exceptions, Auto-Reconnect-Hooks
- Secrets werden ueber Environment-Variablen verwaltet

## Technologie-Stack

- Backend: Python, FastAPI
- Frontend: Next.js, React, TypeScript, Tailwind CSS
- Daten: PostgreSQL, Redis
- Deployment: Docker Compose
- AI/Optimierung: vorbereitete Integrationspunkte fuer PyTorch, TensorFlow, Optuna, XGBoost, RL
