"""Backtesting engine for strategy simulation."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from trading.risk_manager import RiskManager
from trading.strategies import StrategySignal, TradingStrategy


@dataclass(slots=True)
class BacktestResult:
    """Output of a strategy backtest."""

    strategy_name: str
    total_trades: int
    winrate: float
    profit_factor: float
    max_drawdown: float
    net_profit: float
    equity_curve: list[float]
    trade_log: list[dict[str, Any]]
    ranking_score: float


class Backtester:
    """Runs strategy signals over synthetic or historical prices."""

    def __init__(self, risk_manager: RiskManager | None = None, initial_equity: float = 10000.0) -> None:
        self.risk_manager = risk_manager or RiskManager()
        self.initial_equity = initial_equity

    def run(self, prices: list[float], strategy: TradingStrategy) -> BacktestResult:
        if len(prices) < 3:
            raise ValueError("Need at least 3 prices for backtesting.")

        signals = strategy.generate_signals(prices)
        signal_map = {signal.index: signal for signal in signals}
        equity = self.initial_equity
        peak = equity
        max_drawdown = 0.0
        trade_log: list[dict[str, Any]] = []
        equity_curve = [equity]
        gross_profit = 0.0
        gross_loss = 0.0
        wins = 0
        losses = 0
        consecutive_losses = 0

        for i in range(1, len(prices) - 1):
            signal: StrategySignal | None = signal_map.get(i)
            if signal is None:
                equity_curve.append(equity)
                continue

            entry = prices[i]
            next_price = prices[i + 1]
            stop = entry * (0.99 if signal.action == "buy" else 1.01)

            assessment = self.risk_manager.assess_trade(
                equity=equity,
                entry_price=entry,
                stop_price=stop,
                current_drawdown=max_drawdown,
                consecutive_losses=consecutive_losses,
            )
            if not assessment.allowed:
                trade_log.append(
                    {
                        "index": i,
                        "action": signal.action,
                        "status": "blocked",
                        "reason": assessment.reason,
                    }
                )
                equity_curve.append(equity)
                continue

            move = (next_price - entry) / entry
            pnl_ratio = move if signal.action == "buy" else -move
            pnl = assessment.position_size * entry * pnl_ratio
            equity += pnl
            peak = max(peak, equity)
            drawdown = 0.0 if peak == 0 else (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
            equity_curve.append(equity)

            if pnl >= 0:
                wins += 1
                consecutive_losses = 0
                gross_profit += pnl
                status = "win"
            else:
                losses += 1
                consecutive_losses += 1
                gross_loss += abs(pnl)
                status = "loss"

            trade_log.append(
                {
                    "index": i,
                    "action": signal.action,
                    "entry": round(entry, 6),
                    "exit": round(next_price, 6),
                    "pnl": round(pnl, 4),
                    "status": status,
                    "confidence": signal.confidence,
                    "reason": signal.reason,
                }
            )

        total_trades = wins + losses
        winrate = (wins / total_trades) if total_trades else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
        if not isfinite(profit_factor):
            profit_factor = 0.0
        net_profit = equity - self.initial_equity
        ranking_score = (winrate * 0.45) + (min(profit_factor, 4.0) / 4.0 * 0.35) + ((1 - max_drawdown) * 0.20)

        return BacktestResult(
            strategy_name=strategy.name,
            total_trades=total_trades,
            winrate=round(winrate, 4),
            profit_factor=round(profit_factor, 4),
            max_drawdown=round(max_drawdown, 4),
            net_profit=round(net_profit, 4),
            equity_curve=[round(point, 4) for point in equity_curve],
            trade_log=trade_log,
            ranking_score=round(ranking_score, 4),
        )

