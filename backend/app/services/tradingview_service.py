import hashlib
import hmac
import json
import re
import textwrap
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger


# ---------------------------------------------------------------------------
# Canonical alert message patterns
# ---------------------------------------------------------------------------
# Supported formats:
#   "EURUSD BUY @ 1.0850 SL=1.0820 TP=1.0900"
#   "EURUSD SELL 1.0850 SL:1.0820 TP:1.0900"
#   "BUY EURUSD @ 1.0850 SL=1.0820 TP=1.0900"
#   JSON payload: {"symbol":"EURUSD","action":"buy","price":1.0850,...}
_ALERT_PATTERN = re.compile(
    r"""
    (?:(?P<sym1>[A-Z]{3,10})\s+)?        # optional symbol before action
    (?P<action>BUY|SELL|LONG|SHORT|CLOSE)  # required action
    \s+
    (?:(?P<sym2>[A-Z]{3,10})\s+)?        # optional symbol after action
    (?:@\s*)?                             # optional @ separator
    (?P<price>\d+\.?\d*)                  # entry price
    (?:.*?(?:SL[=:]\s*(?P<sl>\d+\.?\d*)))?  # optional SL
    (?:.*?(?:TP[=:]\s*(?P<tp>\d+\.?\d*)))?  # optional TP
    """,
    re.IGNORECASE | re.VERBOSE,
)


