from dataclasses import dataclass


@dataclass(slots=True)
class RiskPolicy:
    risk_per_trade_percent: float = 0.5
    max_live_trades: int = 1
    allow_hedging: bool = False
    force_close_loss_percent: float = 20.0
    trailing_stop_enabled: bool = True
    emergency_stop_enabled: bool = False


DEFAULT_POLICY = RiskPolicy()
