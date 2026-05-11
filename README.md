# J.A.R.V.I.S. V300 Omni System

This repository contains a Streamlit "War Room" dashboard and Python modules for:

- Universal project generation from natural-language commands
- PDF/image processing for strategy and sketch ingestion
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
streamlit run ui/main_shell.py
```

The legacy War Room remains available with:

```bash
streamlit run ui/war_room.py
```

## Universal Creator

Use the adaptive shell or CLI command router:

```bash
python jarvis.py --command "Jarvis, baue mir eine Trading-App fuer meine Strategie"
python jarvis.py --command "scalper scan"
python jarvis.py --command "audit"
```

Generated full project structures are written to `generated_projects/`.

Live trading, OS control, terminal execution, and dependency installation are
disabled unless explicitly enabled with environment variables:

- `JARVIS_LIVE_TRADING=1`
- `JARVIS_OS_CONTROL=1`
- `JARVIS_TERMINAL_CONTROL=1`
- `JARVIS_ALLOW_PIP_INSTALL=1`
