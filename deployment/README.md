# Deployment

## Docker Compose (recommended)

```bash
cp .env.example .env
docker compose -f deployment/docker-compose.yml up --build
```

Services:

| Service   | Port  | Purpose                              |
|-----------|-------|--------------------------------------|
| postgres  | 5432  | Persistent store                     |
| redis     | 6379  | Cache / pub-sub                      |
| backend   | 8000  | FastAPI: REST + WebSocket            |
| frontend  | 3000  | Next.js dashboard + AI chat          |

## Autostart on PC login

* **Linux**: copy `deployment/autostart/jarvis.desktop` to
  `~/.config/autostart/` to open the dashboard at login.
* **Windows**: place a shortcut to `deployment/autostart/jarvis.bat` into
  `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.

## systemd

`deployment/systemd/jarvis-backend.service` is a minimal unit file for running
the backend under systemd on a production box.

## Production checklist

- Replace `SECRET_KEY` and `ENCRYPTION_KEY` with strong random values.
- Configure a real LLM key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`).
- Configure MT5 credentials and set `MT5_MOCK=false`.
- Configure Telegram credentials.
- Put the backend behind nginx + TLS (sample config can be added later).
- Configure firewalled Postgres / Redis (not exposed publicly).
