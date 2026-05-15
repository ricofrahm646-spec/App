"""TradingView webhook handler for JARVIS AI Trading OS."""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Default TV → MT5 symbol map (extend as needed)
_DEFAULT_SYMBOL_MAP: Dict[str, str] = {
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "USDCHF": "USDCHF",
    "AUDUSD": "AUDUSD",
    "NZDUSD": "NZDUSD",
    "USDCAD": "USDCAD",
    "EURJPY": "EURJPY",
    "GBPJPY": "GBPJPY",
    "EURGBP": "EURGBP",
    "XAUUSD": "XAUUSD",
    "XAGUSD": "XAGUSD",
    "FX:EURUSD": "EURUSD",
    "FX:GBPUSD": "GBPUSD",
    "FX:USDJPY": "USDJPY",
    "OANDA:EURUSD": "EURUSD",
    "OANDA:GBPUSD": "GBPUSD",
    "OANDA:USDJPY": "USDJPY",
}

_VALID_ACTIONS = {"buy", "sell", "close", "close_buy", "close_sell"}


@dataclass(frozen=True)
class TradingSignal:
    """Normalised signal produced from a TradingView alert."""

    action: str  # buy | sell | close | close_buy | close_sell
    symbol: str
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    lot_size: Optional[float] = None
    timeframe: Optional[str] = None
    comment: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


class WebhookValidationError(Exception):
    """Raised when a webhook payload fails validation."""


class RateLimitExceeded(Exception):
    """Raised when the per-symbol rate limit is exceeded."""


class WebhookHandler:
    """Parse, validate, and convert TradingView alerts.

    Parameters
    ----------
    secret : str
        Shared secret used to authenticate incoming webhooks (HMAC-SHA256 or
        plain-text comparison, depending on *use_hmac*).
    symbol_map : dict | None
        TradingView symbol → MT5 symbol mapping.  Falls back to
        ``_DEFAULT_SYMBOL_MAP`` entries when *None*.
    use_hmac : bool
        If *True*, validate the ``X-Signature`` header via HMAC-SHA256.
        Otherwise compare the ``secret`` field inside the JSON body.
    rate_limit : int
        Maximum alerts per symbol per *rate_window* seconds.
    rate_window : int
        Sliding window duration in seconds for rate limiting.
    """

    def __init__(
        self,
        secret: str,
        symbol_map: Optional[Dict[str, str]] = None,
        use_hmac: bool = False,
        rate_limit: int = 10,
        rate_window: int = 60,
    ) -> None:
        self._secret = secret
        self._symbol_map: Dict[str, str] = {**_DEFAULT_SYMBOL_MAP}
        if symbol_map:
            self._symbol_map.update(symbol_map)
        self._use_hmac = use_hmac
        self._rate_limit = rate_limit
        self._rate_window = rate_window
        self._hit_log: Dict[str, List[float]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def handle(
        self,
        body: Dict[str, Any],
        raw_body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> TradingSignal:
        """Validate and convert an incoming alert to a :class:`TradingSignal`.

        Parameters
        ----------
        body : dict
            Parsed JSON body of the alert.
        raw_body : bytes | None
            The raw request body (needed for HMAC validation).
        headers : dict | None
            HTTP headers (needed for HMAC validation).
        """
        self._validate_secret(body, raw_body, headers)

        action = self._extract_action(body)
        symbol = self._resolve_symbol(body)
        self._enforce_rate_limit(symbol)

        return TradingSignal(
            action=action,
            symbol=symbol,
            price=self._float_or_none(body, "price"),
            sl=self._float_or_none(body, "sl"),
            tp=self._float_or_none(body, "tp"),
            lot_size=self._float_or_none(body, "lot_size"),
            timeframe=body.get("timeframe"),
            comment=body.get("comment"),
            raw=body,
        )

    def add_symbol_mapping(self, tv_symbol: str, mt5_symbol: str) -> None:
        self._symbol_map[tv_symbol] = mt5_symbol

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_secret(
        self,
        body: Dict[str, Any],
        raw_body: Optional[bytes],
        headers: Optional[Dict[str, str]],
    ) -> None:
        if self._use_hmac:
            if raw_body is None or headers is None:
                raise WebhookValidationError("HMAC validation requires raw_body and headers")
            signature = headers.get("X-Signature") or headers.get("x-signature", "")
            expected = hmac.new(
                self._secret.encode(), raw_body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise WebhookValidationError("Invalid HMAC signature")
        else:
            incoming_secret = body.get("secret", "")
            if incoming_secret != self._secret:
                raise WebhookValidationError("Invalid secret")

    @staticmethod
    def _extract_action(body: Dict[str, Any]) -> str:
        action = str(body.get("action", "")).strip().lower()
        if action not in _VALID_ACTIONS:
            raise WebhookValidationError(
                f"Invalid action '{action}'. Must be one of {_VALID_ACTIONS}"
            )
        return action

    def _resolve_symbol(self, body: Dict[str, Any]) -> str:
        raw = body.get("symbol") or body.get("ticker") or ""
        raw = raw.strip().upper()
        if not raw:
            raise WebhookValidationError("Missing 'symbol' or 'ticker' in payload")
        mapped = self._symbol_map.get(raw)
        if mapped:
            return mapped
        clean = raw.split(":")[-1] if ":" in raw else raw
        mapped = self._symbol_map.get(clean, clean)
        return mapped

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _enforce_rate_limit(self, symbol: str) -> None:
        now = time.monotonic()
        window_start = now - self._rate_window
        hits = self._hit_log[symbol]
        self._hit_log[symbol] = [t for t in hits if t > window_start]
        if len(self._hit_log[symbol]) >= self._rate_limit:
            raise RateLimitExceeded(
                f"Rate limit ({self._rate_limit}/{self._rate_window}s) "
                f"exceeded for {symbol}"
            )
        self._hit_log[symbol].append(now)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _float_or_none(body: Dict[str, Any], key: str) -> Optional[float]:
        val = body.get(key)
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
