# Backtesting

Backtesting support is split into:

- baseline API simulation in `backend.app.services.backtesting_service`
- future VectorBT adapters for vectorized multi-symbol testing
- future Backtrader adapters for event-driven order simulations

Required validation layers:

1. tick-quality data
2. spread and slippage simulation
3. walk-forward analysis
4. Monte Carlo resampling
5. multi-timeframe confirmation
