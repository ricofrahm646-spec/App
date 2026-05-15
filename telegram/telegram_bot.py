"""Telegram notification service for JARVIS AI Trading OS."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY_S = 2.0
_TELEGRAM_API = "https://api.telegram.org"


@dataclass
class TradeNotification:
    """Structured payload for trade-related messages."""

    symbol: str
    direction: str  # "BUY" | "SELL"
    entry_price: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    lot_size: Optional[float] = None
    confidence: Optional[float] = None
    strategy: Optional[str] = None
    timeframe: Optional[str] = None


@dataclass
class DailySummary:
    """End-of-day performance summary."""

    date: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    net_pnl: float
    win_rate: float
    max_drawdown: float
    equity: float
    open_positions: int = 0


class TelegramNotifier:
    """Async Telegram bot for trade notifications.

    Parameters
    ----------
    bot_token : str
        Telegram Bot API token.
    chat_id : str | int
        Default chat / channel ID to send messages to.
    """

    def __init__(self, bot_token: str, chat_id: str | int) -> None:
        self._token = bot_token
        self._chat_id = str(chat_id)
        self._base_url = f"{_TELEGRAM_API}/bot{bot_token}"
        self._session: Optional[aiohttp.ClientSession] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------

    async def _send_message(
        self,
        text: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "Markdown",
        disable_notification: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self._base_url}/sendMessage"
        payload = {
            "chat_id": chat_id or self._chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }

        last_exc: Optional[Exception] = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                session = await self._get_session()
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    if resp.status == 200 and data.get("ok"):
                        return data
                    logger.warning(
                        "Telegram API error (attempt %d/%d): %s",
                        attempt, _MAX_RETRIES, data,
                    )
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                last_exc = exc
                logger.warning(
                    "Telegram send failed (attempt %d/%d): %s",
                    attempt, _MAX_RETRIES, exc,
                )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_RETRY_DELAY_S * attempt)

        logger.error("All %d Telegram send attempts failed", _MAX_RETRIES)
        if last_exc:
            raise last_exc
        return {}

    # ------------------------------------------------------------------
    # Trade signals
    # ------------------------------------------------------------------

    async def send_signal(self, signal: TradeNotification) -> Dict[str, Any]:
        emoji = "\U0001f7e2" if signal.direction == "BUY" else "\U0001f534"
        lines = [
            f"{emoji} *{signal.direction} Signal*",
            f"*Symbol:* `{signal.symbol}`",
            f"*Entry:* `{signal.entry_price:.5f}`",
        ]
        if signal.sl is not None:
            lines.append(f"*SL:* `{signal.sl:.5f}`")
        if signal.tp is not None:
            lines.append(f"*TP:* `{signal.tp:.5f}`")
        if signal.lot_size is not None:
            lines.append(f"*Lot:* `{signal.lot_size}`")
        if signal.confidence is not None:
            pct = signal.confidence * 100
            lines.append(f"*Confidence:* `{pct:.0f}%`")
        if signal.strategy:
            lines.append(f"*Strategy:* {signal.strategy}")
        if signal.timeframe:
            lines.append(f"*TF:* {signal.timeframe}")
        lines.append(f"\n\u23f0 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        return await self._send_message("\n".join(lines))

    # ------------------------------------------------------------------
    # Trade open / close
    # ------------------------------------------------------------------

    async def send_trade_opened(
        self, symbol: str, direction: str, price: float, lot: float
    ) -> Dict[str, Any]:
        emoji = "\U0001f4c8" if direction == "BUY" else "\U0001f4c9"
        text = (
            f"{emoji} *Trade Opened*\n"
            f"*Symbol:* `{symbol}`\n"
            f"*Direction:* {direction}\n"
            f"*Price:* `{price:.5f}`\n"
            f"*Lot:* `{lot}`\n"
            f"\u23f0 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self._send_message(text)

    async def send_trade_closed(
        self,
        symbol: str,
        direction: str,
        entry: float,
        exit_price: float,
        pnl: float,
        pips: Optional[float] = None,
    ) -> Dict[str, Any]:
        emoji = "\u2705" if pnl >= 0 else "\u274c"
        pnl_str = f"+{pnl:.2f}" if pnl >= 0 else f"{pnl:.2f}"
        lines = [
            f"{emoji} *Trade Closed*",
            f"*Symbol:* `{symbol}`",
            f"*Direction:* {direction}",
            f"*Entry:* `{entry:.5f}`",
            f"*Exit:* `{exit_price:.5f}`",
            f"*P&L:* `{pnl_str}`",
        ]
        if pips is not None:
            lines.append(f"*Pips:* `{pips:+.1f}`")
        lines.append(f"\n\u23f0 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        return await self._send_message("\n".join(lines))

    # ------------------------------------------------------------------
    # Daily summary
    # ------------------------------------------------------------------

    async def send_daily_summary(self, summary: DailySummary) -> Dict[str, Any]:
        pnl_emoji = "\U0001f4b0" if summary.net_pnl >= 0 else "\U0001f4b8"
        wr = summary.win_rate * 100
        text = (
            f"\U0001f4ca *Daily Summary — {summary.date}*\n\n"
            f"*Trades:* {summary.total_trades}  "
            f"(W: {summary.winning_trades} / L: {summary.losing_trades})\n"
            f"*Win Rate:* `{wr:.1f}%`\n"
            f"{pnl_emoji} *Net P&L:* `{summary.net_pnl:+.2f}`\n"
            f"*Max DD:* `{summary.max_drawdown:.2f}%`\n"
            f"*Equity:* `{summary.equity:,.2f}`\n"
            f"*Open Pos:* {summary.open_positions}"
        )
        return await self._send_message(text)

    # ------------------------------------------------------------------
    # Risk / emergency
    # ------------------------------------------------------------------

    async def send_risk_warning(self, message: str) -> Dict[str, Any]:
        text = f"\u26a0\ufe0f *Risk Warning*\n\n{message}"
        return await self._send_message(text)

    async def send_emergency_alert(self, message: str) -> Dict[str, Any]:
        text = (
            f"\U0001f6a8\U0001f6a8 *EMERGENCY ALERT* \U0001f6a8\U0001f6a8\n\n"
            f"{message}\n\n"
            f"\u23f0 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self._send_message(text, disable_notification=False)

    # ------------------------------------------------------------------
    # Convenience sync wrapper
    # ------------------------------------------------------------------

    def send_signal_sync(self, signal: TradeNotification) -> Dict[str, Any]:
        return asyncio.get_event_loop().run_until_complete(self.send_signal(signal))

    def send_daily_summary_sync(self, summary: DailySummary) -> Dict[str, Any]:
        return asyncio.get_event_loop().run_until_complete(
            self.send_daily_summary(summary)
        )
