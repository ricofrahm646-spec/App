"""
Hardcore Growth Mode – Crypto Trading Bot
==========================================

Main entry point.  Runs a fully autonomous 24/7 trading loop:

  1. Scan all EUR pairs on the configured exchange (every 20-30 s)
  2. Score coins on RSI, MACD, volume spike and short-term price action
  3. Open positions for the top 3 coins that score > 80
  4. Monitor open positions for take-profit / stop-loss hits
  5. Log every closed trade to data/history.csv
  6. Send Telegram alerts for new signals and closed trades
  7. Reinvest profits automatically (balance-percentage sizing)
  8. Recover from crashes and resume where it left off

Usage:
    python bot.py

Configuration is read from a .env file (see .env.example).
"""

import logging
import os
import random
import time
import traceback

import config
from logger import TradeLogger
from notifier import TelegramNotifier
from scanner import CoinScanner
from trader import Trader


def _setup_logging() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    handlers: list = [logging.StreamHandler()]
    try:
        handlers.append(logging.FileHandler(config.LOG_FILE, encoding="utf-8"))
    except OSError as exc:
        print(f"Warning: could not open log file {config.LOG_FILE}: {exc}")

    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)


def _trading_cycle(
    scanner: CoinScanner,
    trader: Trader,
    notifier: TelegramNotifier,
    trade_logger: TradeLogger,
) -> None:
    # ── 1. Monitor existing positions ──────────────────────────────────
    closed = trader.monitor_positions()
    if closed:
        trade_logger.log_trades(closed)
        for record in closed:
            notifier.send_close(record)
        trade_logger.print_summary()

    # ── 2. Scan for new opportunities ──────────────────────────────────
    signals = scanner.scan()

    # ── 3. Open positions for qualifying signals ────────────────────────
    new_positions = trader.process_signals(signals)

    # ── 4. Alert on new positions ───────────────────────────────────────
    for pos in new_positions:
        if pos is None:
            continue
        # Find the corresponding signal for full alert data
        for sig in signals:
            if sig.symbol == pos.symbol:
                notifier.send_signal(sig.to_dict())
                break


def main() -> None:
    _setup_logging()

    logging.info("=" * 60)
    logging.info("🚀  Hardcore Growth Mode – Bot starting up")
    logging.info("=" * 60)

    scanner = CoinScanner()
    trader = Trader()
    notifier = TelegramNotifier()
    trade_logger = TradeLogger()

    notifier.send("🚀 Hardcore Growth Mode activated. Bot running 24/7.")

    consecutive_errors = 0

    while True:
        try:
            _trading_cycle(scanner, trader, notifier, trade_logger)
            consecutive_errors = 0
        except KeyboardInterrupt:
            logging.info("Shutdown requested – exiting.")
            notifier.send("⛔ Bot stopped manually.")
            break
        except Exception:  # noqa: BLE001
            consecutive_errors += 1
            tb = traceback.format_exc()
            logging.error("Cycle error (consecutive=%d):\n%s", consecutive_errors, tb)
            notifier.send(f"⚠️ Bot error #{consecutive_errors} – recovering…")

            # Exponential back-off (cap at 5 min) to avoid hammering the exchange
            sleep_secs = min(10 * (2 ** (consecutive_errors - 1)), 300)
            logging.info("Sleeping %d s before next attempt…", sleep_secs)
            time.sleep(sleep_secs)
            continue

        # ── Randomise scan interval (20-30 s) to reduce detectable patterns ──
        interval = random.randint(
            config.SCAN_INTERVAL_MIN, config.SCAN_INTERVAL_MAX
        )
        logging.info("Next scan in %d s…", interval)
        time.sleep(interval)


if __name__ == "__main__":
    main()
