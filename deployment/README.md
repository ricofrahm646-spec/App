# Deployment

Run the complete local stack:

```bash
cp .env.example .env
docker compose up --build
```

To open the dashboard on desktop login, copy `jarvis-dashboard.desktop` to the
local autostart directory after Docker services are configured:

```bash
mkdir -p ~/.config/autostart
cp deployment/jarvis-dashboard.desktop ~/.config/autostart/
```

MetaTrader 5 automation requires a local terminal path and data directory in
`.env`. The cloud container can generate and copy files, while compilation and
chart attachment require terminal access on the host machine.
