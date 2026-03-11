"""
Telegram notifier for the Hardcore Growth Mode trading bot.

Sends alerts for top-scored coins (entry, TP, SL, score) and status messages.
"""

import logging

import config

try:
    import requests as _requests

    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


class TelegramNotifier:
    """Sends messages via the Telegram Bot API using simple HTTP requests."""

    def __init__(self) -> None:
        self._token = config.TELEGRAM_TOKEN
        self._chat_id = config.TELEGRAM_CHAT_ID
        self._enabled = bool(self._token and self._chat_id)
        if not self._enabled:
            logging.info(
                "Telegram notifications disabled (TELEGRAM_TOKEN / TELEGRAM_CHAT_ID not set)."
            )

    def send(self, text: str) -> None:
        """Send a plain-text message."""
        if not self._enabled:
            return
        self._post(text)

    def send_signal(self, signal_dict: dict) -> None:
        """Send a formatted trade-signal alert."""
        if not self._enabled:
            return
        symbol = signal_dict.get("symbol", "?")
        score = signal_dict.get("score", 0)
        entry = signal_dict.get("entry_price", 0)
        tp = signal_dict.get("take_profit", 0)
        sl = signal_dict.get("stop_loss", 0)
        rsi = signal_dict.get("rsi", 0)
        macd = signal_dict.get("macd_diff", 0)
        vol = signal_dict.get("volume_spike_ratio", 0)
        pc = signal_dict.get("price_change_5m", 0)

        text = (
            f"🚀 *Trade Signal* | Score: {score}/100\n"
            f"Coin:   `{symbol}`\n"
            f"Entry:  `{entry:.8f} EUR`\n"
            f"TP:     `{tp:.8f} EUR`  (+{config.TAKE_PROFIT_PERCENT*100:.1f}%)\n"
            f"SL:     `{sl:.8f} EUR`  (-{config.STOP_LOSS_PERCENT*100:.1f}%)\n"
            f"RSI:    `{rsi:.1f}` | MACD: `{macd:.8f}`\n"
            f"Vol×:   `{vol:.2f}` | Δ5m: `{pc:+.2f}%`"
        )
        self._post(text, parse_mode="Markdown")

    def send_close(self, record: dict) -> None:
        """Send a trade-closed alert."""
        if not self._enabled:
            return
        symbol = record.get("symbol", "?")
        reason = record.get("reason", "?")
        pnl = record.get("pnl_eur", 0)
        pnl_pct = record.get("pnl_pct", 0)
        emoji = "✅" if pnl >= 0 else "❌"
        text = (
            f"{emoji} *Trade Closed* ({reason})\n"
            f"Coin:  `{symbol}`\n"
            f"PnL:   `{pnl:+.4f} EUR` (`{pnl_pct:+.2f}%`)"
        )
        self._post(text, parse_mode="Markdown")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _post(self, text: str, parse_mode: str = "") -> None:
        if not _HAS_REQUESTS:
            logging.warning("'requests' library not available – cannot send Telegram message.")
            return
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload: dict = {"chat_id": self._chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            resp = _requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logging.warning("Telegram notification failed: %s", exc)
