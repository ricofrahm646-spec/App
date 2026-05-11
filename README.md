# J.A.R.V.I.S. V300 - OMNIPOTENCE

Full-stack autonomous assistant fusing trading, computer vision, OS control,
stealth research, code generation and voice into one orchestrated system.

```
                    +-----------------------+
                    |       jarvis.py       |  <- master brain + voice
                    +-----------+-----------+
                                |
        +-----------+-----------+-----------+-----------+
        |           |           |           |           |
   trader_ultimate  controller  ghost_       coder       ui.py
   (MT5 SMC scalp)  (vision/OS) security     (forge)     (Streamlit)
                                (research +
                                 audit)
                                |
                          core/bus.py  <-- shared event/log bus
```

## Files

| File                  | Purpose                                                        |
|-----------------------|----------------------------------------------------------------|
| `jarvis.py`           | Master brain, subsystem orchestrator, voice I/O                |
| `trader_ultimate.py`  | MetaTrader 5 M1 SMC scalper (OB / FVG / sweeps / BOS / CHoCH)  |
| `ui.py`               | "War Room" Streamlit dashboard (neon-blue on deep black)       |
| `controller.py`       | MSS + OpenCV vision and PyAutoGUI Bezier mouse control         |
| `ghost_security.py`   | Stealth Playwright news scraper + AST code auditor             |
| `coder.py`            | Template-based generator that builds new apps into `apps/`     |
| `core/smc.py`         | Smart-Money-Concepts engine (pure numpy/pandas)                |
| `core/bus.py`         | Shared event log, signals.csv, equity.csv, trades.log          |
| `config/settings.py`  | All tunables                                                   |
| `SYSTEM_IGNITION.bat` | One-click Windows bootstrap + launch                           |

## Quick start (Windows)

```bat
SYSTEM_IGNITION.bat
```

This creates a venv, installs `requirements.txt`, downloads Playwright's
Chromium, launches the dashboard in a new window and starts the master brain.

## Quick start (any OS, dev mode)

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

streamlit run ui.py            # dashboard
python jarvis.py --silent      # brain (no microphone)
python trader_ultimate.py --dry # SMC dry-run on synthetic data
python ghost_security.py --audit
python coder.py "fastapi service that scores trades"
```

## Trading plan

* Symbols: `EURUSD`, `XAUUSD`, `GBPUSD` (configurable).
* Timeframe: **M1** (HTF M15 bias filter).
* Confluence gate: **>= 90%** (HTF bias + LTF BOS/CHoCH + sweep + OB + FVG +
  premium/discount + sane ATR).
* Risk: 5% per trade, 1:2 RR, ATR-distance stops, trail begins at +1R.
* News protection: trades blocked +/- 15 min around HIGH-impact events that
  match the symbol's currency.
* Campaign: 10 EUR -> 100 EUR with daily 20% DD circuit breaker.

> Aggressive size targets carry real capital risk. Run in a demo account
> first and validate the SMC analyser on your broker's data feed.

## Voice commands (German + English mix)

| Spoken                              | Action                                  |
|-------------------------------------|------------------------------------------|
| "jarvis start trader"               | arm trading loop                         |
| "jarvis vision an"                  | start screen vision                      |
| "jarvis stealth aim"                | vision + stealth-aim follow              |
| "jarvis ghost an"                   | start news + audit watcher               |
| "jarvis baue fastapi predictor"     | generate new app via code-forge          |
| "jarvis status"                     | speak active subsystems                  |
| "jarvis stop"                       | graceful shutdown                        |

J.A.R.V.I.S. addresses the operator as **Sir** (override with
`JARVIS_OWNER_TITLE` environment variable).
