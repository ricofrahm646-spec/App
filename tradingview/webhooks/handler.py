"""
JARVIS TradingView Webhook Handler.

Receives, validates, and processes incoming TradingView alert webhooks,
mapping them to normalised trading actions for downstream consumption.
"""

import hashlib
import hmac
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Recognised forex pairs (majors, minors, and common exotics)
FOREX_PAIRS: set[str] = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
    "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD",
    "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD",
    "AUDJPY", "AUDCHF", "AUDCAD", "AUDNZD",
    "CADJPY", "CADCHF", "NZDJPY", "NZDCHF", "CHFJPY",
    "USDSEK", "USDNOK", "USDDKK", "USDSGD", "USDHKD", "USDMXN",
    "USDTRY", "USDZAR", "USDPLN", "USDHUF", "USDCZK",
}

VALID_ACTIONS = {"BUY", "SELL", "CLOSE", "CLOSE_BUY", "CLOSE_SELL"}


class AlertValidationError(Exception):
    """Raised when an incoming alert fails validation."""


class WebhookHandler:
    """Process and validate incoming TradingView webhook alerts."""

    def __init__(
        self,
        webhook_secret: Optional[str] = None,
        forex_only: bool = True,
        allowed_sources: Optional[List[str]] = None,
    ) -> None:
        """
        Args:
            webhook_secret: HMAC secret for verifying alert authenticity.
            forex_only: When True, reject alerts for non-forex symbols.
            allowed_sources: Optional whitelist of alert source names.
        """
        self._webhook_secret = webhook_secret
        self._forex_only = forex_only
        self._allowed_sources = set(allowed_sources) if allowed_sources else None
        self._alert_history: List[Dict[str, Any]] = []

    # ── Public API ───────────────────────────────────────────────────

    def process_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming TradingView alert.

        Accepts multiple common alert JSON formats and normalises them
        into a consistent internal structure.

        Args:
            alert_data: Raw alert payload (already deserialised from JSON).

        Returns:
            Normalised alert dict with keys:
                symbol, action, price, sl, tp, source, raw, timestamp
        """
        logger.info("Processing incoming alert: %s", alert_data)

        parsed = self._parse_alert(alert_data)
        self._validate_alert(parsed)
        action = self._map_action(parsed)

        result: Dict[str, Any] = {
            "symbol": parsed["symbol"],
            "action": action,
            "price": parsed.get("price"),
            "sl": parsed.get("sl"),
            "tp": parsed.get("tp"),
            "source": parsed.get("source", "tradingview"),
            "raw": alert_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self._log_alert(result)
        return result

    def verify_signature(
        self, payload_body: bytes, signature: str
    ) -> bool:
        """Verify HMAC-SHA256 signature of the raw webhook body.

        Args:
            payload_body: Raw bytes of the request body.
            signature: Hex-encoded HMAC signature from the request header.

        Returns:
            True if the signature is valid.
        """
        if not self._webhook_secret:
            logger.warning("No webhook secret configured — skipping verification")
            return True

        expected = hmac.new(
            self._webhook_secret.encode(),
            payload_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    @property
    def alert_history(self) -> List[Dict[str, Any]]:
        """Return a copy of the processed alert history."""
        return list(self._alert_history)

    # ── Parsing ──────────────────────────────────────────────────────

    def _parse_alert(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalise multiple TradingView alert formats into one schema.

        Supported formats:
          1. Standard:  { "symbol": "...", "action": "...", ... }
          2. Flat text:  { "text": "BUY EURUSD @ 1.12345 SL 1.12000 TP 1.13000" }
          3. TradingView strategy: { "ticker": "...", "strategy": { "order_action": "..." } }
        """
        if "strategy" in data and isinstance(data["strategy"], dict):
            return self._parse_strategy_format(data)
        if "text" in data and isinstance(data["text"], str):
            return self._parse_text_format(data["text"], data)
        return self._parse_standard_format(data)

    def _parse_standard_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        symbol = self._normalise_symbol(
            data.get("symbol") or data.get("ticker") or ""
        )
        action = (data.get("action") or data.get("order") or "").upper().strip()
        price = self._to_float(data.get("price") or data.get("close"))
        sl = self._to_float(data.get("sl") or data.get("stop_loss") or data.get("stoploss"))
        tp = self._to_float(data.get("tp") or data.get("take_profit") or data.get("takeprofit"))
        source = data.get("source", "tradingview")

        return {
            "symbol": symbol,
            "action": action,
            "price": price,
            "sl": sl,
            "tp": tp,
            "source": source,
        }

    def _parse_strategy_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        strategy = data["strategy"]
        symbol = self._normalise_symbol(data.get("ticker") or data.get("symbol") or "")
        action = (strategy.get("order_action") or "").upper().strip()
        price = self._to_float(strategy.get("order_price") or data.get("close"))
        return {
            "symbol": symbol,
            "action": action,
            "price": price,
            "sl": None,
            "tp": None,
            "source": "tradingview_strategy",
        }

    _TEXT_PATTERN = re.compile(
        r"(?P<action>BUY|SELL|CLOSE)\s+"
        r"(?P<symbol>[A-Z]{6})"
        r"(?:\s+@\s*(?P<price>[\d.]+))?"
        r"(?:\s+SL\s*(?P<sl>[\d.]+))?"
        r"(?:\s+TP\s*(?P<tp>[\d.]+))?",
        re.IGNORECASE,
    )

    def _parse_text_format(
        self, text: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        match = self._TEXT_PATTERN.search(text)
        if not match:
            raise AlertValidationError(f"Cannot parse alert text: {text!r}")

        return {
            "symbol": self._normalise_symbol(match.group("symbol")),
            "action": match.group("action").upper(),
            "price": self._to_float(match.group("price")),
            "sl": self._to_float(match.group("sl")),
            "tp": self._to_float(match.group("tp")),
            "source": data.get("source", "tradingview"),
        }

    # ── Validation ───────────────────────────────────────────────────

    def _validate_alert(self, parsed: Dict[str, Any]) -> None:
        if not parsed.get("symbol"):
            raise AlertValidationError("Missing symbol in alert")

        if not parsed.get("action"):
            raise AlertValidationError("Missing action in alert")

        if parsed["action"] not in VALID_ACTIONS:
            raise AlertValidationError(
                f"Invalid action '{parsed['action']}'. "
                f"Must be one of {VALID_ACTIONS}"
            )

        if self._forex_only and parsed["symbol"] not in FOREX_PAIRS:
            raise AlertValidationError(
                f"Symbol '{parsed['symbol']}' is not a recognised forex pair"
            )

        if self._allowed_sources and parsed.get("source") not in self._allowed_sources:
            raise AlertValidationError(
                f"Alert source '{parsed.get('source')}' is not in the allowed list"
            )

    # ── Action mapping ───────────────────────────────────────────────

    @staticmethod
    def _map_action(parsed: Dict[str, Any]) -> str:
        """Map the parsed action to a canonical trading action string."""
        action = parsed["action"]
        mapping = {
            "BUY": "BUY",
            "SELL": "SELL",
            "CLOSE": "CLOSE",
            "CLOSE_BUY": "CLOSE_BUY",
            "CLOSE_SELL": "CLOSE_SELL",
        }
        return mapping.get(action, action)

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _normalise_symbol(symbol: str) -> str:
        """Remove common exchange prefixes/suffixes and uppercases."""
        symbol = symbol.upper().strip()
        for prefix in ("FX:", "OANDA:", "FXCM:", "FOREX:"):
            if symbol.startswith(prefix):
                symbol = symbol[len(prefix):]
        for suffix in (".PRO", ".STD", "_SB"):
            if symbol.endswith(suffix):
                symbol = symbol[: -len(suffix)]
        return symbol

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _log_alert(self, alert: Dict[str, Any]) -> None:
        self._alert_history.append(alert)
        logger.info(
            "Alert processed — %s %s @ %s | SL=%s TP=%s",
            alert["action"],
            alert["symbol"],
            alert.get("price"),
            alert.get("sl"),
            alert.get("tp"),
        )
