# J.A.R.V.I.S. V300 War Room

Integrated operator stack for:

- Streamlit "War Room" dashboard
- SMC-inspired MT5 trading engine with paper mode and live-gated execution
- Desktop vision and humanized cursor control
- Browser research plus static security auditing
- Python app generation into `/apps`
- Voice-capable JARVIS control core

## Start

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python jarvis.py --command "status"
streamlit run ui.py
```

## Main Files

- `ui.py` - War Room dashboard
- `trader_ultimate.py` - market analysis and trade execution engine
- `controller.py` - screen analysis and desktop automation helpers
- `ghost_security.py` - browser research and security audit tools
- `coder.py` - app generator for `/apps`
- `jarvis.py` - orchestration layer and command interface

## Notes

- Live trade execution is intentionally gated behind `JARVIS_ENABLE_LIVE_TRADING=1`.
- Voice mode requires local audio devices and optional dependencies from `requirements.txt`.
- Generated runtime artifacts are written into `runtime/`.
