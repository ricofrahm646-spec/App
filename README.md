# J.A.R.V.I.S. V300 Omni System

This repository contains a Streamlit "War Room" dashboard and Python modules for:

- MT5-compatible SMC trading analysis with dry-run execution by default
- Screen/chart computer vision and opt-in desktop automation
- Responsible Playwright-based market research
- Static security auditing for generated Python apps
- Deterministic app generation into `apps/`
- Local voice command and speech output integration

## Start

On Windows:

```bat
SYSTEM_IGNITION.bat
```

On any Python environment:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
streamlit run ui.py
```

Live trading and OS control are disabled unless explicitly enabled with
environment variables (`JARVIS_LIVE_TRADING=1`, `JARVIS_OS_CONTROL=1`).
