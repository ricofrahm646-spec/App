from __future__ import annotations

from backend.app.schemas import TradingViewWebhook


FOREX_SUFFIXES = ("USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD")


class TradingViewWebhookHandler:
    """Validates TradingView alerts before they reach the execution layer."""

    def __init__(self, secret: str) -> None:
        self.secret = secret

    def validate(self, payload: TradingViewWebhook) -> tuple[bool, str]:
        if payload.secret != self.secret:
            return False, "Invalid TradingView webhook secret."
        if not self._is_forex_symbol(payload.symbol):
            return False, "TradingView integration is restricted to Forex symbols."
        return True, "TradingView alert accepted."

    @staticmethod
    def _is_forex_symbol(symbol: str) -> bool:
        normalized = symbol.replace("/", "").replace(":", "").upper()
        if len(normalized) < 6:
            return False
        base = normalized[-6:-3]
        quote = normalized[-3:]
        return base in FOREX_SUFFIXES and quote in FOREX_SUFFIXES and base != quote
