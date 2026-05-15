"""
JARVIS Backtesting Engine - Professional backtesting with multiple analysis methods
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BacktestConfig:
    symbol:          str
    timeframe:       str
    start_date:      str
    end_date:        str
    initial_capital: float = 10_000.0
    commission:      float = 0.0001   # fraction of trade value
    slippage:        float = 0.0001   # fraction of price
    risk_percent:    float = 2.0
    use_sl:          bool  = True
    use_tp:          bool  = True
    sl_pips:         int   = 30
    tp_pips:         int   = 60


@dataclass
class Trade:
    entry_time:   object
    exit_time:    object
    direction:    int          # +1 = long, -1 = short
    entry_price:  float
    exit_price:   float
    lots:         float
    pnl:          float
    pnl_pct:      float
    exit_reason:  str = "signal"
    commission:   float = 0.0
    slippage:     float = 0.0


@dataclass
class BacktestResult:
    total_trades:   int
    win_trades:     int
    loss_trades:    int
    winrate:        float
    profit_factor:  float
    total_profit:   float
    max_drawdown:   float
    sharpe_ratio:   float
    sortino_ratio:  float
    calmar_ratio:   float
    equity_curve:   List[float]
    trades:         List[Dict]
    monthly_returns: Dict[str, float]
    avg_win:        float = 0.0
    avg_loss:       float = 0.0
    expectancy:     float = 0.0
    max_consec_losses: int = 0
    recovery_factor:   float = 0.0


# ---------------------------------------------------------------------------
# BacktestEngine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """Professional event-driven backtesting engine.

    All strategy functions follow the signature:
        strategy_fn(row: pd.Series, state: dict) -> int
    where the return value is  +1 (buy), -1 (sell), 0 (hold), 999 (close).
    `state` is a mutable dict the strategy can use to store per-bar context.
    """

    # ------------------------------------------------------------------
    # Core backtest
    # ------------------------------------------------------------------

    def run_backtest(
        self,
        strategy_fn: Callable,
        config:      BacktestConfig,
        data:        pd.DataFrame,
    ) -> BacktestResult:
        """Run a bar-by-bar backtest.

        Args:
            strategy_fn: Callable(row, state) → signal int.
            config:      BacktestConfig instance.
            data:        OHLCV DataFrame (columns lowercase).

        Returns:
            BacktestResult
        """
        df = self._prepare_data(data)
        equity          = config.initial_capital
        balance         = config.initial_capital
        equity_curve    = [equity]
        trades_raw: List[Trade] = []
        open_trade: Optional[Dict] = None
        state: Dict = {}

        for idx, row in df.iterrows():
            close = float(row["close"])

            # Manage open position: check SL/TP
            if open_trade is not None:
                direction   = open_trade["direction"]
                entry_price = open_trade["entry_price"]
                sl          = open_trade.get("sl", 0)
                tp          = open_trade.get("tp", 0)
                exit_price  = None
                exit_reason = None

                if config.use_sl and sl > 0:
                    if direction == 1 and row["low"]  <= sl:
                        exit_price  = sl
                        exit_reason = "sl"
                    elif direction == -1 and row["high"] >= sl:
                        exit_price  = sl
                        exit_reason = "sl"

                if exit_price is None and config.use_tp and tp > 0:
                    if direction == 1 and row["high"] >= tp:
                        exit_price  = tp
                        exit_reason = "tp"
                    elif direction == -1 and row["low"]  <= tp:
                        exit_price  = tp
                        exit_reason = "tp"

                if exit_price is not None:
                    trade = self._close_trade(
                        open_trade, exit_price, idx, exit_reason, config
                    )
                    trades_raw.append(trade)
                    balance     += trade.pnl
                    open_trade   = None

            # Strategy signal
            signal = strategy_fn(row, state)

            if open_trade is None and signal in (1, -1):
                slip  = close * config.slippage * signal
                ep    = close + slip
                lots  = self._calc_lots(ep, config)
                sl_price = tp_price = 0.0
                pip_size = close * 0.0001
                if config.use_sl:
                    sl_price = ep - signal * config.sl_pips * pip_size \
                               if signal == 1 else ep + config.sl_pips * pip_size
                if config.use_tp:
                    tp_price = ep + config.tp_pips * pip_size \
                               if signal == 1 else ep - config.tp_pips * pip_size

                open_trade = {
                    "entry_time":  idx,
                    "direction":   signal,
                    "entry_price": ep,
                    "lots":        lots,
                    "sl":          sl_price,
                    "tp":          tp_price,
                }

            elif open_trade is not None and signal == 999:
                trade = self._close_trade(
                    open_trade, close, idx, "signal", config
                )
                trades_raw.append(trade)
                balance    += trade.pnl
                open_trade  = None

            unrealised = 0.0
            if open_trade is not None:
                d   = open_trade["direction"]
                ep  = open_trade["entry_price"]
                lots = open_trade["lots"]
                unrealised = (close - ep) * d * lots * 100_000
            equity = balance + unrealised
            equity_curve.append(equity)

        # Force-close any open position at last bar
        if open_trade is not None:
            last_close = float(df["close"].iloc[-1])
            trade = self._close_trade(
                open_trade, last_close, df.index[-1], "end_of_data", config
            )
            trades_raw.append(trade)
            balance += trade.pnl
            equity_curve[-1] = balance

        return self._build_result(trades_raw, equity_curve, config, df)

    # ------------------------------------------------------------------
    # Tick backtest (higher fidelity)
    # ------------------------------------------------------------------

    def run_tick_backtest(
        self,
        strategy_fn: Callable,
        tick_data:   pd.DataFrame,
        config:      BacktestConfig,
    ) -> BacktestResult:
        """Tick-level backtest.

        tick_data must have columns: time, bid, ask  (and optionally volume).
        The strategy_fn receives each tick row and state dict, returns signal.
        """
        if not all(c in tick_data.columns for c in ("bid", "ask")):
            raise ValueError("tick_data must contain 'bid' and 'ask' columns")

        balance      = config.initial_capital
        equity_curve = [config.initial_capital]
        trades_raw: List[Trade] = []
        open_trade: Optional[Dict] = None
        state: Dict = {}

        for idx, tick in tick_data.iterrows():
            bid = float(tick["bid"])
            ask = float(tick["ask"])
            mid = (bid + ask) / 2

            if open_trade is not None:
                direction   = open_trade["direction"]
                entry_price = open_trade["entry_price"]
                lots        = open_trade["lots"]
                sl          = open_trade.get("sl", 0)
                tp          = open_trade.get("tp", 0)

                current_price = bid if direction == 1 else ask
                exit_price    = None
                exit_reason   = None

                if config.use_sl and sl > 0:
                    if direction == 1 and bid <= sl:
                        exit_price, exit_reason = sl, "sl"
                    elif direction == -1 and ask >= sl:
                        exit_price, exit_reason = sl, "sl"

                if exit_price is None and config.use_tp and tp > 0:
                    if direction == 1 and bid >= tp:
                        exit_price, exit_reason = tp, "tp"
                    elif direction == -1 and ask <= tp:
                        exit_price, exit_reason = tp, "tp"

                if exit_price is not None:
                    trade = self._close_trade(
                        open_trade, exit_price, idx, exit_reason, config
                    )
                    trades_raw.append(trade)
                    balance    += trade.pnl
                    open_trade  = None

            signal = strategy_fn(tick, state)

            if open_trade is None and signal in (1, -1):
                ep = ask if signal == 1 else bid
                lots = self._calc_lots(ep, config)
                pip  = mid * 0.0001
                sl_p = ep - signal * config.sl_pips * pip if config.use_sl else 0.0
                tp_p = ep + signal * config.tp_pips * pip if config.use_tp else 0.0
                open_trade = {
                    "entry_time":  idx,
                    "direction":   signal,
                    "entry_price": ep,
                    "lots":        lots,
                    "sl":          sl_p,
                    "tp":          tp_p,
                }

            unrealised = 0.0
            if open_trade is not None:
                cp = bid if open_trade["direction"] == 1 else ask
                unrealised = (cp - open_trade["entry_price"]) * \
                             open_trade["direction"] * open_trade["lots"] * 100_000
            equity = balance + unrealised
            equity_curve.append(equity)

        if open_trade is not None:
            last_price = float(tick_data["bid"].iloc[-1])
            trade = self._close_trade(
                open_trade, last_price, tick_data.index[-1], "end_of_data", config
            )
            trades_raw.append(trade)
            balance += trade.pnl

        return self._build_result(trades_raw, equity_curve, config, tick_data)

    # ------------------------------------------------------------------
    # Walk-forward analysis
    # ------------------------------------------------------------------

    def walk_forward_analysis(
        self,
        strategy_fn: Callable,
        config:      BacktestConfig,
        data:        pd.DataFrame,
        windows:     int = 5,
    ) -> Dict:
        """Split data into `windows` IS/OOS folds and run separate backtests.

        Returns:
            {
              "windows":         list of {is_result, oos_result, is_range, oos_range},
              "combined_oos":    BacktestResult of all OOS trades concatenated,
              "avg_oos_sharpe":  float,
              "avg_oos_dd":      float,
              "consistency":     float (% of OOS windows with positive return),
            }
        """
        df = self._prepare_data(data)
        n  = len(df)
        fold_size = n // (windows + 1)

        window_results = []
        all_oos_trades: List[Dict] = []
        all_oos_equity: List[float] = [config.initial_capital]

        for i in range(windows):
            is_start  = 0
            is_end    = (i + 1) * fold_size
            oos_start = is_end
            oos_end   = min(oos_start + fold_size, n)

            is_data  = df.iloc[is_start:is_end]
            oos_data = df.iloc[oos_start:oos_end]

            if len(is_data) < 10 or len(oos_data) < 5:
                continue

            is_result  = self.run_backtest(strategy_fn, config, is_data)
            oos_result = self.run_backtest(strategy_fn, config, oos_data)

            all_oos_trades.extend(oos_result.trades)
            all_oos_equity.extend(oos_result.equity_curve[1:])

            window_results.append({
                "window":   i + 1,
                "is_range": (str(is_data.index[0]), str(is_data.index[-1])),
                "oos_range": (str(oos_data.index[0]), str(oos_data.index[-1])),
                "is_result":  self._result_summary(is_result),
                "oos_result": self._result_summary(oos_result),
            })

            logger.info(
                f"WFA window {i+1}/{windows}: "
                f"IS sharpe={is_result.sharpe_ratio:.2f} "
                f"OOS sharpe={oos_result.sharpe_ratio:.2f}"
            )

        oos_sharpes    = [w["oos_result"]["sharpe_ratio"]   for w in window_results]
        oos_drawdowns  = [w["oos_result"]["max_drawdown"]   for w in window_results]
        oos_profitable = [w["oos_result"]["total_profit"] > 0 for w in window_results]

        return {
            "windows":        window_results,
            "avg_oos_sharpe": float(np.mean(oos_sharpes)) if oos_sharpes else 0.0,
            "avg_oos_dd":     float(np.mean(oos_drawdowns)) if oos_drawdowns else 0.0,
            "consistency":    float(np.mean(oos_profitable)) if oos_profitable else 0.0,
            "all_oos_trades": all_oos_trades,
        }

    # ------------------------------------------------------------------
    # Monte Carlo analysis
    # ------------------------------------------------------------------

    def monte_carlo_analysis(
        self,
        trades:      List[Dict],
        simulations: int   = 1_000,
        confidence:  float = 0.95,
        initial_capital: float = 10_000.0,
    ) -> Dict:
        """Monte Carlo simulation by randomly reshuffling trade order.

        Returns:
            {
              "mean_return":        float,
              "median_return":      float,
              "std_return":         float,
              "ci_lower":           float (lower confidence bound on final equity),
              "ci_upper":           float,
              "max_dd_distribution": list[float],
              "mean_max_dd":        float,
              "prob_ruin":          float (pct of sims ending below 50% of capital),
              "final_equities":     list[float],
            }
        """
        if not trades:
            logger.warning("Monte Carlo: no trades to simulate")
            return {}

        pnls = [float(t.get("pnl", 0.0)) for t in trades]

        final_equities: List[float] = []
        max_drawdowns:  List[float] = []

        for _ in range(simulations):
            shuffled = random.sample(pnls, len(pnls))
            equity   = initial_capital
            peak     = initial_capital
            max_dd   = 0.0
            for pnl in shuffled:
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / (peak + 1e-10)
                if dd > max_dd:
                    max_dd = dd

            final_equities.append(equity)
            max_drawdowns.append(max_dd)

        eq_arr = np.array(final_equities)
        dd_arr = np.array(max_drawdowns)
        alpha  = 1 - confidence
        ruin_threshold = initial_capital * 0.5

        return {
            "mean_return":         float((eq_arr.mean() - initial_capital) / initial_capital),
            "median_return":       float((np.median(eq_arr) - initial_capital) / initial_capital),
            "std_return":          float(eq_arr.std() / initial_capital),
            "ci_lower":            float(np.percentile(eq_arr, alpha / 2 * 100)),
            "ci_upper":            float(np.percentile(eq_arr, (1 - alpha / 2) * 100)),
            "max_dd_distribution": dd_arr.tolist(),
            "mean_max_dd":         float(dd_arr.mean()),
            "percentile_5_dd":     float(np.percentile(dd_arr, 95)),
            "prob_ruin":           float((eq_arr < ruin_threshold).mean()),
            "final_equities":      eq_arr.tolist(),
        }

    # ------------------------------------------------------------------
    # Multi-timeframe test
    # ------------------------------------------------------------------

    def multi_timeframe_test(
        self,
        strategy_fn: Callable,
        config:      BacktestConfig,
        data_map:    Dict[str, pd.DataFrame],
    ) -> Dict:
        """Run independent backtests across multiple timeframes.

        Args:
            strategy_fn: Strategy function (same signature as run_backtest).
            config:      Base config (timeframe field is overridden per run).
            data_map:    { timeframe_str: ohlcv_dataframe }

        Returns:
            { timeframe: BacktestResult-summary dict }
        """
        results = {}
        for tf, df in data_map.items():
            cfg = BacktestConfig(
                symbol=config.symbol,
                timeframe=tf,
                start_date=config.start_date,
                end_date=config.end_date,
                initial_capital=config.initial_capital,
                commission=config.commission,
                slippage=config.slippage,
                risk_percent=config.risk_percent,
                use_sl=config.use_sl,
                use_tp=config.use_tp,
                sl_pips=config.sl_pips,
                tp_pips=config.tp_pips,
            )
            try:
                result = self.run_backtest(strategy_fn, cfg, df)
                results[tf] = self._result_summary(result)
                logger.info(
                    f"MTF {tf}: trades={result.total_trades} "
                    f"profit={result.total_profit:.2f} "
                    f"sharpe={result.sharpe_ratio:.2f}"
                )
            except Exception as exc:
                logger.error(f"MTF backtest failed for {tf}: {exc}")
                results[tf] = {"error": str(exc)}

        return results

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def calculate_metrics(
        self,
        trades:          List[Dict],
        equity_curve:    List[float],
        initial_capital: float,
    ) -> Dict:
        """Calculate comprehensive performance metrics.

        Args:
            trades:         List of trade dicts (keys: pnl, direction, pnl_pct).
            equity_curve:   List of equity values (one per bar + initial).
            initial_capital: Starting capital.

        Returns:
            dict with all key performance metrics.
        """
        if not trades:
            return self._empty_metrics(initial_capital)

        pnls = np.array([t.get("pnl", 0.0) for t in trades])

        wins   = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        total  = len(pnls)

        winrate       = len(wins) / total if total else 0.0
        avg_win       = float(wins.mean())  if len(wins)   else 0.0
        avg_loss      = float(losses.mean()) if len(losses) else 0.0
        gross_profit  = float(wins.sum())
        gross_loss    = float(abs(losses.sum()))
        profit_factor = gross_profit / (gross_loss + 1e-10)
        expectancy    = (winrate * avg_win) + ((1 - winrate) * avg_loss)

        # Equity metrics
        eq_arr  = np.array(equity_curve, dtype=float)
        total_profit = float(eq_arr[-1] - initial_capital)

        # Max drawdown
        peak    = np.maximum.accumulate(eq_arr)
        dd      = (peak - eq_arr) / (peak + 1e-10)
        max_dd  = float(dd.max())

        # Sharpe ratio (annualised, assuming daily bars)
        returns = np.diff(eq_arr) / (eq_arr[:-1] + 1e-10)
        sharpe  = float(
            returns.mean() / (returns.std() + 1e-10) * math.sqrt(252)
        ) if len(returns) > 1 else 0.0

        # Sortino ratio
        neg_ret  = returns[returns < 0]
        down_std = neg_ret.std() if len(neg_ret) > 1 else 1e-10
        sortino  = float(returns.mean() / (down_std + 1e-10) * math.sqrt(252))

        # Calmar ratio
        calmar = float(
            (total_profit / initial_capital) / (max_dd + 1e-10)
        ) if max_dd > 0 else 0.0

        # Recovery factor
        recovery = float(total_profit / (gross_loss + 1e-10))

        # Consecutive losses
        max_consec = self._max_consecutive_losses(pnls)

        return {
            "total_trades":      total,
            "win_trades":        int(len(wins)),
            "loss_trades":       int(len(losses)),
            "winrate":           round(winrate, 4),
            "profit_factor":     round(profit_factor, 4),
            "total_profit":      round(total_profit, 2),
            "gross_profit":      round(gross_profit, 2),
            "gross_loss":        round(gross_loss, 2),
            "max_drawdown":      round(max_dd, 4),
            "sharpe_ratio":      round(sharpe, 4),
            "sortino_ratio":     round(sortino, 4),
            "calmar_ratio":      round(calmar, 4),
            "avg_win":           round(avg_win, 2),
            "avg_loss":          round(avg_loss, 2),
            "expectancy":        round(expectancy, 2),
            "recovery_factor":   round(recovery, 4),
            "max_consec_losses": max_consec,
            "final_equity":      round(float(eq_arr[-1]), 2),
            "return_pct":        round(total_profit / initial_capital * 100, 2),
        }

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    def generate_report(self, result: BacktestResult, output_path: str) -> str:
        """Generate a Markdown performance report.

        Args:
            result:      BacktestResult instance.
            output_path: File path to write the report (with .md or .txt extension).

        Returns:
            The report text content.
        """
        lines = [
            "# JARVIS Backtest Report",
            "",
            "## Summary",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Trades      | {result.total_trades} |",
            f"| Win Trades        | {result.win_trades} |",
            f"| Loss Trades       | {result.loss_trades} |",
            f"| Win Rate          | {result.winrate:.2%} |",
            f"| Profit Factor     | {result.profit_factor:.2f} |",
            f"| Total Profit      | ${result.total_profit:,.2f} |",
            f"| Max Drawdown      | {result.max_drawdown:.2%} |",
            f"| Sharpe Ratio      | {result.sharpe_ratio:.2f} |",
            f"| Sortino Ratio     | {result.sortino_ratio:.2f} |",
            f"| Calmar Ratio      | {result.calmar_ratio:.2f} |",
            f"| Avg Win           | ${result.avg_win:,.2f} |",
            f"| Avg Loss          | ${result.avg_loss:,.2f} |",
            f"| Expectancy        | ${result.expectancy:,.2f} |",
            f"| Max Consec Losses | {result.max_consec_losses} |",
            f"| Recovery Factor   | {result.recovery_factor:.2f} |",
            "",
            "## Monthly Returns",
            "| Month | Return |",
            "|-------|--------|",
        ]

        for month, ret in sorted(result.monthly_returns.items()):
            sign = "+" if ret >= 0 else ""
            lines.append(f"| {month} | {sign}{ret:.2f}% |")

        lines += [
            "",
            "## Trade Log (last 20)",
            "| # | Direction | Entry | Exit | PnL |",
            "|---|-----------|-------|------|-----|",
        ]
        for i, t in enumerate(result.trades[-20:], 1):
            d    = "BUY" if t.get("direction", 1) == 1 else "SELL"
            ep   = t.get("entry_price", 0)
            xp   = t.get("exit_price", 0)
            pnl  = t.get("pnl", 0)
            lines.append(f"| {i} | {d} | {ep:.5f} | {xp:.5f} | {pnl:+.2f} |")

        report = "\n".join(lines)

        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(report, encoding="utf-8")
        logger.info(f"Backtest report saved: {p}")
        return report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare_data(df: pd.DataFrame) -> pd.DataFrame:
        """Normalise column names to lowercase and sort by index."""
        out = df.copy()
        out.columns = [c.lower() for c in out.columns]
        required = {"open", "high", "low", "close"}
        missing  = required - set(out.columns)
        if missing:
            raise ValueError(f"Data missing columns: {missing}")
        if not out.index.is_monotonic_increasing:
            out = out.sort_index()
        return out

    @staticmethod
    def _calc_lots(price: float, config: BacktestConfig) -> float:
        risk   = config.initial_capital * config.risk_percent / 100.0
        sl_dist = price * config.sl_pips * 0.0001
        if sl_dist <= 0:
            return 0.01
        lots = risk / (sl_dist * 100_000)
        return max(0.01, min(100.0, round(lots, 2)))

    @staticmethod
    def _close_trade(
        open_trade:  Dict,
        exit_price:  float,
        exit_time:   object,
        exit_reason: str,
        config:      BacktestConfig,
    ) -> Trade:
        direction   = open_trade["direction"]
        entry_price = open_trade["entry_price"]
        lots        = open_trade["lots"]
        commission  = (entry_price + exit_price) * lots * 100_000 * config.commission
        pnl         = (exit_price - entry_price) * direction * lots * 100_000 - commission

        return Trade(
            entry_time   = open_trade["entry_time"],
            exit_time    = exit_time,
            direction    = direction,
            entry_price  = entry_price,
            exit_price   = exit_price,
            lots         = lots,
            pnl          = pnl,
            pnl_pct      = pnl / (entry_price * lots * 100_000 + 1e-10),
            exit_reason  = exit_reason,
            commission   = commission,
        )

    def _build_result(
        self,
        trades:      List[Trade],
        equity_curve: List[float],
        config:       BacktestConfig,
        df:           pd.DataFrame,
    ) -> BacktestResult:
        trades_dict = [
            {
                "entry_time":  str(t.entry_time),
                "exit_time":   str(t.exit_time),
                "direction":   t.direction,
                "entry_price": t.entry_price,
                "exit_price":  t.exit_price,
                "lots":        t.lots,
                "pnl":         t.pnl,
                "pnl_pct":     t.pnl_pct,
                "exit_reason": t.exit_reason,
                "commission":  t.commission,
            }
            for t in trades
        ]

        metrics = self.calculate_metrics(trades_dict, equity_curve, config.initial_capital)
        monthly = self._calc_monthly_returns(equity_curve, df)

        return BacktestResult(
            total_trades    = metrics["total_trades"],
            win_trades      = metrics["win_trades"],
            loss_trades     = metrics["loss_trades"],
            winrate         = metrics["winrate"],
            profit_factor   = metrics["profit_factor"],
            total_profit    = metrics["total_profit"],
            max_drawdown    = metrics["max_drawdown"],
            sharpe_ratio    = metrics["sharpe_ratio"],
            sortino_ratio   = metrics["sortino_ratio"],
            calmar_ratio    = metrics["calmar_ratio"],
            equity_curve    = equity_curve,
            trades          = trades_dict,
            monthly_returns = monthly,
            avg_win         = metrics["avg_win"],
            avg_loss        = metrics["avg_loss"],
            expectancy      = metrics["expectancy"],
            max_consec_losses = metrics["max_consec_losses"],
            recovery_factor = metrics["recovery_factor"],
        )

    @staticmethod
    def _calc_monthly_returns(equity_curve: List[float],
                               df: pd.DataFrame) -> Dict[str, float]:
        """Approximate monthly returns from the equity curve."""
        if len(equity_curve) < 2 or len(df) < 2:
            return {}

        # Try to align equity curve with df index
        idx = df.index
        try:
            dates = pd.to_datetime(idx)
        except Exception:
            return {}

        # Downsample to roughly month-end equity values
        monthly: Dict[str, float] = {}
        eq_arr  = np.array(equity_curve[1:])  # skip initial
        n       = min(len(eq_arr), len(dates))
        temp_df = pd.DataFrame({"equity": eq_arr[:n]}, index=dates[:n])

        try:
            month_end = temp_df.resample("ME")["equity"].last()
            for i in range(1, len(month_end)):
                prev = month_end.iloc[i - 1]
                curr = month_end.iloc[i]
                month_key = month_end.index[i].strftime("%Y-%m")
                monthly[month_key] = round((curr - prev) / (prev + 1e-10) * 100, 2)
        except Exception:
            pass

        return monthly

    @staticmethod
    def _max_consecutive_losses(pnls: np.ndarray) -> int:
        max_consec = 0
        current    = 0
        for pnl in pnls:
            if pnl < 0:
                current += 1
                max_consec = max(max_consec, current)
            else:
                current = 0
        return max_consec

    @staticmethod
    def _empty_metrics(initial_capital: float) -> Dict:
        return {
            "total_trades": 0, "win_trades": 0, "loss_trades": 0,
            "winrate": 0.0, "profit_factor": 0.0, "total_profit": 0.0,
            "gross_profit": 0.0, "gross_loss": 0.0, "max_drawdown": 0.0,
            "sharpe_ratio": 0.0, "sortino_ratio": 0.0, "calmar_ratio": 0.0,
            "avg_win": 0.0, "avg_loss": 0.0, "expectancy": 0.0,
            "recovery_factor": 0.0, "max_consec_losses": 0,
            "final_equity": initial_capital, "return_pct": 0.0,
        }

    @staticmethod
    def _result_summary(result: BacktestResult) -> Dict:
        return {
            "total_trades":    result.total_trades,
            "winrate":         result.winrate,
            "profit_factor":   result.profit_factor,
            "total_profit":    result.total_profit,
            "max_drawdown":    result.max_drawdown,
            "sharpe_ratio":    result.sharpe_ratio,
            "sortino_ratio":   result.sortino_ratio,
            "calmar_ratio":    result.calmar_ratio,
            "expectancy":      result.expectancy,
            "max_consec_losses": result.max_consec_losses,
        }
