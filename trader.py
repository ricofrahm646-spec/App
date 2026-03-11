"""
Trade executor for the Hardcore Growth Mode trading bot.

Responsibilities:
- Place market buy orders using 30-50% of current EUR balance
- Track open positions with take-profit and stop-loss prices
- Monitor open positions and close them when TP/SL is hit
- Automatically retry failed order placements
- Persist open positions to data/state.json for crash recovery
- Automatically reinvest profits (achieved via percentage-of-balance sizing)
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional

import ccxt

import config
from scanner import CoinSignal


@dataclass
class Position:
    symbol: str
    buy_price: float
    amount: float         # base currency amount bought
    take_profit: float
    stop_loss: float
    score: int
    trade_id: str         # client order id or exchange order id


class Trader:
    """Manages order placement and position monitoring."""

    def __init__(self) -> None:
        exchange_class = getattr(ccxt, config.EXCHANGE_ID)
        self.exchange: ccxt.Exchange = exchange_class(
            {
                "apiKey": config.API_KEY,
                "secret": config.API_SECRET,
                "enableRateLimit": True,
            }
        )
        self.open_positions: Dict[str, Position] = {}
        self._load_state()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def process_signals(
        self, signals: List[CoinSignal]
    ) -> List[Optional[Position]]:
        """Open new positions for the supplied signals (skip already open symbols)."""
        opened: List[Optional[Position]] = []
        for signal in signals:
            if signal.symbol in self.open_positions:
                logging.info("Already holding %s – skipping.", signal.symbol)
                continue
            pos = self._open_position(signal)
            if pos is not None:
                opened.append(pos)
        return opened

    def monitor_positions(self) -> List[dict]:
        """Check all open positions against live prices; close on TP/SL hit.

        Returns a list of closed-trade records suitable for logging.
        """
        closed_trades: List[dict] = []
        symbols = list(self.open_positions.keys())
        for symbol in symbols:
            pos = self.open_positions[symbol]
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = float(ticker["last"])
            except Exception as exc:  # noqa: BLE001
                logging.warning("Could not fetch ticker for %s: %s", symbol, exc)
                continue

            if current_price >= pos.take_profit:
                record = self._close_position(pos, current_price, reason="TAKE_PROFIT")
                closed_trades.append(record)
            elif current_price <= pos.stop_loss:
                record = self._close_position(pos, current_price, reason="STOP_LOSS")
                closed_trades.append(record)

        return closed_trades

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _open_position(self, signal: CoinSignal) -> Optional[Position]:
        eur_balance = self._get_eur_balance()
        if eur_balance is None or eur_balance <= 0:
            logging.warning("No EUR balance available – skipping %s.", signal.symbol)
            return None

        # Use a score-weighted allocation within [min%, max%] range
        pct_range = config.TRADE_AMOUNT_PERCENT_MAX - config.TRADE_AMOUNT_PERCENT_MIN
        pct = config.TRADE_AMOUNT_PERCENT_MIN + pct_range * (signal.score / 100)
        trade_eur = eur_balance * pct

        amount = trade_eur / signal.entry_price  # base currency amount

        order = self._place_order_with_retry("buy", signal.symbol, amount)
        if order is None:
            return None

        fill_price = float(order.get("average") or order.get("price") or signal.entry_price)
        pos = Position(
            symbol=signal.symbol,
            buy_price=fill_price,
            amount=float(order.get("filled") or amount),
            take_profit=round(fill_price * (1 + config.TAKE_PROFIT_PERCENT), 8),
            stop_loss=round(fill_price * (1 - config.STOP_LOSS_PERCENT), 8),
            score=signal.score,
            trade_id=str(order.get("id", "")),
        )
        self.open_positions[signal.symbol] = pos
        self._save_state()
        logging.info(
            "Opened %s @ %.8f | TP=%.8f | SL=%.8f | score=%d",
            pos.symbol, pos.buy_price, pos.take_profit, pos.stop_loss, pos.score,
        )
        return pos

    def _close_position(self, pos: Position, exit_price: float, reason: str) -> dict:
        order = self._place_order_with_retry("sell", pos.symbol, pos.amount)
        actual_exit = (
            float(order.get("average") or order.get("price") or exit_price)
            if order
            else exit_price
        )

        pnl = (actual_exit - pos.buy_price) * pos.amount
        pnl_pct = (actual_exit - pos.buy_price) / pos.buy_price * 100

        logging.info(
            "Closed %s @ %.8f (%s) | PnL=%.4f EUR (%.2f%%)",
            pos.symbol, actual_exit, reason, pnl, pnl_pct,
        )

        record = {
            "symbol": pos.symbol,
            "buy_price": pos.buy_price,
            "sell_price": actual_exit,
            "amount": pos.amount,
            "pnl_eur": round(pnl, 4),
            "pnl_pct": round(pnl_pct, 2),
            "reason": reason,
            "score": pos.score,
        }

        del self.open_positions[pos.symbol]
        self._save_state()
        return record

    def _place_order_with_retry(
        self, side: str, symbol: str, amount: float
    ) -> Optional[dict]:
        for attempt in range(1, config.MAX_RETRIES + 1):
            try:
                order = self.exchange.create_market_order(symbol, side, amount)
                logging.info(
                    "Order %s %s %.8f – attempt %d succeeded", side, symbol, amount, attempt
                )
                return order
            except ccxt.InsufficientFunds as exc:
                logging.error("Insufficient funds for %s %s: %s", side, symbol, exc)
                return None
            except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
                logging.warning(
                    "Order attempt %d/%d failed for %s %s: %s",
                    attempt, config.MAX_RETRIES, side, symbol, exc,
                )
                if attempt < config.MAX_RETRIES:
                    time.sleep(config.RETRY_DELAY)
        return None

    def _get_eur_balance(self) -> Optional[float]:
        try:
            balance = self.exchange.fetch_balance()
            return float(balance["free"].get(config.QUOTE_CURRENCY, 0))
        except Exception as exc:  # noqa: BLE001
            logging.error("Could not fetch balance: %s", exc)
            return None

    # ------------------------------------------------------------------
    # State persistence (crash recovery)
    # ------------------------------------------------------------------

    def _save_state(self) -> None:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        data = {sym: asdict(pos) for sym, pos in self.open_positions.items()}
        with open(config.STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    def _load_state(self) -> None:
        if not os.path.exists(config.STATE_FILE):
            return
        try:
            with open(config.STATE_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
            for sym, d in data.items():
                self.open_positions[sym] = Position(**d)
            if self.open_positions:
                logging.info(
                    "Recovered %d open position(s) from state file.",
                    len(self.open_positions),
                )
        except Exception as exc:  # noqa: BLE001
            logging.warning("Could not load state: %s – starting fresh.", exc)
