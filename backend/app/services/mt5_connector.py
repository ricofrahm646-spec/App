from dataclasses import dataclass

from app.core.config import Settings
from app.services.risk_engine import RiskEngine

try:
    import MetaTrader5 as mt5  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency for runtime environments with MT5 installed
    mt5 = None


@dataclass(slots=True)
class Position:
    symbol: str
    direction: str
    volume: float
    profit_fraction: float


class SafeMt5Connector:
    """A thin safety-focused MT5 wrapper for later live integration."""

    def __init__(self, settings: Settings, risk_engine: RiskEngine) -> None:
        self.settings = settings
        self.risk_engine = risk_engine
        self._simulated_positions: list[Position] = []

    def connect(self) -> bool:
        if mt5 is None:
            return False
        return bool(
            mt5.initialize(
                path=self.settings.mt5_path,
                login=int(self.settings.mt5_login) if self.settings.mt5_login else None,
                password=self.settings.mt5_password,
                server=self.settings.mt5_server,
            )
        )

    def get_open_positions(self) -> list[Position]:
        if mt5 is None:
            return list(self._simulated_positions)

        native_positions = mt5.positions_get() or []
        mapped: list[Position] = []
        for position in native_positions:
            direction = "buy" if position.type == mt5.POSITION_TYPE_BUY else "sell"
            mapped.append(
                Position(
                    symbol=position.symbol,
                    direction=direction,
                    volume=float(position.volume),
                    profit_fraction=0.0,
                )
            )
        return mapped

    def open_trade(self, *, symbol: str, direction: str, volume: float) -> dict[str, str | float]:
        active_positions = self.get_open_positions()
        issues = self.risk_engine.validate_trade_window(
            active_positions=len(active_positions),
            requested_direction=direction,
            open_directions={position.direction for position in active_positions},
        )
        if issues:
            raise ValueError("; ".join(issues))

        if mt5 is None:
            simulated = Position(symbol=symbol, direction=direction.lower(), volume=volume, profit_fraction=0.0)
            self._simulated_positions.append(simulated)
            return {"status": "simulated", "symbol": symbol, "direction": direction.lower(), "volume": volume}

        return {"status": "connected", "symbol": symbol, "direction": direction.lower(), "volume": volume}

    def emergency_close_if_needed(self) -> list[str]:
        closed: list[str] = []
        remaining: list[Position] = []
        for position in self.get_open_positions():
            floating_loss_fraction = max(-position.profit_fraction, 0.0)
            if self.risk_engine.should_emergency_close(floating_loss_fraction):
                closed.append(position.symbol)
                continue
            remaining.append(position)
        self._simulated_positions = remaining
        return closed
