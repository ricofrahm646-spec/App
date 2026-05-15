import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

try:
    from telegram import Bot, InputFile
    from telegram.error import TelegramError
    from telegram.constants import ParseMode
except ImportError:
    Bot = None  # type: ignore
    TelegramError = Exception
    ParseMode = None  # type: ignore
    logger.warning("python-telegram-bot not installed; Telegram features unavailable.")


class TelegramService:
    """
    Manages all Telegram notifications for the JARVIS trading system.

    Sends trade signals, alerts, daily summaries, and chart images.
    Uses HTML parse mode for rich formatting.
    """

    def __init__(self) -> None:
        self._bot: Optional[object] = None
        self._chat_id: Optional[str] = None
        self._initialized: bool = False

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    async def initialize(self, token: str, chat_id: str) -> bool:
        """
        Connect the bot and verify the chat_id is reachable.

        Args:
            token: Telegram Bot API token (from @BotFather).
            chat_id: Target chat / channel ID (e.g. "-1001234567890").

        Returns:
            True if the bot started and a test message could be delivered.
        """
        if Bot is None:
            logger.error("python-telegram-bot package is not installed.")
            return False

        try:
            self._bot = Bot(token=token)
            self._chat_id = str(chat_id)

            # Verify connectivity
            me = await self._bot.get_me()
            logger.info(f"Telegram bot connected: @{me.username} (id={me.id})")
            self._initialized = True
            await self.send_message(
                "🤖 <b>JARVIS</b> is online and monitoring the markets."
            )
            return True
        except TelegramError as exc:
            logger.error(f"Telegram initialisation failed: {exc}")
            self._initialized = False
            return False

    def _ensure_init(self) -> None:
        if not self._initialized or self._bot is None:
            raise RuntimeError(
                "TelegramService not initialised. Call initialize() first."
            )

    # ------------------------------------------------------------------
    # Core send helpers
    # ------------------------------------------------------------------

    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a text message to the configured chat.

        Args:
            message: Text content (supports HTML tags when parse_mode="HTML").
            parse_mode: "HTML" (default) or "Markdown".

        Returns:
            True on success, False on failure.
        """
        self._ensure_init()
        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=True,
            )
            return True
        except TelegramError as exc:
            logger.error(f"send_message failed: {exc}")
            return False

    async def send_chart(self, image_path: str, caption: str = "") -> bool:
        """
        Send a chart image file with an optional caption.

        Args:
            image_path: Absolute path to the image file (PNG/JPEG).
            caption: Optional caption text (HTML supported).

        Returns:
            True on success, False on failure.
        """
        self._ensure_init()
        path = Path(image_path)
        if not path.exists():
            logger.error(f"Chart image not found: {image_path}")
            return False

        try:
            with open(path, "rb") as f:
                await self._bot.send_photo(
                    chat_id=self._chat_id,
                    photo=f,
                    caption=caption[:1024],  # Telegram caption limit
                    parse_mode="HTML",
                )
            return True
        except TelegramError as exc:
            logger.error(f"send_chart failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Trade event notifications
    # ------------------------------------------------------------------

    async def send_trade_signal(self, signal: Dict) -> bool:
        """
        Announce an incoming trade signal before execution.

        Expected signal keys:
            symbol, action (BUY/SELL), price, sl, tp,
            strategy (str), confidence (float 0-1, optional).
        """
        action = signal.get("action", "BUY").upper()
        emoji = "🟢" if action == "BUY" else "🔴"
        symbol = signal.get("symbol", "N/A")
        price = signal.get("price", 0.0)
        sl = signal.get("sl", 0.0)
        tp = signal.get("tp", 0.0)
        strategy = signal.get("strategy", "JARVIS")
        confidence = signal.get("confidence")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        lines = [
            f"{emoji} <b>SIGNAL: {action} {symbol}</b>",
            f"📍 Entry:  <code>{price}</code>",
            f"🛑 SL:     <code>{sl}</code>",
            f"🎯 TP:     <code>{tp}</code>",
            f"⚙️ Strategy: {strategy}",
        ]
        if confidence is not None:
            lines.append(f"📊 Confidence: {confidence*100:.1f}%")
        lines.append(f"🕐 {ts}")

        return await self.send_message("\n".join(lines))

    async def send_trade_opened(self, trade: Dict) -> bool:
        """
        Notify that a trade has been successfully executed.

        Expected trade keys: ticket, symbol, type, volume, open_price, sl, tp, magic.
        """
        action = trade.get("type", "BUY").upper()
        emoji = "🟢" if action == "BUY" else "🔴"
        symbol = trade.get("symbol", "N/A")
        ticket = trade.get("ticket", 0)
        volume = trade.get("volume", 0.0)
        price = trade.get("open_price", trade.get("price", 0.0))
        sl = trade.get("sl", 0.0)
        tp = trade.get("tp", 0.0)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        msg = (
            f"{emoji} <b>TRADE OPENED</b>\n"
            f"🎫 Ticket:  <code>#{ticket}</code>\n"
            f"💱 Symbol:  <b>{symbol}</b>\n"
            f"📈 Type:    {action} {volume} lot(s)\n"
            f"📍 Price:   <code>{price}</code>\n"
            f"🛑 SL:      <code>{sl}</code>\n"
            f"🎯 TP:      <code>{tp}</code>\n"
            f"🕐 {ts}"
        )
        return await self.send_message(msg)

    async def send_trade_closed(self, trade: Dict) -> bool:
        """
        Notify that a trade has been closed with its P&L.

        Expected trade keys: ticket, symbol, type, profit, close_price,
                             open_price, volume, pips (optional).
        """
        profit = trade.get("profit", 0.0)
        profit_emoji = "✅" if profit >= 0 else "❌"
        profit_sign = "+" if profit >= 0 else ""
        symbol = trade.get("symbol", "N/A")
        ticket = trade.get("ticket", 0)
        action = trade.get("type", "BUY").upper()
        volume = trade.get("volume", 0.0)
        open_price = trade.get("open_price", 0.0)
        close_price = trade.get("close_price", trade.get("price", 0.0))
        pips = trade.get("pips", "N/A")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

        msg = (
            f"{profit_emoji} <b>TRADE CLOSED</b>\n"
            f"🎫 Ticket:      <code>#{ticket}</code>\n"
            f"💱 Symbol:      <b>{symbol}</b>\n"
            f"📈 Type:        {action} {volume} lot(s)\n"
            f"📍 Open:        <code>{open_price}</code>\n"
            f"🚪 Close:       <code>{close_price}</code>\n"
            f"📏 Pips:        {pips}\n"
            f"💰 P&L:         <b>{profit_sign}{profit:.2f}</b>\n"
            f"🕐 {ts}"
        )
        return await self.send_message(msg)

    async def send_profit_update(self, profit: float, total: float) -> bool:
        """
        Send a running profit update.

        Args:
            profit: Current trade / session profit.
            total: Total account profit (floating).
        """
        profit_emoji = "📈" if profit >= 0 else "📉"
        sign = "+" if profit >= 0 else ""
        msg = (
            f"{profit_emoji} <b>Profit Update</b>\n"
            f"💵 Current P&L:  <b>{sign}{profit:.2f}</b>\n"
            f"💼 Total P&L:    <b>{'+' if total >= 0 else ''}{total:.2f}</b>\n"
            f"🕐 {datetime.now().strftime('%H:%M:%S UTC')}"
        )
        return await self.send_message(msg)

    async def send_risk_warning(self, message: str) -> bool:
        """
        Send a high-priority risk alert.

        Args:
            message: Human-readable warning text.
        """
        msg = (
            f"⚠️ <b>RISK WARNING</b>\n"
            f"{message}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        return await self.send_message(msg)

    async def send_daily_summary(self, summary: Dict) -> bool:
        """
        Send the end-of-day performance summary.

        Expected summary keys:
            date (str), total_trades, winning_trades, losing_trades,
            gross_profit, gross_loss, net_profit, profit_factor,
            win_rate (float 0-1), max_drawdown (float 0-1),
            best_trade (float), worst_trade (float), account_balance (float).
        """
        date = summary.get("date", datetime.now().strftime("%Y-%m-%d"))
        total = summary.get("total_trades", 0)
        wins = summary.get("winning_trades", 0)
        losses = summary.get("losing_trades", 0)
        net = summary.get("net_profit", 0.0)
        gross_profit = summary.get("gross_profit", 0.0)
        gross_loss = summary.get("gross_loss", 0.0)
        pf = summary.get("profit_factor", 0.0)
        wr = summary.get("win_rate", 0.0) * 100
        max_dd = summary.get("max_drawdown", 0.0) * 100
        best = summary.get("best_trade", 0.0)
        worst = summary.get("worst_trade", 0.0)
        balance = summary.get("account_balance", 0.0)
        net_sign = "+" if net >= 0 else ""
        session_emoji = "🏆" if net > 0 else "😔" if net < 0 else "😐"

        msg = (
            f"{session_emoji} <b>Daily Summary — {date}</b>\n"
            f"{'─' * 30}\n"
            f"📊 Trades:         {wins}W / {losses}L / {total} total\n"
            f"📈 Win Rate:       {wr:.1f}%\n"
            f"💰 Net P&L:        <b>{net_sign}{net:.2f}</b>\n"
            f"✅ Gross Profit:   {gross_profit:.2f}\n"
            f"❌ Gross Loss:     {gross_loss:.2f}\n"
            f"⚡ Profit Factor:  {pf:.2f}\n"
            f"📉 Max Drawdown:   {max_dd:.1f}%\n"
            f"🏅 Best Trade:     +{best:.2f}\n"
            f"💀 Worst Trade:    {worst:.2f}\n"
            f"🏦 Balance:        {balance:.2f}\n"
        )
        return await self.send_message(msg)

    # ------------------------------------------------------------------
    # System notifications
    # ------------------------------------------------------------------

    async def send_system_status(self, status: Dict) -> bool:
        """
        Broadcast system health information.

        Expected keys: connected (bool), uptime_hours (float),
                       open_trades (int), server (str).
        """
        connected = status.get("connected", False)
        conn_icon = "🟢" if connected else "🔴"
        msg = (
            f"🖥️ <b>System Status</b>\n"
            f"{conn_icon} MT5: {'Connected' if connected else 'Disconnected'}\n"
            f"⏱️ Uptime: {status.get('uptime_hours', 0):.1f}h\n"
            f"📂 Open Trades: {status.get('open_trades', 0)}\n"
            f"🌐 Server: {status.get('server', 'N/A')}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        return await self.send_message(msg)

    async def broadcast_to_multiple(
        self, chat_ids: List[str], message: str
    ) -> Dict[str, bool]:
        """
        Send the same message to multiple chats concurrently.

        Returns:
            Dict mapping each chat_id to success/failure bool.
        """
        original_chat = self._chat_id
        results: Dict[str, bool] = {}

        async def _send_to(cid: str) -> tuple:
            self._chat_id = cid
            success = await self.send_message(message)
            return cid, success

        tasks = [asyncio.create_task(_send_to(cid)) for cid in chat_ids]
        done = await asyncio.gather(*tasks, return_exceptions=True)

        for item in done:
            if isinstance(item, Exception):
                logger.error(f"broadcast error: {item}")
            else:
                cid, ok = item
                results[cid] = ok

        self._chat_id = original_chat
        return results
