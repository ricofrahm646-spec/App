import math
import statistics
from typing import Dict, List

from loguru import logger


class RiskService:
    """
    Central risk management service for the JARVIS trading system.

    All monetary values are in account currency units.
    All percentages are expressed as decimals (0.02 = 2%).
    """

    MAX_RISK_PER_TRADE: float = 0.02   # 2% per trade
    MAX_DAILY_DRAWDOWN: float = 0.05   # 5% daily drawdown limit
    MAX_TOTAL_DRAWDOWN: float = 0.20   # 20% total drawdown limit
    MAX_CONCURRENT_TRADES: int = 1
    MIN_RISK_REWARD: float = 1.5       # Minimum acceptable R:R ratio

    # ------------------------------------------------------------------
    # Position sizing
    # ------------------------------------------------------------------

    def calculate_position_size(
        self,
        account_balance: float,
        risk_percent: float,
        sl_distance_pips: float,
        pip_value: float,
    ) -> float:
        """
        Calculate the position size in lots using fixed fractional risk.

        Args:
            account_balance: Current account balance.
            risk_percent: Fraction of balance to risk (e.g. 0.02 = 2%).
            sl_distance_pips: Distance from entry to stop-loss in pips.
            pip_value: Monetary value of 1 pip per 1 standard lot.

        Returns:
            Lot size rounded to 2 decimal places, minimum 0.01.
        """
        if sl_distance_pips <= 0 or pip_value <= 0 or account_balance <= 0:
            logger.warning(
                "calculate_position_size: invalid input "
                f"balance={account_balance} sl_pips={sl_distance_pips} pip_value={pip_value}"
            )
            return 0.01

        risk_amount = account_balance * risk_percent
        loss_per_lot = sl_distance_pips * pip_value
        raw_lots = risk_amount / loss_per_lot

        # Clamp to reasonable bounds and round
        lots = max(0.01, min(100.0, round(raw_lots, 2)))
        logger.debug(
            f"Position size: balance={account_balance:.2f} risk={risk_percent*100:.1f}% "
            f"sl={sl_distance_pips}pips pip_val={pip_value:.4f} → lots={lots}"
        )
        return lots

    # ------------------------------------------------------------------
    # Risk / reward
    # ------------------------------------------------------------------

    def calculate_risk_reward(
        self,
        entry: float,
        sl: float,
        tp: float,
        direction: str,
    ) -> float:
        """
        Compute the risk-to-reward ratio for a trade.

        Args:
            entry: Entry price.
            sl: Stop-loss price.
            tp: Take-profit price.
            direction: "BUY" or "SELL".

        Returns:
            R:R ratio as a positive float. Returns 0.0 on invalid input.
        """
        direction = direction.upper()
        if direction == "BUY":
            risk = entry - sl
            reward = tp - entry
        elif direction == "SELL":
            risk = sl - entry
            reward = entry - tp
        else:
            logger.warning(f"Unknown direction: {direction}")
            return 0.0

        if risk <= 0:
            logger.warning(f"Invalid risk ({risk}): SL is on the wrong side of entry.")
            return 0.0
        if reward <= 0:
            logger.warning(f"Invalid reward ({reward}): TP is on the wrong side of entry.")
            return 0.0

        rr = round(reward / risk, 2)
        logger.debug(f"R:R for {direction}: entry={entry} sl={sl} tp={tp} → {rr}")
        return rr

    # ------------------------------------------------------------------
    # Trade validation
    # ------------------------------------------------------------------

    def validate_trade(
        self,
        symbol: str,
        direction: str,
        account_info: Dict,
        open_trades: List[Dict],
    ) -> Dict:
        """
        Validate whether a new trade is permissible under risk rules.

        Args:
            symbol: Instrument to trade.
            direction: "BUY" or "SELL".
            account_info: From MT5Service.get_account_info().
            open_trades: List of currently open positions.

        Returns:
            {"allowed": bool, "reason": str}
        """
        direction = direction.upper()
        balance = account_info.get("balance", 0.0)
        equity = account_info.get("equity", 0.0)
        margin_level = account_info.get("margin_level", 9999.0)

        # Check max concurrent trades
        if len(open_trades) >= self.MAX_CONCURRENT_TRADES:
            return {
                "allowed": False,
                "reason": (
                    f"Max concurrent trades reached ({self.MAX_CONCURRENT_TRADES}). "
                    f"Currently open: {len(open_trades)}."
                ),
            }

        # Check for opposing position on same symbol
        for trade in open_trades:
            if trade.get("symbol") == symbol:
                trade_dir = trade.get("type", "").upper()
                if trade_dir != direction:
                    return {
                        "allowed": False,
                        "reason": (
                            f"Opposing {trade_dir} trade already open for {symbol}. "
                            "Cannot place opposing direction."
                        ),
                    }

        # Check total drawdown
        if balance > 0:
            total_drawdown = (balance - equity) / balance
            if total_drawdown >= self.MAX_TOTAL_DRAWDOWN:
                return {
                    "allowed": False,
                    "reason": (
                        f"Total drawdown {total_drawdown*100:.1f}% exceeds "
                        f"maximum allowed {self.MAX_TOTAL_DRAWDOWN*100:.0f}%."
                    ),
                }

        # Check margin level (warn below 200%, block below 120%)
        if margin_level < 120.0 and margin_level > 0:
            return {
                "allowed": False,
                "reason": (
                    f"Margin level too low: {margin_level:.1f}%. "
                    "Minimum required: 120%."
                ),
            }

        # All checks passed
        return {"allowed": True, "reason": "Trade parameters within risk limits."}

    # ------------------------------------------------------------------
    # Drawdown calculations
    # ------------------------------------------------------------------

    def calculate_drawdown(self, balance: float, equity: float) -> float:
        """
        Calculate current floating drawdown as a fraction of balance.

        Returns: 0.0 to 1.0 (e.g. 0.05 = 5% drawdown).
        """
        if balance <= 0:
            return 0.0
        drawdown = max(0.0, (balance - equity) / balance)
        return round(drawdown, 6)

    def calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """
        Calculate the maximum peak-to-trough drawdown from an equity curve.

        Args:
            equity_curve: Chronological list of equity values.

        Returns:
            Maximum drawdown as a fraction (e.g. 0.15 = 15%).
        """
        if len(equity_curve) < 2:
            return 0.0

        max_drawdown = 0.0
        peak = equity_curve[0]

        for equity in equity_curve[1:]:
            if equity > peak:
                peak = equity
            elif peak > 0:
                drawdown = (peak - equity) / peak
                max_drawdown = max(max_drawdown, drawdown)

        return round(max_drawdown, 6)

    # ------------------------------------------------------------------
    # Trading halt logic
    # ------------------------------------------------------------------

    def should_stop_trading(
        self,
        balance_start: float,
        current_equity: float,
        trades: List[Dict],
    ) -> Dict:
        """
        Determine whether trading should be halted based on risk limits.

        Args:
            balance_start: Account balance at the start of the trading session / day.
            current_equity: Current account equity.
            trades: Trade history for the current period.

        Returns:
            {"stop": bool, "reason": str}
        """
        if balance_start <= 0:
            return {"stop": True, "reason": "Invalid starting balance."}

        total_drawdown = (balance_start - current_equity) / balance_start

        if total_drawdown >= self.MAX_TOTAL_DRAWDOWN:
            return {
                "stop": True,
                "reason": (
                    f"Total drawdown {total_drawdown*100:.1f}% reached the "
                    f"{self.MAX_TOTAL_DRAWDOWN*100:.0f}% limit."
                ),
            }

        # Calculate intraday loss from closed trades
        today_profit = sum(t.get("profit", 0.0) for t in trades)
        daily_drawdown = -today_profit / balance_start if today_profit < 0 else 0.0

        if daily_drawdown >= self.MAX_DAILY_DRAWDOWN:
            return {
                "stop": True,
                "reason": (
                    f"Daily drawdown {daily_drawdown*100:.1f}% reached the "
                    f"{self.MAX_DAILY_DRAWDOWN*100:.0f}% daily limit."
                ),
            }

        # Check for consecutive losses (stop after 5 consecutive losses)
        if len(trades) >= 5:
            last_five = [t.get("profit", 0.0) for t in trades[-5:]]
            if all(p < 0 for p in last_five):
                return {
                    "stop": True,
                    "reason": "5 consecutive losing trades detected. Trading halted for review.",
                }

        return {"stop": False, "reason": "Risk parameters within safe limits."}

    # ------------------------------------------------------------------
    # Performance metrics
    # ------------------------------------------------------------------

    def calculate_profit_factor(self, trades: List[Dict]) -> float:
        """
        Calculate the profit factor (gross profit / gross loss).

        Returns: Profit factor. Returns 0.0 if no losing trades exist.
        """
        gross_profit = sum(t["profit"] for t in trades if t.get("profit", 0) > 0)
        gross_loss = abs(sum(t["profit"] for t in trades if t.get("profit", 0) < 0))

        if gross_loss == 0:
            return float("inf") if gross_profit > 0 else 0.0

        return round(gross_profit / gross_loss, 4)

    def calculate_sharpe_ratio(
        self, returns: List[float], risk_free_rate: float = 0.0
    ) -> float:
        """
        Calculate the annualised Sharpe Ratio from a series of period returns.

        Args:
            returns: List of periodic returns (e.g. daily P&L as fractions).
            risk_free_rate: Annual risk-free rate (default 0%).

        Returns:
            Annualised Sharpe Ratio. Returns 0.0 if insufficient data.
        """
        if len(returns) < 2:
            return 0.0

        mean_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)

        if std_return == 0:
            return 0.0

        # Assume daily returns → annualise with √252
        periods_per_year = 252
        daily_rf = risk_free_rate / periods_per_year
        sharpe = (mean_return - daily_rf) / std_return * math.sqrt(periods_per_year)
        return round(sharpe, 4)

    def calculate_win_rate(self, trades: List[Dict]) -> float:
        """Return win rate as a fraction (0.0–1.0)."""
        if not trades:
            return 0.0
        winners = sum(1 for t in trades if t.get("profit", 0) > 0)
        return round(winners / len(trades), 4)

    def calculate_expectancy(self, trades: List[Dict]) -> float:
        """
        Calculate mathematical expectancy per trade in account currency.

        Expectancy = (Win Rate × Avg Win) - (Loss Rate × Avg Loss)
        """
        if not trades:
            return 0.0

        wins = [t["profit"] for t in trades if t.get("profit", 0) > 0]
        losses = [abs(t["profit"]) for t in trades if t.get("profit", 0) < 0]

        win_rate = len(wins) / len(trades)
        loss_rate = 1 - win_rate
        avg_win = statistics.mean(wins) if wins else 0.0
        avg_loss = statistics.mean(losses) if losses else 0.0

        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        return round(expectancy, 4)

    # ------------------------------------------------------------------
    # Dynamic risk adjustment
    # ------------------------------------------------------------------

    def dynamic_risk_adjustment(self, recent_performance: Dict) -> float:
        """
        Adjust the risk percentage based on recent trading performance.

        Logic:
        - Reduce risk after losses or high drawdown.
        - Increase risk (up to max) after a winning streak.

        Args:
            recent_performance: {
                "consecutive_wins": int,
                "consecutive_losses": int,
                "current_drawdown": float,   # fraction, e.g. 0.05
                "win_rate_recent": float,    # fraction over last 20 trades
                "profit_factor_recent": float,
            }

        Returns:
            Adjusted risk fraction (clamped between 0.005 and MAX_RISK_PER_TRADE).
        """
        base_risk = self.MAX_RISK_PER_TRADE
        adjusted = base_risk

        consecutive_wins = recent_performance.get("consecutive_wins", 0)
        consecutive_losses = recent_performance.get("consecutive_losses", 0)
        drawdown = recent_performance.get("current_drawdown", 0.0)
        win_rate = recent_performance.get("win_rate_recent", 0.5)
        pf = recent_performance.get("profit_factor_recent", 1.0)

        # Penalty for drawdown
        if drawdown >= 0.10:
            adjusted *= 0.50   # Halve risk above 10% drawdown
        elif drawdown >= 0.05:
            adjusted *= 0.75   # Reduce by 25% above 5% drawdown

        # Penalty for consecutive losses
        if consecutive_losses >= 3:
            adjusted *= max(0.25, 1 - 0.15 * consecutive_losses)

        # Bonus for strong win streak and healthy profit factor
        if consecutive_wins >= 3 and pf > 1.5 and win_rate > 0.6:
            adjusted *= min(1.25, 1 + 0.05 * consecutive_wins)

        # Hard clamp
        adjusted = round(max(0.005, min(self.MAX_RISK_PER_TRADE, adjusted)), 4)

        logger.debug(
            f"Dynamic risk: base={base_risk*100:.1f}% "
            f"→ adjusted={adjusted*100:.2f}% "
            f"(dd={drawdown*100:.1f}%, "
            f"cons_wins={consecutive_wins}, cons_losses={consecutive_losses})"
        )
        return adjusted

    # ------------------------------------------------------------------
    # Utility summary
    # ------------------------------------------------------------------

    def full_risk_report(
        self,
        account_info: Dict,
        trades: List[Dict],
        equity_curve: List[float],
        returns: List[float],
    ) -> Dict:
        """
        Generate a comprehensive risk report for the trading session.

        Returns a structured dict with all key risk metrics.
        """
        balance = account_info.get("balance", 0.0)
        equity = account_info.get("equity", 0.0)

        return {
            "current_drawdown_pct": round(self.calculate_drawdown(balance, equity) * 100, 2),
            "max_drawdown_pct": round(self.calculate_max_drawdown(equity_curve) * 100, 2),
            "profit_factor": self.calculate_profit_factor(trades),
            "sharpe_ratio": self.calculate_sharpe_ratio(returns),
            "win_rate_pct": round(self.calculate_win_rate(trades) * 100, 2),
            "expectancy": self.calculate_expectancy(trades),
            "total_trades": len(trades),
            "open_positions": account_info.get("open_positions", 0),
            "balance": balance,
            "equity": equity,
            "margin_level": account_info.get("margin_level", 0.0),
        }
