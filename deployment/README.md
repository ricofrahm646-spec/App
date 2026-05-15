# Deployment

## Lokaler Start

```bash
docker compose up --build
```

## Komponenten

- Backend (FastAPI)
- Frontend (Next.js)
- PostgreSQL
- Redis

## Autostart Dashboard

Nutze `deployment/scripts/start_jarvis.sh` als Systemstart-Hook (Linux service, crontab `@reboot` oder Desktop autostart).
