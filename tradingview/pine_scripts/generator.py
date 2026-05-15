"""
JARVIS Pine Script Generator.

Programmatically generates TradingView Pine Script v5 code for
custom indicators, strategies, and alert conditions.
"""

import logging
import textwrap
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PineScriptGenerator:
    """Generate Pine Script v5 source code for TradingView."""

    VERSION = "5"

    # ── Indicator generation ─────────────────────────────────────────

    def generate_indicator_script(
        self,
        name: str,
        params: Dict[str, Any],
    ) -> str:
        """Generate a Pine Script indicator.

        Args:
            name: Indicator name shown on the chart.
            params: Configuration dict.  Recognised keys:
                indicator_type - "ma_crossover" | "rsi" | "macd" | "bollinger" |
                                 "stochastic" | "atr" | "custom"
                overlay        - plot on price chart (default True)
                (type-specific keys documented in each helper)

        Returns:
            Complete Pine Script v5 source code.
        """
        indicator_type = params.get("indicator_type", "ma_crossover")
        overlay = params.get("overlay", True)

        header = self._script_header(name, overlay=overlay)
        body = self._indicator_body(indicator_type, params)
        return f"{header}\n\n{body}\n"

    def _indicator_body(self, itype: str, params: Dict[str, Any]) -> str:
        generators = {
            "ma_crossover": self._ma_crossover_indicator,
            "rsi": self._rsi_indicator,
            "macd": self._macd_indicator,
            "bollinger": self._bollinger_indicator,
            "stochastic": self._stochastic_indicator,
            "atr": self._atr_indicator,
        }
        gen = generators.get(itype)
        if gen is None:
            logger.warning("Unknown indicator type '%s', using custom stub", itype)
            return self._custom_indicator(params)
        return gen(params)

    # ── Strategy generation ──────────────────────────────────────────

    def generate_strategy_script(
        self,
        name: str,
        params: Dict[str, Any],
    ) -> str:
        """Generate a Pine Script strategy.

        Args:
            name: Strategy name.
            params: Configuration dict.  Recognised keys:
                strategy_type - "ma_crossover" | "rsi_reversal" | "breakout"
                initial_capital, default_qty, commission, slippage
                (type-specific keys documented in each helper)

        Returns:
            Complete Pine Script v5 source code.
        """
        strategy_type = params.get("strategy_type", "ma_crossover")
        initial_capital = params.get("initial_capital", 10000)
        default_qty = params.get("default_qty", 1)
        commission = params.get("commission", 0.0)
        slippage = params.get("slippage", 0)

        header = textwrap.dedent(f"""\
            //@version=5
            strategy("{name}", overlay=true, initial_capital={initial_capital},
                     default_qty_type=strategy.fixed, default_qty_value={default_qty},
                     commission_type=strategy.commission.percent, commission_value={commission},
                     slippage={slippage})
        """).rstrip()

        body = self._strategy_body(strategy_type, params)
        return f"{header}\n\n{body}\n"

    def _strategy_body(self, stype: str, params: Dict[str, Any]) -> str:
        generators = {
            "ma_crossover": self._ma_crossover_strategy,
            "rsi_reversal": self._rsi_reversal_strategy,
            "breakout": self._breakout_strategy,
        }
        gen = generators.get(stype)
        if gen is None:
            logger.warning("Unknown strategy type '%s', using custom stub", stype)
            return self._custom_strategy(params)
        return gen(params)

    # ── Alert script ─────────────────────────────────────────────────

    def generate_alert_script(
        self,
        conditions: List[Dict[str, Any]],
    ) -> str:
        """Generate a Pine Script with alert conditions.

        Args:
            conditions: List of dicts, each with:
                name      - human-readable label
                condition - Pine expression string (e.g. "ta.crossover(fast, slow)")
                message   - alert message template

        Returns:
            Complete Pine Script v5 source code.
        """
        header = self._script_header("JARVIS Alert Conditions", overlay=True)
        lines: List[str] = []
        for idx, cond in enumerate(conditions, 1):
            cname = cond.get("name", f"Condition {idx}")
            expr = cond.get("condition", "close > open")
            msg = cond.get("message", f'{{"action": "alert", "condition": "{cname}"}}')
            var = f"cond_{idx}"
            lines.append(f'{var} = {expr}')
            lines.append(
                f'alertcondition({var}, title="{cname}", '
                f'message=\'{msg}\')'
            )
            lines.append(
                f'plotshape({var}, title="{cname}", '
                f'style=shape.triangleup, location=location.belowbar, '
                f'color=color.new(color.green, 0), size=size.small)'
            )
            lines.append("")

        return f"{header}\n\n{chr(10).join(lines)}\n"

    # ── Forex-pair specific helpers ──────────────────────────────────

    @staticmethod
    def generate_forex_session_highlight(
        pair: str = "EURUSD",
    ) -> str:
        """Generate script that highlights major forex trading sessions."""
        return textwrap.dedent(f"""\
            //@version=5
            indicator("Forex Sessions — {pair}", overlay=true)

            show_tokyo  = input.bool(true, "Show Tokyo Session")
            show_london = input.bool(true, "Show London Session")
            show_ny     = input.bool(true, "Show New York Session")

            is_tokyo  = (hour >= 0 and hour < 9)
            is_london = (hour >= 7 and hour < 16)
            is_ny     = (hour >= 13 and hour < 22)

            bgcolor(show_tokyo  and is_tokyo  ? color.new(color.blue, 92) : na, title="Tokyo")
            bgcolor(show_london and is_london ? color.new(color.green, 92) : na, title="London")
            bgcolor(show_ny     and is_ny     ? color.new(color.orange, 92) : na, title="New York")
        """)

    # ── Private: indicator bodies ────────────────────────────────────

    @staticmethod
    def _ma_crossover_indicator(params: Dict[str, Any]) -> str:
        fast = params.get("fast_period", 9)
        slow = params.get("slow_period", 21)
        ma_type = params.get("ma_type", "EMA")
        ma_func = "ta.ema" if ma_type.upper() == "EMA" else "ta.sma"
        return textwrap.dedent(f"""\
            fast_len = input.int({fast}, "Fast Period")
            slow_len = input.int({slow}, "Slow Period")

            fast_ma = {ma_func}(close, fast_len)
            slow_ma = {ma_func}(close, slow_len)

            bull_cross = ta.crossover(fast_ma, slow_ma)
            bear_cross = ta.crossunder(fast_ma, slow_ma)

            plot(fast_ma, "Fast MA", color=color.blue, linewidth=2)
            plot(slow_ma, "Slow MA", color=color.red, linewidth=2)

            plotshape(bull_cross, title="Buy Signal", style=shape.triangleup,
                      location=location.belowbar, color=color.green, size=size.small, text="BUY")
            plotshape(bear_cross, title="Sell Signal", style=shape.triangledown,
                      location=location.abovebar, color=color.red, size=size.small, text="SELL")
        """)

    @staticmethod
    def _rsi_indicator(params: Dict[str, Any]) -> str:
        period = params.get("period", 14)
        ob = params.get("overbought", 70)
        os_ = params.get("oversold", 30)
        return textwrap.dedent(f"""\
            rsi_len = input.int({period}, "RSI Period")
            ob_level = input.int({ob}, "Overbought")
            os_level = input.int({os_}, "Oversold")

            rsi_val = ta.rsi(close, rsi_len)

            plot(rsi_val, "RSI", color=color.purple, linewidth=2)
            hline(ob_level, "Overbought", color=color.red, linestyle=hline.style_dashed)
            hline(os_level, "Oversold", color=color.green, linestyle=hline.style_dashed)
            hline(50, "Midline", color=color.gray, linestyle=hline.style_dotted)

            bgcolor(rsi_val > ob_level ? color.new(color.red, 90) : na)
            bgcolor(rsi_val < os_level ? color.new(color.green, 90) : na)
        """)

    @staticmethod
    def _macd_indicator(params: Dict[str, Any]) -> str:
        fast = params.get("fast_period", 12)
        slow = params.get("slow_period", 26)
        signal = params.get("signal_period", 9)
        return textwrap.dedent(f"""\
            fast_len   = input.int({fast}, "Fast Length")
            slow_len   = input.int({slow}, "Slow Length")
            signal_len = input.int({signal}, "Signal Length")

            [macd_line, signal_line, hist] = ta.macd(close, fast_len, slow_len, signal_len)

            plot(macd_line, "MACD", color=color.blue, linewidth=2)
            plot(signal_line, "Signal", color=color.orange, linewidth=2)
            plot(hist, "Histogram", style=plot.style_histogram,
                 color=hist >= 0 ? color.new(color.green, 40) : color.new(color.red, 40))
            hline(0, "Zero", color=color.gray, linestyle=hline.style_dotted)
        """)

    @staticmethod
    def _bollinger_indicator(params: Dict[str, Any]) -> str:
        period = params.get("period", 20)
        mult = params.get("multiplier", 2.0)
        return textwrap.dedent(f"""\
            bb_len  = input.int({period}, "BB Period")
            bb_mult = input.float({mult}, "BB Multiplier")

            basis = ta.sma(close, bb_len)
            dev   = bb_mult * ta.stdev(close, bb_len)
            upper = basis + dev
            lower = basis - dev

            plot(basis, "Basis", color=color.gray)
            p_upper = plot(upper, "Upper Band", color=color.blue)
            p_lower = plot(lower, "Lower Band", color=color.blue)
            fill(p_upper, p_lower, color=color.new(color.blue, 92), title="BB Fill")
        """)

    @staticmethod
    def _stochastic_indicator(params: Dict[str, Any]) -> str:
        k_period = params.get("k_period", 14)
        d_period = params.get("d_period", 3)
        smooth = params.get("smooth", 3)
        return textwrap.dedent(f"""\
            k_len = input.int({k_period}, "K Period")
            d_len = input.int({d_period}, "D Period")
            smooth = input.int({smooth}, "Smooth")

            k = ta.sma(ta.stoch(close, high, low, k_len), smooth)
            d = ta.sma(k, d_len)

            plot(k, "K", color=color.blue, linewidth=2)
            plot(d, "D", color=color.orange, linewidth=2)
            hline(80, "Overbought", color=color.red, linestyle=hline.style_dashed)
            hline(20, "Oversold", color=color.green, linestyle=hline.style_dashed)
        """)

    @staticmethod
    def _atr_indicator(params: Dict[str, Any]) -> str:
        period = params.get("period", 14)
        return textwrap.dedent(f"""\
            atr_len = input.int({period}, "ATR Period")
            atr_val = ta.atr(atr_len)

            plot(atr_val, "ATR", color=color.orange, linewidth=2)

            sl_mult = input.float(1.5, "SL Multiplier")
            tp_mult = input.float(2.0, "TP Multiplier")

            plot(close - atr_val * sl_mult, "SL Level", color=color.red,
                 style=plot.style_stepline, linewidth=1)
            plot(close + atr_val * tp_mult, "TP Level", color=color.green,
                 style=plot.style_stepline, linewidth=1)
        """)

    @staticmethod
    def _custom_indicator(params: Dict[str, Any]) -> str:
        source = params.get("source", "close")
        return textwrap.dedent(f"""\
            // Custom indicator stub — extend as needed
            src = input.source({source}, "Source")
            plot(src, "Custom", color=color.purple)
        """)

    # ── Private: strategy bodies ─────────────────────────────────────

    @staticmethod
    def _ma_crossover_strategy(params: Dict[str, Any]) -> str:
        fast = params.get("fast_period", 9)
        slow = params.get("slow_period", 21)
        sl_pips = params.get("sl_pips", 30)
        tp_pips = params.get("tp_pips", 60)
        pip = params.get("pip_value", 0.0001)
        return textwrap.dedent(f"""\
            fast_len = input.int({fast}, "Fast Period")
            slow_len = input.int({slow}, "Slow Period")
            sl_pips  = input.float({sl_pips}, "SL Pips")
            tp_pips  = input.float({tp_pips}, "TP Pips")
            pip      = {pip}

            fast_ma = ta.ema(close, fast_len)
            slow_ma = ta.ema(close, slow_len)

            long_cond  = ta.crossover(fast_ma, slow_ma)
            short_cond = ta.crossunder(fast_ma, slow_ma)

            if long_cond
                strategy.entry("Long", strategy.long)
                strategy.exit("Long Exit", "Long",
                              stop=close - sl_pips * pip,
                              limit=close + tp_pips * pip)

            if short_cond
                strategy.entry("Short", strategy.short)
                strategy.exit("Short Exit", "Short",
                              stop=close + sl_pips * pip,
                              limit=close - tp_pips * pip)

            plot(fast_ma, "Fast MA", color=color.blue)
            plot(slow_ma, "Slow MA", color=color.red)
        """)

    @staticmethod
    def _rsi_reversal_strategy(params: Dict[str, Any]) -> str:
        period = params.get("period", 14)
        ob = params.get("overbought", 70)
        os_ = params.get("oversold", 30)
        sl_pips = params.get("sl_pips", 25)
        tp_pips = params.get("tp_pips", 50)
        pip = params.get("pip_value", 0.0001)
        return textwrap.dedent(f"""\
            rsi_len  = input.int({period}, "RSI Period")
            ob_level = input.int({ob}, "Overbought")
            os_level = input.int({os_}, "Oversold")
            sl_pips  = input.float({sl_pips}, "SL Pips")
            tp_pips  = input.float({tp_pips}, "TP Pips")
            pip      = {pip}

            rsi_val = ta.rsi(close, rsi_len)

            long_cond  = ta.crossover(rsi_val, os_level)
            short_cond = ta.crossunder(rsi_val, ob_level)

            if long_cond
                strategy.entry("Long", strategy.long)
                strategy.exit("Long TP/SL", "Long",
                              stop=close - sl_pips * pip,
                              limit=close + tp_pips * pip)

            if short_cond
                strategy.entry("Short", strategy.short)
                strategy.exit("Short TP/SL", "Short",
                              stop=close + sl_pips * pip,
                              limit=close - tp_pips * pip)
        """)

    @staticmethod
    def _breakout_strategy(params: Dict[str, Any]) -> str:
        lookback = params.get("lookback", 20)
        sl_pips = params.get("sl_pips", 30)
        tp_pips = params.get("tp_pips", 60)
        pip = params.get("pip_value", 0.0001)
        return textwrap.dedent(f"""\
            lookback = input.int({lookback}, "Lookback Period")
            sl_pips  = input.float({sl_pips}, "SL Pips")
            tp_pips  = input.float({tp_pips}, "TP Pips")
            pip      = {pip}

            highest_high = ta.highest(high, lookback)
            lowest_low   = ta.lowest(low, lookback)

            long_cond  = ta.crossover(close, highest_high[1])
            short_cond = ta.crossunder(close, lowest_low[1])

            if long_cond
                strategy.entry("Breakout Long", strategy.long)
                strategy.exit("Long Exit", "Breakout Long",
                              stop=close - sl_pips * pip,
                              limit=close + tp_pips * pip)

            if short_cond
                strategy.entry("Breakout Short", strategy.short)
                strategy.exit("Short Exit", "Breakout Short",
                              stop=close + sl_pips * pip,
                              limit=close - tp_pips * pip)

            plot(highest_high, "Resistance", color=color.red, linewidth=1)
            plot(lowest_low, "Support", color=color.green, linewidth=1)
        """)

    @staticmethod
    def _custom_strategy(params: Dict[str, Any]) -> str:
        return textwrap.dedent("""\
            // Custom strategy stub — extend as needed
            if ta.crossover(ta.ema(close, 9), ta.ema(close, 21))
                strategy.entry("Long", strategy.long)
            if ta.crossunder(ta.ema(close, 9), ta.ema(close, 21))
                strategy.entry("Short", strategy.short)
        """)

    # ── Utilities ────────────────────────────────────────────────────

    @staticmethod
    def _script_header(name: str, overlay: bool = True) -> str:
        return (
            f'//@version=5\n'
            f'indicator("{name}", overlay={str(overlay).lower()})'
        )
