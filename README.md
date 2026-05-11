# J.A.R.V.I.S. V300 — OMNIPOTENCE PROTOCOL

An integrated AI trading and automation system combining Smart Money Concepts (SMC) based M1 scalping, real-time chart analysis, news intelligence, automated code generation, and a War Room command dashboard.

> **RISK DISCLAIMER:** Automated trading carries substantial risk of financial loss. Past performance does not guarantee future results. Only trade with money you can afford to lose. This software is provided AS-IS with NO guarantees of profit.

## Architecture

```
jarvis.py                 # Master orchestrator
core/
  trader_ultimate.py      # SMC trading engine (MT5)
  ui.py                   # War Room Streamlit dashboard
  controller.py           # Chart pattern analysis (OpenCV)
  ghost_security.py       # News scraping & code audit
  coder.py                # Code generation engine
  voice.py                # Speech-to-command / TTS
config/
  settings.py             # Central configuration
apps/                     # Generated applications
logs/                     # System logs
data/                     # Shared state & data
```

## Core Modules

### Trading Ultima (`trader_ultimate.py`)
- **SMC Analysis:** Order Blocks, Fair Value Gaps (FVG), Liquidity Sweeps
- **Confluence Engine:** Multi-factor scoring (90%+ threshold for trade entry)
- **Risk Management:** Per-trade risk limits, daily loss caps, position sizing
- **Trail Stop:** Dynamic ATR-based trailing stop loss
- **News Protection:** Blocks trading around high-impact economic events
- **MT5 Integration:** Full MetaTrader 5 API for order execution (Windows) with simulation fallback

### War Room Dashboard (`ui.py`)
- Deep-black + neon-blue "War Room" aesthetic
- Live candlestick charts with buy/sell signal markers
- Equity curve with return/drawdown metrics
- Confluence gauge and signal breakdown
- Agent status monitoring and system logs
- Auto-refresh every 2 seconds

### Chart Vision (`controller.py`)
- Candlestick pattern detection (Doji, Hammer, Engulfing, Pin Bars)
- Support/resistance level identification
- Trend analysis via linear regression
- Optional screen capture + OpenCV image analysis for visual chart patterns

### News & Security (`ghost_security.py`)
- Economic calendar scraping (ForexFactory, Investing.com)
- High-impact event detection with configurable buffer
- Python AST-based static code auditor
- Detects dangerous calls (eval, exec, pickle.loads, etc.)
- Pattern-based checks for hardcoded secrets, insecure configs

### Code Generator (`coder.py`)
- Template-based app generation (Flask API, CLI tools, Streamlit apps, scrapers, data processors)
- Automatic syntax validation and import checking
- Code quality analysis
- Generated apps stored in `/apps` directory

### Voice Engine (`voice.py`)
- Offline TTS via pyttsx3
- Speech recognition via Google Speech API
- Wake word detection ("Jarvis", "Hey Jarvis")
- Voice commands: status, start/stop trading, scan, audit, report, shutdown

## Quick Start

### Windows
```cmd
SYSTEM_IGNITION.bat
```

### Linux / macOS
```bash
./SYSTEM_IGNITION.sh
```

### Manual Setup
```bash
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# or: venv\Scripts\activate  # Windows

pip install -r requirements.txt
python -m playwright install chromium  # optional

# Full system
python jarvis.py

# Dashboard only
streamlit run core/ui.py --server.port 8501 --theme.base dark

# No voice
python jarvis.py --no-voice
```

## Configuration

All settings are in `config/settings.py`. Key options:

| Setting | Default | Description |
|---|---|---|
| `MT5_LOGIN` | env var | MetaTrader 5 account number |
| `MT5_PASSWORD` | env var | MT5 password |
| `MT5_SERVER` | MetaQuotes-Demo | MT5 broker server |
| `risk_per_trade_pct` | 1.0% | Risk per trade as % of balance |
| `max_daily_loss_pct` | 5.0% | Maximum daily drawdown |
| `min_confluence_score` | 0.90 | Minimum signal quality (0-1) |
| `news_protection_minutes` | 15 | Buffer around high-impact news |

Set MT5 credentials via environment variables:
```bash
export MT5_LOGIN=12345678
export MT5_PASSWORD=your_password
export MT5_SERVER=YourBroker-Server
```

## Platform Notes

- **MetaTrader 5** Python API only works on Windows with MT5 terminal installed. On Linux/macOS the system runs in simulation mode.
- **Voice** requires a microphone and audio output device. Falls back gracefully if unavailable.
- **Screen capture** (mss/OpenCV) requires a display. Headless servers use data-only analysis.
