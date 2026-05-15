# ═══════════════════════════════════════════════════════════════════════════
# JARVIS AI Trading Operating System — Makefile
# ═══════════════════════════════════════════════════════════════════════════

.PHONY: help build up down restart logs status test lint clean \
        migrate migrate-create shell-backend shell-frontend \
        dev dev-backend dev-frontend setup

COMPOSE := docker compose -f deployment/docker-compose.yml --env-file deployment/.env
PROJECT := jarvis

# Default target
help: ## Show this help message
	@echo ""
	@echo "  JARVIS Trading OS — Available Commands"
	@echo "  ═══════════════════════════════════════"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Docker Operations ────────────────────────────────────────────────────

build: ## Build all Docker images
	$(COMPOSE) build

build-no-cache: ## Build all Docker images without cache
	$(COMPOSE) build --no-cache

up: ## Start all services in detached mode
	$(COMPOSE) up -d

up-attached: ## Start all services with logs attached
	$(COMPOSE) up

up-proxy: ## Start all services including nginx reverse proxy
	$(COMPOSE) --profile proxy up -d

down: ## Stop and remove all containers
	$(COMPOSE) down

restart: ## Restart all services
	$(COMPOSE) restart

restart-backend: ## Restart backend service only
	$(COMPOSE) restart backend

restart-frontend: ## Restart frontend service only
	$(COMPOSE) restart frontend

# ── Logging & Monitoring ────────────────────────────────────────────────

logs: ## View logs from all services (follow mode)
	$(COMPOSE) logs -f

logs-backend: ## View backend logs
	$(COMPOSE) logs -f backend

logs-frontend: ## View frontend logs
	$(COMPOSE) logs -f frontend

logs-db: ## View PostgreSQL logs
	$(COMPOSE) logs -f postgres

logs-redis: ## View Redis logs
	$(COMPOSE) logs -f redis

status: ## Show status of all services
	$(COMPOSE) ps

health: ## Check health of all services
	@echo "Backend health:"
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "  Backend not reachable"
	@echo ""
	@echo "Container status:"
	@$(COMPOSE) ps

# ── Testing ──────────────────────────────────────────────────────────────

test: ## Run all tests
	cd backend && python -m pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

test-watch: ## Run tests in watch mode
	cd backend && python -m pytest tests/ -v --tb=short -f

# ── Code Quality ─────────────────────────────────────────────────────────

lint: ## Run linters (ruff + mypy)
	ruff check .
	cd frontend && npm run lint

format: ## Auto-format code
	ruff format .

typecheck: ## Run type checking
	mypy backend/app --ignore-missing-imports

# ── Database ─────────────────────────────────────────────────────────────

migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	cd backend && alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Rollback last migration
	cd backend && alembic downgrade -1

migrate-history: ## Show migration history
	cd backend && alembic history --verbose

db-shell: ## Open PostgreSQL interactive shell
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-jarvis} -d $${POSTGRES_DB:-jarvis}

db-reset: ## Drop and recreate the database (DESTRUCTIVE)
	@echo "WARNING: This will destroy all data. Press Ctrl+C to cancel."
	@sleep 3
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-jarvis} -c "DROP DATABASE IF EXISTS $${POSTGRES_DB:-jarvis};"
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-jarvis} -c "CREATE DATABASE $${POSTGRES_DB:-jarvis};"
	@echo "Database reset complete. Run 'make migrate' to apply migrations."

# ── Shell Access ─────────────────────────────────────────────────────────

shell-backend: ## Open a shell in the backend container
	$(COMPOSE) exec backend bash

shell-frontend: ## Open a shell in the frontend container
	$(COMPOSE) exec frontend sh

shell-redis: ## Open Redis CLI
	$(COMPOSE) exec redis redis-cli

# ── Local Development ───────────────────────────────────────────────────

setup: ## Set up local development environment
	@echo "Setting up JARVIS development environment..."
	cp -n deployment/.env.example deployment/.env 2>/dev/null || true
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
	cd frontend && npm install
	@echo ""
	@echo "Setup complete! Edit deployment/.env with your credentials."
	@echo "Run 'make dev' to start the development environment."

dev: ## Start infrastructure (DB + Redis) for local development
	$(COMPOSE) up -d postgres redis
	@echo ""
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis:      localhost:6379"
	@echo ""
	@echo "Start backend:  cd backend && uvicorn app.main:app --reload"
	@echo "Start frontend: cd frontend && npm run dev"

dev-backend: ## Run backend in development mode (local)
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend in development mode (local)
	cd frontend && npm run dev

# ── Cleanup ──────────────────────────────────────────────────────────────

clean: ## Remove containers, volumes, and build artifacts
	$(COMPOSE) down -v --remove-orphans
	docker image prune -f
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/htmlcov backend/.coverage
	rm -rf frontend/.next frontend/out

clean-all: ## Full cleanup including Docker images
	$(COMPOSE) down -v --rmi all --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

clean-volumes: ## Remove only Docker volumes (DESTRUCTIVE)
	@echo "WARNING: This will destroy all persistent data. Press Ctrl+C to cancel."
	@sleep 3
	$(COMPOSE) down -v

# ── Utility ──────────────────────────────────────────────────────────────

env-check: ## Validate environment configuration
	@echo "Checking deployment/.env..."
	@test -f deployment/.env && echo "  .env file exists" || echo "  ERROR: .env file missing (copy from .env.example)"
	@echo ""
	@echo "Required variables:"
	@for var in SECRET_KEY POSTGRES_PASSWORD DATABASE_URL; do \
		grep -q "^$$var=" deployment/.env 2>/dev/null && echo "  $$var: set" || echo "  $$var: MISSING"; \
	done

version: ## Show version information
	@echo "JARVIS Trading OS v1.0.0"
	@echo "Docker: $$(docker --version 2>/dev/null || echo 'not installed')"
	@echo "Compose: $$(docker compose version 2>/dev/null || echo 'not installed')"
	@echo "Python: $$(python3 --version 2>/dev/null || echo 'not installed')"
	@echo "Node: $$(node --version 2>/dev/null || echo 'not installed')"
