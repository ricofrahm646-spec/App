# J.A.R.V.I.S. V300 — OMNIPOTENT AUTONOMOUS INTELLIGENCE SYSTEM

A unified AI system integrating trading analysis, computer vision, security scanning, code generation, and voice control.

## Architecture

```
jarvis.py              ← Master Brain: orchestrates all subsystems
├── trader_ultimate.py ← MT5 SMC Trading Engine (Orderblocks, FVG, Liquidity Sweeps)
├── controller.py      ← Vision & OS Controller (Screen capture, chart analysis, automation)
├── ghost_security.py  ← Ghost Engine (Stealth browsing, news scraping, code security audit)
├── coder.py           ← Code Generator (AI + template hybrid, deploys to /apps)
└── ui.py              ← War Room Dashboard (Streamlit, dark theme, live charts)
```

## Quick Start

### Windows
```batch
SYSTEM_IGNITION.bat
```

### Linux / macOS
```bash
chmod +x SYSTEM_IGNITION.sh
./SYSTEM_IGNITION.sh
```

### Manual Setup
```bash
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env   # Edit with your credentials
```

## Launch Modes

| Mode | Command | Description |
|------|---------|-------------|
| Dashboard | `streamlit run ui.py` | War Room with live charts and agent status |
| Interactive | `python jarvis.py` | Text-based command interface |
| Autonomous | `python jarvis.py --auto` | Starts all subsystems automatically |
| Voice | `python jarvis.py --voice` | Speech-to-command with wake word "Jarvis" |
| Trader Only | `python trader_ultimate.py` | Standalone trading engine |

## Subsystems

### Trading Engine (`trader_ultimate.py`)
- **SMC Analysis**: Order Blocks, Fair Value Gaps, Liquidity Sweeps, BOS/CHoCH detection
- **Risk Management**: Position sizing, daily loss limits, spread filtering
- **Trail Stop**: ATR-based trailing stop loss
- **News Protection**: Blackout periods around high-impact news events
- **Confluence Gate**: Only executes trades at 90%+ confluence score
- Connects to MetaTrader 5 or runs in simulation mode

### Vision Controller (`controller.py`)
- Screen capture via MSS (high-performance)
- Chart pattern recognition with OpenCV (trend lines, support/resistance, candle counting)
- Human-like Bezier curve mouse automation for desktop control
- Window management and keyboard automation

### Ghost Engine (`ghost_security.py`)
- Playwright-based stealth browser (anti-detection configured)
- Economic calendar scraping for news event tracking
- Static code security scanner (pattern matching + AST parsing)
- Bandit integration for comprehensive security analysis

### Coder Engine (`coder.py`)
- Template-based generation: CLI tools, web scrapers, data processors, API servers, automation scripts
- AI-powered generation via OpenAI (when API key configured)
- Automatic security scanning of generated code before deployment
- All apps deployed to `/apps` directory

### War Room Dashboard (`ui.py`)
- Deep-black theme with neon-blue accents (Orbitron + JetBrains Mono fonts)
- Live candlestick charts with SMC zone overlays (FVG, Order Blocks)
- Equity curve tracking
- Agent status panel with real-time subsystem monitoring
- System log with color-coded entries

## Configuration

Copy `.env.example` to `.env` and configure:

```env
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=YourBroker-Server
OPENAI_API_KEY=sk-...
TRADE_SYMBOL=EURUSD
```

Advanced parameters can be tuned in `config/settings.py`.

## Voice Commands

When running with `--voice`, say "Jarvis" followed by:
- "start trading" / "stop trading" / "trading status"
- "start vision" / "stop vision"
- "start ghost" / "stop ghost"
- "scan security"
- "create app [description]" / "list apps"
- "system status" / "full start" / "shutdown"

## Risk Warning

**Automated trading carries significant financial risk.** This software is provided for educational and research purposes. Past performance does not guarantee future results. Always test thoroughly with demo accounts before using real funds. Never risk capital you cannot afford to lose.
