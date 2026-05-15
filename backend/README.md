# Backend (FastAPI)

## Kernmodule

- `api/routes/chat.py`: KI-Chat Interface
- `api/routes/trading.py`: Trade Open/Close + Positions
- `api/routes/risk.py`: Risiko-Snapshot + Emergency Close
- `api/routes/mql5.py`: MQL5 Generierung/Compile/Installation
- `api/routes/backtesting.py`: Backtesting Start
- `api/routes/telegram.py`: Telegram Notifications
- `api/routes/tradingview.py`: TradingView Webhooks
- `api/routes/files.py`: Generischer Datei-Generator

## Start lokal

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
