FROM python:3.11-slim

WORKDIR /app

COPY backend /app/backend
COPY mt5 /app/mt5
COPY mql5 /app/mql5
COPY strategies /app/strategies
COPY risk_management /app/risk_management

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir /app/backend

WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
