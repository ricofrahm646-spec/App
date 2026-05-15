# MT5 Connector Layer

Geplanter Verantwortungsbereich:

- Verbindung zum MetaTrader 5 Terminal
- Symbol-/Chart-Erkennung (offene Charts, aktive Timeframes)
- Order-Execution (Buy/Sell, SL/TP, Close)
- Trailing Stop und Trade-Management
- Compiler-Hook fuer `.mq5 -> .ex5`

Die konkrete Runtime-Anbindung erfolgt ueber den Backend-Service `app/services/mt5_connector.py`.