class TradingViewService:
    """
    Handles TradingView webhook alerts, signal parsing, history tracking,
    and Pine Script generation for the JARVIS trading system.
    """

    def __init__(self) -> None:
        self._signal_history: List[Dict] = []
        self._max_history: int = 10_000

    # ------------------------------------------------------------------
    # Webhook processing
    # ------------------------------------------------------------------

    async def process_webhook(self, payload: Dict, secret: str) -> Dict:
        """
        Validate and parse an incoming TradingView webhook payload.

        The payload can be either a structured JSON dict or contain a plain
        text "message" field.  The `secret` is compared against an HMAC-SHA256
        signature expected in `payload["signature"]` (if present).

        Returns a normalised signal dict:
            {symbol, action, price, sl, tp, strategy, timeframe, timestamp}
        """
        # --- Signature validation (optional but enforced if key provided) ---
        raw_signature = payload.get("signature", "")
        payload_copy = {k: v for k, v in payload.items() if k != "signature"}
        payload_str = json.dumps(payload_copy, separators=(",", ":"), sort_keys=True)

        if secret and raw_signature:
            valid = await self.validate_webhook_secret(payload_str, raw_signature, secret)
            if not valid:
                logger.warning("Webhook signature validation FAILED.")
                raise ValueError("Invalid webhook signature.")
        elif secret and not raw_signature:
            logger.warning("No signature present in webhook; proceeding without validation.")

        # --- Parse the signal ---
        signal: Optional[Dict] = None

        # Case 1: Fully structured JSON payload
        if "symbol" in payload and "action" in payload:
            signal = self._parse_structured_payload(payload)

        # Case 2: Plain-text message field
        elif "message" in payload:
            signal = self.parse_alert_message(payload["message"])
            if signal:
                signal["strategy"] = payload.get("strategy", "TradingView")
                signal["timeframe"] = payload.get("timeframe", "")

        if signal is None:
            raise ValueError(f"Could not parse TradingView payload: {payload}")

        signal["timestamp"] = datetime.utcnow().isoformat()
        self._store_signal(signal)
        logger.info(
            f"Webhook signal processed: {signal['action']} {signal['symbol']} "
            f"@ {signal['price']}"
        )
        return signal

    def _parse_structured_payload(self, payload: Dict) -> Dict:
        """Parse a fully structured TradingView JSON payload."""
        action = str(payload.get("action", "")).upper()
        # Normalise LONG/SHORT aliases
        action = {"LONG": "BUY", "SHORT": "SELL"}.get(action, action)

        return {
            "symbol": str(payload.get("symbol", "")).upper(),
            "action": action,
            "price": float(payload.get("price", 0.0)),
            "sl": float(payload.get("sl", payload.get("stop_loss", 0.0))),
            "tp": float(payload.get("tp", payload.get("take_profit", 0.0))),
            "strategy": str(payload.get("strategy", payload.get("strategy_name", "TV"))),
            "timeframe": str(payload.get("timeframe", payload.get("interval", ""))),
            "volume": float(payload.get("volume", payload.get("qty", 0.0))),
            "comment": str(payload.get("comment", "")),
        }

    # ------------------------------------------------------------------
    # Webhook signature validation
    # ------------------------------------------------------------------

    async def validate_webhook_secret(
        self, payload_str: str, signature: str, secret: str
    ) -> bool:
        """
        Validate HMAC-SHA256 signature of the raw payload string.

        Args:
            payload_str: JSON-serialised payload (without the signature field).
            signature: Hex-encoded HMAC signature from the request.
            secret: Shared secret configured in TradingView alert.

        Returns:
            True if signature matches.
        """
        expected = hmac.new(
            secret.encode("utf-8"),
            payload_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        match = hmac.compare_digest(expected.lower(), signature.lower())
        if not match:
            logger.debug(
                f"HMAC mismatch: expected={expected[:12]}… got={signature[:12]}…"
            )
        return match

    # ------------------------------------------------------------------
    # Alert message parser
    # ------------------------------------------------------------------

    def parse_alert_message(self, message: str) -> Optional[Dict]:
        """
        Parse a plain-text TradingView alert message into a structured signal.

        Supported formats:
            "EURUSD BUY @ 1.0850 SL=1.0820 TP=1.0900"
            "BUY EURUSD 1.0850 SL:1.0820 TP:1.0900"
            "EURUSD SELL 1.0850"
            JSON string (auto-detected)

        Returns None if the message cannot be parsed.
        """
        message = message.strip()

        # Attempt JSON first
        if message.startswith("{"):
            try:
                data = json.loads(message)
                if "symbol" in data and "action" in data:
                    return self._parse_structured_payload(data)
            except json.JSONDecodeError:
                pass

        # Regex pattern match
        m = _ALERT_PATTERN.match(message.upper())
        if not m:
            logger.warning(f"parse_alert_message: no match for: {message!r}")
            return None

        symbol = (m.group("sym1") or m.group("sym2") or "").upper()
        action = m.group("action").upper()
        action = {"LONG": "BUY", "SHORT": "SELL"}.get(action, action)
        price = float(m.group("price") or 0)
        sl = float(m.group("sl") or 0)
        tp = float(m.group("tp") or 0)

        if not symbol:
            logger.warning("parse_alert_message: symbol could not be determined.")
            return None

        return {
            "symbol": symbol,
            "action": action,
            "price": price,
            "sl": sl,
            "tp": tp,
            "strategy": "TradingView",
            "timeframe": "",
        }

    # ------------------------------------------------------------------
    # Signal history
    # ------------------------------------------------------------------

    def _store_signal(self, signal: Dict) -> None:
        """Store a parsed signal in the in-memory history (bounded)."""
        self._signal_history.append(signal)
        if len(self._signal_history) > self._max_history:
            self._signal_history = self._signal_history[-self._max_history:]

    async def get_signal_history(
        self, symbol: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        """
        Retrieve recent signal history, optionally filtered by symbol.

        Args:
            symbol: If provided, filter to signals for this symbol only.
            limit: Maximum number of records to return (most-recent first).

        Returns:
            List of signal dicts in reverse-chronological order.
        """
        history = self._signal_history
        if symbol:
            history = [s for s in history if s.get("symbol", "").upper() == symbol.upper()]
        return list(reversed(history[-limit:]))

    def clear_history(self) -> None:
        """Clear the in-memory signal history."""
        self._signal_history.clear()
        logger.info("Signal history cleared.")

    # ------------------------------------------------------------------
    # Pine Script v5 generation
    # ------------------------------------------------------------------

    async def generate_pine_script(
        self, strategy_name: str, params: Dict
    ) -> str:
        """
        Generate a complete Pine Script v5 strategy.

        Args:
            strategy_name: Display name for the strategy.
            params: Configuration dict with keys:
                strategy_type (str): e.g. "trend", "mean-reversion", "breakout".
                indicators (List[str]): e.g. ["EMA(20)", "RSI(14)"].
                timeframe (str): e.g. "60" (minutes) or "D".
                risk_percent (float): 1-100.
                commission_pct (float): Commission per trade.
                initial_capital (float): Starting capital for backtest.
                long_only (bool): Whether to enable long-only mode.
                extra (str): Free-form extra requirements.

        Returns:
            Complete Pine Script v5 code as a string.
        """
        strategy_type = params.get("strategy_type", "trend")
        indicators = params.get("indicators", ["EMA(20)", "EMA(50)"])
        risk_pct = params.get("risk_percent", 2.0)
        commission = params.get("commission_pct", 0.05)
        initial_capital = params.get("initial_capital", 10000)
        long_only = params.get("long_only", False)
        timeframe = params.get("timeframe", "")
        extra = params.get("extra", "")

        # Build the script from known components for the most common strategy types
        if strategy_type == "trend":
            script = self._pine_trend_strategy(
                strategy_name, indicators, risk_pct, commission,
                initial_capital, long_only, timeframe, extra
            )
        elif strategy_type == "mean-reversion":
            script = self._pine_mean_reversion_strategy(
                strategy_name, indicators, risk_pct, commission,
                initial_capital, long_only, timeframe, extra
            )
        elif strategy_type == "breakout":
            script = self._pine_breakout_strategy(
                strategy_name, indicators, risk_pct, commission,
                initial_capital, long_only, timeframe, extra
            )
        else:
            # Generic template
            script = self._pine_generic_strategy(
                strategy_name, strategy_type, indicators, risk_pct,
                commission, initial_capital, long_only, timeframe, extra
            )

        logger.info(f"Generated Pine Script v5: '{strategy_name}' ({len(script)} chars)")
        return script

    # ------------------------------------------------------------------
    # Pine Script builders
    # ------------------------------------------------------------------

    def _pine_header(
        self, strategy_name: str, commission: float, initial_capital: float, long_only: bool
    ) -> str:
        direction = "strategy.direction.long" if long_only else "strategy.direction.all"
        return textwrap.dedent(
            f"""\
            //@version=5
            // ──────────────────────────────────────────────────────────────────────
            // {strategy_name}
            // Generated by JARVIS AI Trading OS
            // ──────────────────────────────────────────────────────────────────────
            strategy(
                title           = "{strategy_name}",
                shorttitle      = "{strategy_name[:10]}",
                overlay         = true,
                initial_capital = {initial_capital},
                default_qty_type = strategy.percent_of_equity,
                default_qty_value = 100,
                commission_type = strategy.commission.percent,
                commission_value = {commission},
                direction       = {direction},
                pyramiding      = 0
            )
            """
        )

    def _pine_risk_block(self, risk_pct: float) -> str:
        return textwrap.dedent(
            f"""\
            // ── Risk Management ──────────────────────────────────────────────────
            riskPct     = input.float({risk_pct}, "Risk % per Trade", minval=0.1, maxval=10, step=0.1)
            slMultiplier = input.float(1.5, "ATR Stop-Loss Multiplier",  minval=0.5, step=0.1)
            tpMultiplier = input.float(3.0, "ATR Take-Profit Multiplier", minval=1.0, step=0.1)
            atrLen       = input.int(14, "ATR Length", minval=1)
            atrValue     = ta.atr(atrLen)

            float slDistance = slMultiplier * atrValue
            float tpDistance = tpMultiplier * atrValue
            """
        )

    def _pine_trend_strategy(
        self, name, indicators, risk_pct, commission,
        initial_capital, long_only, timeframe, extra
    ) -> str:
        header = self._pine_header(name, commission, initial_capital, long_only)
        risk_block = self._pine_risk_block(risk_pct)

        body = textwrap.dedent(
            """\
            // ── Indicator Inputs ─────────────────────────────────────────────────
            fastLen  = input.int(20,  "Fast EMA Length", minval=1)
            slowLen  = input.int(50,  "Slow EMA Length", minval=1)
            rsiLen   = input.int(14,  "RSI Length",      minval=1)
            rsiOB    = input.int(70,  "RSI Overbought",  minval=50, maxval=100)
            rsiOS    = input.int(30,  "RSI Oversold",    minval=0,  maxval=50)

            fastEMA  = ta.ema(close, fastLen)
            slowEMA  = ta.ema(close, slowLen)
            rsiValue = ta.rsi(close, rsiLen)

            // ── Plots ────────────────────────────────────────────────────────────
            plot(fastEMA, "Fast EMA", color=color.new(color.blue,  0), linewidth=2)
            plot(slowEMA, "Slow EMA", color=color.new(color.orange, 0), linewidth=2)

            // ── Entry Conditions ─────────────────────────────────────────────────
            bullCross = ta.crossover(fastEMA, slowEMA)
            bearCross = ta.crossunder(fastEMA, slowEMA)

            longCondition  = bullCross and rsiValue < rsiOB and rsiValue > 50
            shortCondition = bearCross and rsiValue > rsiOS and rsiValue < 50

            // ── Execution ────────────────────────────────────────────────────────
            if longCondition
                strategy.entry("Long", strategy.long)
                strategy.exit("Long SL/TP", "Long",
                              stop  = close - slDistance,
                              limit = close + tpDistance,
                              comment = "EMA Cross Long")

            if shortCondition and not strategy.direction == strategy.direction.long
                strategy.entry("Short", strategy.short)
                strategy.exit("Short SL/TP", "Short",
                              stop  = close + slDistance,
                              limit = close - tpDistance,
                              comment = "EMA Cross Short")

            // ── Background Colour ─────────────────────────────────────────────
            bgcolor(fastEMA > slowEMA ? color.new(color.green, 92) : color.new(color.red, 92))
            """
        )
        return header + "\n" + risk_block + "\n" + body

    def _pine_mean_reversion_strategy(
        self, name, indicators, risk_pct, commission,
        initial_capital, long_only, timeframe, extra
    ) -> str:
        header = self._pine_header(name, commission, initial_capital, long_only)
        risk_block = self._pine_risk_block(risk_pct)

        body = textwrap.dedent(
            """\
            // ── Indicator Inputs ─────────────────────────────────────────────────
            bbLen   = input.int(20, "BB Length", minval=1)
            bbMult  = input.float(2.0, "BB Std Dev Multiplier", step=0.1)
            rsiLen  = input.int(14, "RSI Length", minval=1)

            [bbMid, bbUpper, bbLower] = ta.bb(close, bbLen, bbMult)
            rsiValue = ta.rsi(close, rsiLen)

            // ── Plots ────────────────────────────────────────────────────────────
            plot(bbMid,   "BB Mid",   color=color.gray)
            plot(bbUpper, "BB Upper", color=color.red)
            plot(bbLower, "BB Lower", color=color.green)

            // ── Entry Conditions ─────────────────────────────────────────────────
            longCondition  = close < bbLower and rsiValue < 35
            shortCondition = close > bbUpper and rsiValue > 65

            // ── Execution ────────────────────────────────────────────────────────
            if longCondition
                strategy.entry("Long", strategy.long)
                strategy.exit("Long TP", "Long",
                              stop  = close - slDistance,
                              limit = bbMid,
                              comment = "BB Reversion Long")

            if shortCondition and not strategy.direction == strategy.direction.long
                strategy.entry("Short", strategy.short)
                strategy.exit("Short TP", "Short",
                              stop  = close + slDistance,
                              limit = bbMid,
                              comment = "BB Reversion Short")
            """
        )
        return header + "\n" + risk_block + "\n" + body

    def _pine_breakout_strategy(
        self, name, indicators, risk_pct, commission,
        initial_capital, long_only, timeframe, extra
    ) -> str:
        header = self._pine_header(name, commission, initial_capital, long_only)
        risk_block = self._pine_risk_block(risk_pct)

        body = textwrap.dedent(
            """\
            // ── Indicator Inputs ─────────────────────────────────────────────────
            lookback    = input.int(20,  "Donchian Channel Length", minval=5)
            volFilterOn = input.bool(true, "Volume Filter")
            volMultiple = input.float(1.5, "Volume Multiplier (vs avg)", step=0.1)

            donchUpper = ta.highest(high, lookback)
            donchLower = ta.lowest(low,   lookback)
            avgVol     = ta.sma(volume, lookback)

            // ── Plots ────────────────────────────────────────────────────────────
            plot(donchUpper, "Donchian Upper", color=color.blue,  style=plot.style_stepline)
            plot(donchLower, "Donchian Lower", color=color.orange, style=plot.style_stepline)

            // ── Entry Conditions ─────────────────────────────────────────────────
            volOk         = volFilterOn ? volume > avgVol * volMultiple : true
            longCondition  = ta.crossover(close, donchUpper[1]) and volOk
            shortCondition = ta.crossunder(close, donchLower[1]) and volOk

            // ── Execution ────────────────────────────────────────────────────────
            if longCondition
                strategy.entry("Long", strategy.long)
                strategy.exit("Long SL/TP", "Long",
                              stop  = donchLower,
                              limit = close + tpDistance,
                              comment = "Donchian Breakout Long")

            if shortCondition and not strategy.direction == strategy.direction.long
                strategy.entry("Short", strategy.short)
                strategy.exit("Short SL/TP", "Short",
                              stop  = donchUpper,
                              limit = close - tpDistance,
                              comment = "Donchian Breakout Short")
            """
        )
        return header + "\n" + risk_block + "\n" + body

    def _pine_generic_strategy(
        self, name, strategy_type, indicators, risk_pct,
        commission, initial_capital, long_only, timeframe, extra
    ) -> str:
        header = self._pine_header(name, commission, initial_capital, long_only)
        risk_block = self._pine_risk_block(risk_pct)

        indicator_lines = "\n".join(
            f"// TODO: Implement {ind}" for ind in indicators
        )

        body = textwrap.dedent(
            f"""\
            // ── Strategy Type: {strategy_type} ────────────────────────────────────
            // Indicators requested: {', '.join(indicators)}
            // Extra notes: {extra or 'None'}
            //
            {indicator_lines}

            // ── Entry Conditions (customise below) ──────────────────────────────
            longCondition  = false // Define your long entry here
            shortCondition = false // Define your short entry here

            if longCondition
                strategy.entry("Long", strategy.long)
                strategy.exit("Long SL/TP", "Long",
                              stop  = close - slDistance,
                              limit = close + tpDistance)

            if shortCondition and not strategy.direction == strategy.direction.long
                strategy.entry("Short", strategy.short)
                strategy.exit("Short SL/TP", "Short",
                              stop  = close + slDistance,
                              limit = close - tpDistance)
            """
        )
        return header + "\n" + risk_block + "\n" + body

    # ------------------------------------------------------------------
    # Alert string formatter (for configuring TradingView alerts)
    # ------------------------------------------------------------------

    def build_alert_template(
        self, symbol: str, action: str, strategy: str = "JARVIS"
    ) -> str:
        """
        Return a TradingView alert message template to paste into the alert dialog.

        The {{close}}, {{high}}, {{low}} placeholders are filled by TradingView.
        """
        return (
            f"{symbol} {action.upper()} @ {{{{close}}}} "
            f"SL={{{{low if action == 'BUY' else high}}}} "
            f"TP={{{{close + (close - low) * 2 if action == 'BUY' else close - (high - close) * 2}}}} "
            f"strategy={strategy}"
        )
