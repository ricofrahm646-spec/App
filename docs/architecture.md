# JARVIS Architecture

## Design Principles

- modular services with explicit boundaries
- safe-by-default trading guardrails
- automation-friendly file generation
- typed contracts between UI, API and execution services
- truthful reporting without fake performance metrics

## Core Runtime Flow

1. The operator issues a command in the dashboard chat UI.
2. The backend chat orchestrator classifies the intent and generates a build plan.
3. Strategy, file generation, risk and MT5 services collaborate to produce artifacts.
4. Resulting Python, MQL5, Pine Script or configuration files are stored by module.
5. Execution and monitoring events are streamed to the dashboard and notifications.

## Major Subsystems

### Backend API

- FastAPI application with REST and WebSocket entrypoints
- system overview endpoint for dashboard hydration
- chat command endpoint for operator-driven automation
- risk engine enforcing one-trade and max-loss rules

### Frontend Dashboard

- Next.js App Router with Tailwind styling
- command console for natural-language requests
- status cards for equity, drawdown, win rate and live state
- operator panels for strategies, alerts and integration status

### AI Layer

- strategy ideation prompt plans
- optimizer service contracts for Optuna, RL and ensemble experiments
- overfitting safeguards and evaluation metadata

### MT5 and MQL5

- MT5 installation planner for copying generated files to terminal folders
- MQL5 template generator for expert advisors and indicators
- execution policies that can later connect to a terminal bridge service

### Data and Infra

- PostgreSQL for runs, trades, strategies and generated artifacts
- Redis for queues, locks and streaming state
- Docker Compose stack for local bring-up

## Safety Controls

- hard guard against simultaneous long and short exposure
- single live trade limit
- forced close threshold when loss ratio reaches 20 percent
- emergency stop flag for strategy disablement
- centralized structured logging hooks
