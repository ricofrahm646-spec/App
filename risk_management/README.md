# Risk Management Rules

Hard Rules (aktuell in `backend/app/services/risk_engine.py`):

1. Maximal **1 Trade gleichzeitig**
2. Kein gleichzeitiges **Buy und Sell**
3. Emergency Exit bei **>= 20% Verlust**

Erweiterungspunkte:

- Dynamische Lot-Berechnung
- Equity-basierte Risikoanpassung
- Session-/News-Filter
- Multi-Asset Exposure Control
