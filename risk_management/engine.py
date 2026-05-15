"""
JARVIS Risk Management Engine
Centralized risk control: position sizing, drawdown limits, trade validation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from loguru import logger


@dataclass
class RiskSettings:
    """Configurable risk parameters."""
    risk_per_trade_pct: float = 2.0          # % of balance per trade
    max_daily_loss_pct: float = 5.0          # % max daily loss
    max_total_drawdown_pct: float = 20.0     # % max total drawdown (hard stop)
    max_concurrent_trades: int = 1           # max open trades at once
    min_risk_reward: float = 1.5             # minimum R:R ratio
    max_spread_pips: float = 3.0             # max allowed spread
    use_dynamic_sizing: bool = True          # adjust size based on recent performance


@dataclass
class RiskReport:
    """Result of trade validation."""
    allowed: bool
    reason: str
    suggested_lot: float = 0.0
    risk_reward: float = 0.0
    warnings: List[str] = field(default_factory=list)


class RiskEngine:
    """
    Production risk management engine.
    Enforces position limits, drawdown controls, and position sizing.
    """

    PIP_SIZES: Dict[str, float] = {
        "EURUSD": 0.0001, "GBPUSD": 0.0001, "AUDUSD": 0.0001,
        "USDCAD": 0.0001, "USDCHF": 0.0001, "NZDUSD": 0.0001,
        "USDJPY": 0.01,   "EURJPY": 0.01,   "GBPJPY": 0.01,
        "XAUUSD": 0.1,    "XAGUSD": 0.001,  "US30": 1.0,
        "NAS100": 1.0,    "SPX500": 0.1,
    }

    def __init__(self, settings: Optional[RiskSettings] = None) -> None:
        self.settings = settings or RiskSettings()
        self._daily_start_balance: Optional[float] = None

    def pip_size(self, symbol: str) -> float:
        """Return pip size for a symbol."""
        return self.PIP_SIZES.get(symbol.upper(), 0.0001)

    def pips_to_price(self, symbol: str, pips: float) -> float:
        return pips * self.pip_size(symbol)

    def price_to_pips(self, symbol: str, price_distance: float) -> float:
        ps = self.pip_size(symbol)
        return price_distance / ps if ps > 0 else 0.0

    def calculate_lot_size(
        self,
        symbol: str,
        account_balance: float,
        sl_price_distance: float,
        pip_value_per_lot: float = 10.0,
        risk_override_pct: Optional[float] = None,
    ) -> float:
        """
        Calculate position size based on risk %.

        lot = (balance * risk%) / (sl_pips * pip_value_per_lot)
        """
        risk_pct = risk_override_pct or self.settings.risk_per_trade_pct
        risk_amount = account_balance * (risk_pct / 100.0)
        sl_pips = self.price_to_pips(symbol, sl_price_distance)

        if sl_pips <= 0:
            logger.warning("Invalid SL distance (%.5f) for %s", sl_price_distance, symbol)
            return 0.01

        lot = risk_amount / (sl_pips * pip_value_per_lot)
        lot = max(0.01, round(lot, 2))
        lot = min(lot, 10.0)  # hard cap at 10 lots
        return lot

    def calculate_risk_reward(
        self,
        entry: float,
        sl: float,
        tp: float,
        direction: str,
    ) -> float:
        """Calculate risk:reward ratio."""
        if direction.upper() == "BUY":
            sl_dist = entry - sl
            tp_dist = tp - entry
        else:
            sl_dist = sl - entry
            tp_dist = entry - tp

        if sl_dist <= 0:
            return 0.0
        return tp_dist / sl_dist

    def validate_trade(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        account_balance: float,
        account_equity: float,
        open_trades: List[Dict],
        daily_start_balance: Optional[float] = None,
        current_spread_pips: float = 0.0,
    ) -> RiskReport:
        """
        Full trade validation.
        Returns RiskReport with allowed=True/False and reason.
        """
        warnings: List[str] = []

        # 1. Max concurrent trades
        if len(open_trades) >= self.settings.max_concurrent_trades:
            return RiskReport(
                allowed=False,
                reason=f"Max concurrent trades reached ({self.settings.max_concurrent_trades})",
                warnings=warnings,
            )

        # 2. No opposing position on same symbol
        for trade in open_trades:
            if trade.get("symbol") == symbol:
                existing_dir = trade.get("type", trade.get("order_type", "")).upper()
                if existing_dir and existing_dir != direction.upper():
                    return RiskReport(
                        allowed=False,
                        reason=f"Opposing position exists on {symbol}",
                        warnings=warnings,
                    )

        # 3. Total drawdown check
        total_drawdown = self.calculate_drawdown(account_balance, account_equity)
        if total_drawdown >= self.settings.max_total_drawdown_pct:
            return RiskReport(
                allowed=False,
                reason=f"Total drawdown {total_drawdown:.1f}% exceeds limit {self.settings.max_total_drawdown_pct}%",
                warnings=warnings,
            )

        # 4. Daily loss check
        if daily_start_balance and daily_start_balance > 0:
            daily_loss = (daily_start_balance - account_equity) / daily_start_balance * 100
            if daily_loss >= self.settings.max_daily_loss_pct:
                return RiskReport(
                    allowed=False,
                    reason=f"Daily loss {daily_loss:.1f}% exceeds limit {self.settings.max_daily_loss_pct}%",
                    warnings=warnings,
                )
            if daily_loss > self.settings.max_daily_loss_pct * 0.8:
                warnings.append(f"Approaching daily loss limit: {daily_loss:.1f}%")

        # 5. Risk:Reward check
        rr = self.calculate_risk_reward(entry_price, sl_price, tp_price, direction)
        if rr < self.settings.min_risk_reward:
            return RiskReport(
                allowed=False,
                reason=f"Risk:Reward {rr:.2f} below minimum {self.settings.min_risk_reward}",
                risk_reward=rr,
                warnings=warnings,
            )

        # 6. Spread check
        if current_spread_pips > self.settings.max_spread_pips:
            return RiskReport(
                allowed=False,
                reason=f"Spread {current_spread_pips:.1f} pips exceeds max {self.settings.max_spread_pips}",
                warnings=warnings,
            )

        # 7. Calculate suggested lot size
        sl_dist = abs(entry_price - sl_price)
        lot = self.calculate_lot_size(symbol, account_balance, sl_dist)

        return RiskReport(
            allowed=True,
            reason="Trade validated",
            suggested_lot=lot,
            risk_reward=rr,
            warnings=warnings,
        )

    def calculate_drawdown(self, balance: float, equity: float) -> float:
        """Calculate current drawdown %."""
        if balance <= 0:
            return 0.0
        return max(0.0, (balance - equity) / balance * 100)

    def should_emergency_stop(
        self,
        account_balance: float,
        account_equity: float,
        open_trades: List[Dict],
    ) -> Tuple[bool, str]:
        """Check if emergency stop should be triggered."""
        drawdown = self.calculate_drawdown(account_balance, account_equity)
        if drawdown >= self.settings.max_total_drawdown_pct:
            return True, f"Emergency stop: drawdown {drawdown:.1f}% >= {self.settings.max_total_drawdown_pct}%"

        # Check individual trades for excessive loss
        for trade in open_trades:
            trade_profit = trade.get("profit", 0.0)
            if trade_profit < 0:
                trade_loss_pct = abs(trade_profit) / account_balance * 100
                if trade_loss_pct >= 20:
                    return True, f"Trade loss {trade_loss_pct:.1f}% on {trade.get('symbol')} exceeds 20%"

        return False, ""

    def dynamic_risk_adjustment(self, recent_trades: List[Dict]) -> float:
        """
        Adjust risk % based on recent performance.
        Reduces risk after losses, increases after wins (within bounds).
        """
        if len(recent_trades) < 5:
            return self.settings.risk_per_trade_pct

        last_5 = recent_trades[-5:]
        wins = sum(1 for t in last_5 if t.get("profit_loss", t.get("profit", 0)) > 0)
        win_rate = wins / len(last_5)

        base_risk = self.settings.risk_per_trade_pct
        if win_rate >= 0.8:
            return min(base_risk * 1.25, base_risk * 1.5)  # 25% increase, capped
        elif win_rate <= 0.2:
            return max(base_risk * 0.5, 0.5)               # 50% reduction, min 0.5%
        else:
            return base_risk

    def calculate_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate comprehensive performance metrics from trade list."""
        if not trades:
            return {"winrate": 0, "profit_factor": 0, "total_profit": 0, "max_drawdown": 0}

        profits = [t.get("profit_loss", t.get("profit", 0)) for t in trades]
        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]

        winrate = len(wins) / len(profits) * 100 if profits else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Max drawdown from equity curve
        equity = 10000.0
        peak = equity
        max_dd = 0.0
        equity_curve = [equity]
        for p in profits:
            equity += p
            equity_curve.append(equity)
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)

        total_profit = sum(profits)
        sharpe = self._sharpe(profits)

        return {
            "total_trades": len(trades),
            "win_trades": len(wins),
            "loss_trades": len(losses),
            "winrate": round(winrate, 2),
            "profit_factor": round(profit_factor, 2),
            "total_profit": round(total_profit, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 3),
            "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
            "expectancy": round(total_profit / len(profits), 2) if profits else 0,
            "equity_curve": equity_curve,
        }

    @staticmethod
    def _sharpe(returns: List[float], risk_free: float = 0.0) -> float:
        if len(returns) < 2:
            return 0.0
        import numpy as np
        arr = np.array(returns, dtype=float)
        avg = arr.mean() - risk_free
        std = arr.std(ddof=1)
        return float(avg / std * math.sqrt(252)) if std > 0 else 0.0
