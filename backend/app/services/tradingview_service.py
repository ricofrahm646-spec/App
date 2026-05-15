from dataclasses import dataclass


@dataclass
class TradingViewSignal:
    symbol: str
    side: str
    stop_loss: float
    take_profit: float
    source: str = "tradingview-webhook"


class TradingViewService:
    """Processes validated TradingView webhook payloads."""

    def parse_webhook(self, payload: dict[str, str | float]) -> TradingViewSignal:
        return TradingViewSignal(
            symbol=str(payload["symbol"]),
            side=str(payload["side"]).lower(),
            stop_loss=float(payload["stop_loss"]),
            take_profit=float(payload["take_profit"]),
        )
