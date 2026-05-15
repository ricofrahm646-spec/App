FROM python:3.12-slim

WORKDIR /app

COPY backend/pyproject.toml /app/backend/pyproject.toml
RUN pip install --no-cache-dir hatchling && \
    pip install --no-cache-dir \
      asyncpg fastapi httpx jinja2 orjson pydantic-settings python-multipart redis sqlalchemy "uvicorn[standard]"

COPY backend /app/backend
COPY mql5 /app/mql5
COPY strategies /app/strategies
COPY .env.example /app/.env.example

WORKDIR /app/backend

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
