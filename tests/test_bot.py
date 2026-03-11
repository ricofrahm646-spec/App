"""
Unit tests for the Hardcore Growth Mode crypto trading bot.

Tests cover:
- CoinSignal scoring and TP/SL calculation
- CoinScanner indicator helpers (RSI, MACD)
- TradeLogger CSV persistence
- TelegramNotifier graceful no-op when unconfigured
- Trader state persistence (crash-recovery round-trip)
- Config defaults
"""

import csv
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

# Point DATA_DIR at a temp directory so tests don't pollute real data
import config as _config_module


class ConfigDefaultsTest(unittest.TestCase):
    def test_quote_currency_default(self):
        import config
        self.assertEqual(config.QUOTE_CURRENCY, "EUR")

    def test_scan_interval_order(self):
        import config
        self.assertLessEqual(config.SCAN_INTERVAL_MIN, config.SCAN_INTERVAL_MAX)

    def test_risk_percentages(self):
        import config
        self.assertGreater(config.STOP_LOSS_PERCENT, 0)
        self.assertGreater(config.TAKE_PROFIT_PERCENT, config.STOP_LOSS_PERCENT)

    def test_trade_amount_range(self):
        import config
        self.assertLessEqual(
            config.TRADE_AMOUNT_PERCENT_MIN, config.TRADE_AMOUNT_PERCENT_MAX
        )
        self.assertGreater(config.TRADE_AMOUNT_PERCENT_MIN, 0)
        self.assertLessEqual(config.TRADE_AMOUNT_PERCENT_MAX, 1)


class CoinSignalTest(unittest.TestCase):
    def _make_signal(self, entry=100.0, score=100):
        from scanner import CoinSignal
        return CoinSignal(
            symbol="BTC/EUR",
            score=score,
            entry_price=entry,
            rsi=35.0,
            macd_diff=0.001,
            volume_spike_ratio=2.0,
            price_change_5m=0.03,
        )

    def test_take_profit_above_entry(self):
        sig = self._make_signal(entry=1000.0)
        self.assertGreater(sig.take_profit, sig.entry_price)

    def test_stop_loss_below_entry(self):
        sig = self._make_signal(entry=1000.0)
        self.assertLess(sig.stop_loss, sig.entry_price)

    def test_tp_sl_percentages(self):
        import config
        sig = self._make_signal(entry=1000.0)
        expected_tp = 1000.0 * (1 + config.TAKE_PROFIT_PERCENT)
        expected_sl = 1000.0 * (1 - config.STOP_LOSS_PERCENT)
        self.assertAlmostEqual(sig.take_profit, round(expected_tp, 8), places=4)
        self.assertAlmostEqual(sig.stop_loss, round(expected_sl, 8), places=4)

    def test_to_dict_keys(self):
        sig = self._make_signal()
        d = sig.to_dict()
        for key in ("symbol", "score", "entry_price", "take_profit", "stop_loss"):
            self.assertIn(key, d)


class ScannerIndicatorsTest(unittest.TestCase):
    def _sample_close(self, n=50, start=100.0, step=0.5):
        return pd.Series([start + i * step for i in range(n)])

    def test_rsi_in_range(self):
        from scanner import CoinScanner
        close = self._sample_close()
        rsi = CoinScanner._rsi(close)
        self.assertGreaterEqual(rsi, 0)
        self.assertLessEqual(rsi, 100)

    def test_rsi_rising_series_above_50(self):
        from scanner import CoinScanner
        close = self._sample_close(n=50, step=1.0)   # strictly rising
        rsi = CoinScanner._rsi(close)
        self.assertGreater(rsi, 50)

    def test_macd_diff_returns_float(self):
        from scanner import CoinScanner
        close = self._sample_close(n=50)
        diff = CoinScanner._macd_diff(close)
        self.assertIsInstance(diff, float)

    def test_macd_flat_series_near_zero(self):
        from scanner import CoinScanner
        close = pd.Series([100.0] * 50)
        diff = CoinScanner._macd_diff(close)
        self.assertAlmostEqual(diff, 0.0, places=6)


class TradeLoggerTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_data_dir = _config_module.DATA_DIR
        self._orig_history = _config_module.HISTORY_FILE
        _config_module.DATA_DIR = self._tmpdir
        _config_module.HISTORY_FILE = os.path.join(self._tmpdir, "history.csv")

    def tearDown(self):
        _config_module.DATA_DIR = self._orig_data_dir
        _config_module.HISTORY_FILE = self._orig_history

    def _make_logger(self):
        from logger import TradeLogger
        return TradeLogger()

    def test_csv_created_on_init(self):
        self._make_logger()
        self.assertTrue(os.path.exists(_config_module.HISTORY_FILE))

    def test_csv_has_header(self):
        self._make_logger()
        with open(_config_module.HISTORY_FILE, newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader)
        self.assertIn("symbol", header)
        self.assertIn("pnl_eur", header)

    def test_log_trade_appends_row(self):
        trade_logger = self._make_logger()
        record = {
            "symbol": "ETH/EUR",
            "score": 100,
            "buy_price": 2000.0,
            "sell_price": 2150.0,
            "amount": 0.5,
            "pnl_eur": 75.0,
            "pnl_pct": 7.5,
            "reason": "TAKE_PROFIT",
        }
        trade_logger.log_trade(record)
        with open(_config_module.HISTORY_FILE, newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "ETH/EUR")
        self.assertEqual(rows[0]["reason"], "TAKE_PROFIT")

    def test_log_multiple_trades(self):
        trade_logger = self._make_logger()
        for i in range(5):
            trade_logger.log_trade(
                {
                    "symbol": f"COIN{i}/EUR",
                    "pnl_eur": float(i),
                    "pnl_pct": float(i),
                    "reason": "TAKE_PROFIT",
                }
            )
        with open(_config_module.HISTORY_FILE, newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(len(rows), 5)

    def test_print_summary_no_crash_on_empty(self):
        trade_logger = self._make_logger()
        trade_logger.print_summary()  # should not raise


class TelegramNotifierTest(unittest.TestCase):
    def test_no_op_when_unconfigured(self):
        """Notifier must not raise when token/chat_id are empty."""
        orig_token = _config_module.TELEGRAM_TOKEN
        orig_chat = _config_module.TELEGRAM_CHAT_ID
        _config_module.TELEGRAM_TOKEN = ""
        _config_module.TELEGRAM_CHAT_ID = ""
        try:
            from notifier import TelegramNotifier
            n = TelegramNotifier()
            n.send("hello")
            n.send_signal(
                {
                    "symbol": "BTC/EUR",
                    "score": 100,
                    "entry_price": 50000.0,
                    "take_profit": 53750.0,
                    "stop_loss": 48750.0,
                    "rsi": 35.0,
                    "macd_diff": 0.001,
                    "volume_spike_ratio": 2.0,
                    "price_change_5m": 3.0,
                }
            )
            n.send_close({"symbol": "BTC/EUR", "reason": "TP", "pnl_eur": 100.0, "pnl_pct": 7.5})
        finally:
            _config_module.TELEGRAM_TOKEN = orig_token
            _config_module.TELEGRAM_CHAT_ID = orig_chat


class TraderStateTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_data_dir = _config_module.DATA_DIR
        self._orig_state = _config_module.STATE_FILE
        _config_module.DATA_DIR = self._tmpdir
        _config_module.STATE_FILE = os.path.join(self._tmpdir, "state.json")

    def tearDown(self):
        _config_module.DATA_DIR = self._orig_data_dir
        _config_module.STATE_FILE = self._orig_state

    def test_save_and_load_state(self):
        from trader import Trader, Position
        with patch("ccxt.kraken") as mock_cls:
            mock_cls.return_value = MagicMock()
            t = Trader()

        pos = Position(
            symbol="SOL/EUR",
            buy_price=150.0,
            amount=1.0,
            take_profit=161.25,
            stop_loss=146.25,
            score=100,
            trade_id="abc123",
        )
        t.open_positions["SOL/EUR"] = pos
        t._save_state()

        # Load into a fresh Trader
        with patch("ccxt.kraken") as mock_cls:
            mock_cls.return_value = MagicMock()
            t2 = Trader()

        self.assertIn("SOL/EUR", t2.open_positions)
        loaded = t2.open_positions["SOL/EUR"]
        self.assertEqual(loaded.buy_price, 150.0)
        self.assertEqual(loaded.trade_id, "abc123")

    def test_empty_state_file_handled(self):
        """Trader should start cleanly even if state file doesn't exist."""
        from trader import Trader
        with patch("ccxt.kraken") as mock_cls:
            mock_cls.return_value = MagicMock()
            t = Trader()
        self.assertEqual(len(t.open_positions), 0)


if __name__ == "__main__":
    unittest.main()
