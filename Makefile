.PHONY: help install backend frontend test lint format up down logs psql shell

help:
	@echo "JARVIS — make targets"
	@echo "  install    Install backend + frontend dependencies"
	@echo "  backend    Run backend (uvicorn, reload)"
	@echo "  frontend   Run frontend (next dev)"
	@echo "  test       Run pytest"
	@echo "  lint       Ruff + black --check"
	@echo "  format     Ruff --fix + black"
	@echo "  up         docker compose up --build"
	@echo "  down       docker compose down -v"
	@echo "  logs       Tail compose logs"

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

backend:
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

test:
	pytest

lint:
	ruff check .
	black --check .

format:
	ruff check --fix .
	black .

up:
	docker compose -f deployment/docker-compose.yml up --build

down:
	docker compose -f deployment/docker-compose.yml down -v

logs:
	docker compose -f deployment/docker-compose.yml logs -f --tail=200

psql:
	docker compose -f deployment/docker-compose.yml exec postgres psql -U jarvis jarvis

shell:
	docker compose -f deployment/docker-compose.yml exec backend bash
