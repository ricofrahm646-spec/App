"""
JARVIS Telegram Bot - Async trade notification and alerting system.

Sends formatted trade signals, risk warnings, and daily reports
via the Telegram Bot API with retry logic and rate limiting.
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import aiohttp

logger = logging.getLogger(__name__)

# Telegram rate limits: ~30 messages/second to different chats,
# ~1 message/second to the same chat
_RATE_LIMIT_INTERVAL = 1.1  # seconds between messages to same chat
_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0
_TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramBot:
    """Async Telegram bot for JARVIS trade notifications."""

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> None:
        self._token: Optional[str] = token
        self._chat_id: Optional[str] = chat_id
        self._last_send_time: float = 0.0
        self._session: Optional[aiohttp.ClientSession] = None
        self._send_lock = asyncio.Lock()

    # ── Configuration ────────────────────────────────────────────────

    def set_token(self, token: str) -> None:
        """Set the Telegram bot token."""
        self._token = token
        self._session = None  # force new session on next call

    def set_chat_id(self, chat_id: str) -> None:
        """Set the default chat ID for messages."""
        self._chat_id = chat_id

    @property
    def _api_url(self) -> str:
        if not self._token:
            raise ValueError("Telegram bot token not configured")
        return f"{_TELEGRAM_API_BASE}/bot{self._token}"

    # ── Session management ───────────────────────────────────────────

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ── Rate limiting ────────────────────────────────────────────────

    async def _wait_for_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_send_time
        if elapsed < _RATE_LIMIT_INTERVAL:
            await asyncio.sleep(_RATE_LIMIT_INTERVAL - elapsed)

    # ── Core send ────────────────────────────────────────────────────

    async def _send_request(
        self,
        method: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send a request to the Telegram Bot API with retry + rate limiting."""
        session = await self._get_session()
        url = f"{self._api_url}/{method}"

        last_error: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            async with self._send_lock:
                await self._wait_for_rate_limit()
                try:
                    async with session.post(url, json=payload) as resp:
                        self._last_send_time = time.monotonic()
                        data = await resp.json()

                        if resp.status == 429:
                            retry_after = data.get("parameters", {}).get(
                                "retry_after", attempt * _RETRY_BACKOFF_BASE
                            )
                            logger.warning(
                                "Rate limited by Telegram, retrying after %ss",
                                retry_after,
                            )
                            await asyncio.sleep(float(retry_after))
                            continue

                        if not data.get("ok"):
                            error_desc = data.get("description", "Unknown error")
                            logger.error(
                                "Telegram API error (attempt %d/%d): %s",
                                attempt,
                                _MAX_RETRIES,
                                error_desc,
                            )
                            last_error = RuntimeError(
                                f"Telegram API: {error_desc}"
                            )
                            if attempt < _MAX_RETRIES:
                                await asyncio.sleep(
                                    _RETRY_BACKOFF_BASE**attempt
                                )
                            continue

                        return data

                except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                    logger.error(
                        "Network error sending Telegram message "
                        "(attempt %d/%d): %s",
                        attempt,
                        _MAX_RETRIES,
                        exc,
                    )
                    last_error = exc
                    if attempt < _MAX_RETRIES:
                        await asyncio.sleep(_RETRY_BACKOFF_BASE**attempt)

        raise last_error or RuntimeError("Failed to send Telegram message")

    # ── Generic message ──────────────────────────────────────────────

    async def send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "HTML",
        disable_preview: bool = True,
    ) -> Dict[str, Any]:
        """Send a generic text message."""
        target = chat_id or self._chat_id
        if not target:
            raise ValueError("No chat_id configured or provided")

        payload = {
            "chat_id": target,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }
        return await self._send_request("sendMessage", payload)

    # ── Trade signal ─────────────────────────────────────────────────

    async def send_signal(
        self,
        signal_type: str,
        symbol: str,
        price: float,
        sl: float,
        tp: float,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a buy/sell signal notification.

        Args:
            signal_type: "BUY" or "SELL".
            symbol: Trading pair, e.g. "EURUSD".
            price: Entry price.
            sl: Stop-loss price.
            tp: Take-profit price.
        """
        arrow = "\U0001f7e2" if signal_type.upper() == "BUY" else "\U0001f534"
        direction = signal_type.upper()

        sl_pips = abs(price - sl) * (10000 if "JPY" not in symbol else 100)
        tp_pips = abs(tp - price) * (10000 if "JPY" not in symbol else 100)
        rr = tp_pips / sl_pips if sl_pips else 0.0

        text = (
            f"{arrow} <b>SIGNAL: {direction} {symbol}</b>\n"
            f"{'━' * 28}\n"
            f"\U0001f4b0 Entry Price: <code>{price:.5f}</code>\n"
            f"\U0001f6d1 Stop Loss:   <code>{sl:.5f}</code> "
            f"({sl_pips:.1f} pips)\n"
            f"\U0001f3af Take Profit: <code>{tp:.5f}</code> "
            f"({tp_pips:.1f} pips)\n"
            f"\U0001f4ca R:R Ratio:   <b>{rr:.2f}</b>\n"
            f"{'━' * 28}\n"
            f"\U0001f552 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self.send_message(text, chat_id=chat_id)

    # ── Trade opened ─────────────────────────────────────────────────

    async def send_trade_opened(
        self,
        symbol: str,
        direction: str,
        volume: float,
        price: float,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a trade-opened notification."""
        emoji = "\U0001f4c8" if direction.upper() == "BUY" else "\U0001f4c9"
        text = (
            f"{emoji} <b>TRADE OPENED</b>\n"
            f"{'━' * 28}\n"
            f"\U0001f4b1 Symbol:    <code>{symbol}</code>\n"
            f"\U000027a1 Direction: <b>{direction.upper()}</b>\n"
            f"\U0001f4e6 Volume:    <code>{volume:.2f}</code> lots\n"
            f"\U0001f4b0 Price:     <code>{price:.5f}</code>\n"
            f"{'━' * 28}\n"
            f"\U0001f552 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self.send_message(text, chat_id=chat_id)

    # ── Trade closed ─────────────────────────────────────────────────

    async def send_trade_closed(
        self,
        symbol: str,
        direction: str,
        profit: float,
        pips: float,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a trade-closed notification."""
        if profit >= 0:
            emoji = "\u2705"
            result = "PROFIT"
        else:
            emoji = "\u274c"
            result = "LOSS"

        text = (
            f"{emoji} <b>TRADE CLOSED — {result}</b>\n"
            f"{'━' * 28}\n"
            f"\U0001f4b1 Symbol:    <code>{symbol}</code>\n"
            f"\U000027a1 Direction: <b>{direction.upper()}</b>\n"
            f"\U0001f4b5 P&L:       <b>${profit:+.2f}</b>\n"
            f"\U0001f4cf Pips:      <b>{pips:+.1f}</b>\n"
            f"{'━' * 28}\n"
            f"\U0001f552 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self.send_message(text, chat_id=chat_id)

    # ── Risk warning ─────────────────────────────────────────────────

    async def send_risk_warning(
        self,
        message: str,
        severity: str = "MEDIUM",
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a risk warning alert.

        Args:
            message: Warning description.
            severity: LOW, MEDIUM, HIGH, or CRITICAL.
        """
        severity_icons = {
            "LOW": "\U0001f7e1",       # yellow circle
            "MEDIUM": "\U0001f7e0",    # orange circle
            "HIGH": "\u26a0\ufe0f",    # warning sign
            "CRITICAL": "\U0001f6a8",  # rotating light
        }
        icon = severity_icons.get(severity.upper(), "\u26a0\ufe0f")

        text = (
            f"{icon} <b>RISK WARNING — {severity.upper()}</b>\n"
            f"{'━' * 28}\n"
            f"{message}\n"
            f"{'━' * 28}\n"
            f"\U0001f552 {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self.send_message(text, chat_id=chat_id)

    # ── Daily report ─────────────────────────────────────────────────

    async def send_daily_report(
        self,
        stats: Dict[str, Any],
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a daily performance summary.

        Expected *stats* keys:
            total_trades, winning_trades, losing_trades,
            total_profit, total_pips, win_rate, balance,
            equity, max_drawdown, best_trade, worst_trade
        """
        total = stats.get("total_trades", 0)
        wins = stats.get("winning_trades", 0)
        losses = stats.get("losing_trades", 0)
        profit = stats.get("total_profit", 0.0)
        pips = stats.get("total_pips", 0.0)
        win_rate = stats.get("win_rate", 0.0)
        balance = stats.get("balance", 0.0)
        equity = stats.get("equity", 0.0)
        max_dd = stats.get("max_drawdown", 0.0)
        best = stats.get("best_trade", 0.0)
        worst = stats.get("worst_trade", 0.0)

        day_emoji = "\U0001f4c8" if profit >= 0 else "\U0001f4c9"

        text = (
            f"\U0001f4ca <b>DAILY REPORT</b> — "
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n"
            f"{'━' * 30}\n"
            f"\n"
            f"<b>Trading Activity</b>\n"
            f"  Total Trades: {total}\n"
            f"  \u2705 Wins:  {wins}  |  \u274c Losses: {losses}\n"
            f"  Win Rate:    <b>{win_rate:.1f}%</b>\n"
            f"\n"
            f"<b>Performance</b> {day_emoji}\n"
            f"  Total P&L:   <b>${profit:+.2f}</b>\n"
            f"  Total Pips:  <b>{pips:+.1f}</b>\n"
            f"  Best Trade:  ${best:+.2f}\n"
            f"  Worst Trade: ${worst:+.2f}\n"
            f"\n"
            f"<b>Account</b>\n"
            f"  Balance:     ${balance:,.2f}\n"
            f"  Equity:      ${equity:,.2f}\n"
            f"  Max DD:      {max_dd:.2f}%\n"
            f"{'━' * 30}\n"
            f"\U0001f916 <i>JARVIS AI Trading OS</i>"
        )
        return await self.send_message(text, chat_id=chat_id)

    # ── Connection test ──────────────────────────────────────────────

    async def test_connection(self) -> bool:
        """Test connectivity to the Telegram Bot API.

        Returns True if the bot token is valid and the API is reachable.
        """
        try:
            data = await self._send_request("getMe", {})
            bot_info = data.get("result", {})
            logger.info(
                "Telegram connection OK — bot: @%s",
                bot_info.get("username", "unknown"),
            )
            return True
        except Exception:
            logger.exception("Telegram connection test failed")
            return False

    # ── Context manager ──────────────────────────────────────────────

    async def __aenter__(self) -> "TelegramBot":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()
