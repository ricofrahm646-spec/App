# MT5 Automation

The backend exposes MT5 command plans for cloud environments and can execute
them when a local MetaTrader 5 terminal is configured.

Configure:

- `MT5_DATA_PATH` - usually the terminal's `MQL5` data directory
- `MT5_TERMINAL_PATH` - path to `terminal64.exe` for compilation automation

Generated `.mq5` files are copied into `Experts` or `Indicators`. Compilation
requires a local terminal with the correct Wine/Windows environment.
