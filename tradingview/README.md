# TradingView Integration

JARVIS supports Forex-only TradingView webhook payloads:

```json
{"symbol": "EURUSD", "side": "buy", "price": 1.0812}
```

Generated Pine Script files are saved into this directory and can be pasted
into TradingView alerts. The backend validates symbols before converting
signals into risk-gated trade requests.
