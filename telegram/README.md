# Telegram Integration

The backend sends Telegram notifications for:

- buy/sell signals
- opened trades
- closed trades
- profit/loss summaries
- risk warnings
- emergency stop events

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`. Store production
tokens through the encrypted settings flow exposed by the backend.
