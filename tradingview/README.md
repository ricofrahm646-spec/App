# TradingView Integration

TradingView integration is designed around webhook alerts and Pine Script strategies that call into the JARVIS backend.

Current foundation:

- Forex-pair validation before webhook acceptance
- Payload builder for Buy/Sell alerts with SL and TP
- Shared-secret placeholder for webhook verification

Next steps:

- Add webhook endpoint to the backend
- Generate Pine Script templates per strategy
- Persist alert history for dashboard review
