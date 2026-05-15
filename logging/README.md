# Logging

Loguru is configured centrally in `backend/app/core/logging_setup.py`.

Default sinks:

* `stdout`        – coloured, structured format
* `logs/jarvis.log` – rotating, 20 MB × 14 days
* `logs/errors.log` – ERROR+ only, 60 days retention

Override the level with the `LOG_LEVEL` env var (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
