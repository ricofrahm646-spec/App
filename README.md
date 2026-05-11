# JARVIS V300 Omnipotence

Unified local operator console for:

- Streamlit "War Room" dashboard (`ui.py`)
- SMC-inspired MT5 / paper trading engine (`trader_ultimate.py`)
- Screen vision and operator-gated desktop control (`controller.py`)
- Market research and code audit scanner (`ghost_security.py`)
- Voice/text orchestration core (`jarvis.py`)
- Python app factory for `/apps` (`coder.py`)

## Quick start

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m streamlit run ui.py
```

Separate control core:

```bash
python jarvis.py --workspace . --symbol EURUSD --mode paper
```

## Safety notes

- Trading defaults to `paper` mode. `live` mode requires a local, authenticated MetaTrader 5 terminal and explicit operator intent.
- Desktop control is disabled by default. Enable only with `JARVIS_ALLOW_DESKTOP_CONTROL=1`.
- Voice input requires a local Vosk model path in `JARVIS_VOSK_MODEL`.
