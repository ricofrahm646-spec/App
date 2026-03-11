"""
Unit tests for trading_bot.py

Tests cover all indicator calculations, scoring functions, CSV logging,
and the core analysis pipeline using synthetic (mock) data – no live
network calls are made.
"""

import csv
import math
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import ccxt
import numpy as np
import pandas as pd

import config
import trading_bot as tb


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_closes(values) -> pd.Series:
    return pd.Series(values, dtype=float)


def _make_volumes(values) -> pd.Series:
    return pd.Series(values, dtype=float)


def _synthetic_ohlcv(n: int = 60, base_price: float = 100.0, base_vol: float = 1000.0):
    """Return a list of [ts, open, high, low, close, volume] rows."""
    rows = []
    price = base_price
    for i in range(n):
        open_ = price
        close = price * (1 + 0.001 * (i % 5 - 2))  # small oscillation
        high = max(open_, close) * 1.001
        low = min(open_, close) * 0.999
        vol = base_vol * (1 + 0.05 * (i % 3))
        rows.append([i * 300_000, open_, high, low, close, vol])
        price = close
    return rows


# ── RSI ────────────────────────────────────────────────────────────────────────

class TestRSI(unittest.TestCase):
    def test_insufficient_data_returns_nan(self):
        closes = _make_closes([100.0] * 5)
        result = tb.calculate_rsi(closes, period=14)
        self.assertTrue(math.isnan(result))

    def test_all_gains_rsi_near_100(self):
        # Monotonically rising prices → RSI close to 100
        closes = _make_closes([float(i) for i in range(1, 50)])
        rsi = tb.calculate_rsi(closes, period=14)
        self.assertFalse(math.isnan(rsi))
        self.assertGreater(rsi, 90.0)

    def test_all_losses_rsi_near_0(self):
        # Monotonically falling prices → RSI close to 0
        closes = _make_closes([float(i) for i in range(50, 1, -1)])
        rsi = tb.calculate_rsi(closes, period=14)
        self.assertFalse(math.isnan(rsi))
        self.assertLess(rsi, 10.0)

    def test_rsi_within_bounds(self):
        closes = _make_closes([100 + (i % 7) - 3 for i in range(50)])
        rsi = tb.calculate_rsi(closes, period=14)
        self.assertFalse(math.isnan(rsi))
        self.assertGreaterEqual(rsi, 0.0)
        self.assertLessEqual(rsi, 100.0)


# ── MACD ───────────────────────────────────────────────────────────────────────

class TestMACD(unittest.TestCase):
    def test_insufficient_data_returns_nan(self):
        closes = _make_closes([100.0] * 10)
        macd, sig, hist = tb.calculate_macd(closes)
        self.assertTrue(math.isnan(macd))
        self.assertTrue(math.isnan(sig))
        self.assertTrue(math.isnan(hist))

    def test_histogram_equals_macd_minus_signal(self):
        closes = _make_closes([100 + i * 0.5 for i in range(60)])
        macd, sig, hist = tb.calculate_macd(closes)
        self.assertFalse(math.isnan(macd))
        self.assertAlmostEqual(hist, macd - sig, places=8)

    def test_rising_market_macd_positive(self):
        # Strongly rising prices → MACD line should be positive
        closes = _make_closes([100 + i for i in range(60)])
        macd, sig, hist = tb.calculate_macd(closes)
        self.assertGreater(macd, 0.0)


# ── Bollinger Bands ────────────────────────────────────────────────────────────

class TestBollingerBands(unittest.TestCase):
    def test_insufficient_data_returns_nan(self):
        closes = _make_closes([100.0] * 5)
        upper, mid, lower = tb.calculate_bollinger_bands(closes, period=20)
        self.assertTrue(math.isnan(upper))

    def test_band_order(self):
        closes = _make_closes([100 + (i % 5) for i in range(40)])
        upper, mid, lower = tb.calculate_bollinger_bands(closes, period=20)
        self.assertFalse(math.isnan(upper))
        self.assertGreater(upper, mid)
        self.assertGreater(mid, lower)

    def test_constant_prices_zero_width(self):
        closes = _make_closes([50.0] * 30)
        upper, mid, lower = tb.calculate_bollinger_bands(closes, period=20)
        self.assertAlmostEqual(upper, 50.0, places=6)
        self.assertAlmostEqual(mid, 50.0, places=6)
        self.assertAlmostEqual(lower, 50.0, places=6)


# ── Volume change ──────────────────────────────────────────────────────────────

class TestVolumeChange(unittest.TestCase):
    def test_insufficient_data_returns_zero(self):
        vols = _make_volumes([1000.0] * 3)
        self.assertEqual(tb.calculate_volume_change(vols, lookback=5, baseline=5), 0.0)

    def test_doubled_volume_returns_100(self):
        # baseline avg = 100, recent avg = 200 → 100 % increase
        baseline = [100.0] * 5
        recent = [200.0] * 5
        vols = _make_volumes(baseline + recent)
        change = tb.calculate_volume_change(vols, lookback=5, baseline=5)
        self.assertAlmostEqual(change, 100.0, places=4)

    def test_zero_baseline_returns_zero(self):
        vols = _make_volumes([0.0] * 10 + [500.0] * 5)
        change = tb.calculate_volume_change(vols, lookback=5, baseline=5)
        self.assertEqual(change, 0.0)


# ── Price change ───────────────────────────────────────────────────────────────

class TestPriceChange(unittest.TestCase):
    def test_single_value_returns_zero(self):
        self.assertEqual(tb.calculate_price_change(_make_closes([100.0])), 0.0)

    def test_10_percent_increase(self):
        closes = _make_closes([100.0, 110.0])
        self.assertAlmostEqual(tb.calculate_price_change(closes), 10.0, places=6)

    def test_price_decrease_returns_negative(self):
        closes = _make_closes([200.0, 180.0])
        change = tb.calculate_price_change(closes)
        self.assertLess(change, 0.0)


# ── Scoring functions ──────────────────────────────────────────────────────────

class TestScoringFunctions(unittest.TestCase):
    def test_score_price_zero_or_negative(self):
        self.assertEqual(tb.score_price_momentum(0.0), 0.0)
        self.assertEqual(tb.score_price_momentum(-1.0), 0.0)

    def test_score_price_capped_at_100(self):
        self.assertEqual(tb.score_price_momentum(100.0), 100.0)

    def test_score_price_at_5pct(self):
        self.assertAlmostEqual(tb.score_price_momentum(5.0), 100.0, places=4)

    def test_score_price_at_2pct(self):
        self.assertAlmostEqual(tb.score_price_momentum(2.0), 40.0, places=4)

    def test_score_volume_zero_or_negative(self):
        self.assertEqual(tb.score_volume_spike(0.0), 0.0)
        self.assertEqual(tb.score_volume_spike(-50.0), 0.0)

    def test_score_volume_capped_at_100(self):
        self.assertEqual(tb.score_volume_spike(1000.0), 100.0)

    def test_score_rsi_nan_returns_zero(self):
        self.assertEqual(tb.score_rsi(float("nan")), 0.0)

    def test_score_rsi_optimal_range(self):
        self.assertEqual(tb.score_rsi(60.0), 100.0)

    def test_score_rsi_outside_range(self):
        self.assertEqual(tb.score_rsi(90.0), 0.0)
        self.assertEqual(tb.score_rsi(30.0), 0.0)

    def test_score_macd_bullish(self):
        self.assertEqual(tb.score_macd(1.0, 0.5, 0.5), 100.0)

    def test_score_macd_macd_above_signal_no_hist(self):
        self.assertEqual(tb.score_macd(1.0, 0.5, -0.1), 50.0)

    def test_score_macd_bearish(self):
        self.assertEqual(tb.score_macd(-1.0, 0.5, -0.5), 0.0)

    def test_score_bollinger_above_upper(self):
        self.assertEqual(tb.score_bollinger(105.0, 100.0, 95.0), 100.0)

    def test_score_bollinger_above_middle(self):
        self.assertEqual(tb.score_bollinger(97.0, 100.0, 95.0), 50.0)

    def test_score_bollinger_below_middle(self):
        self.assertEqual(tb.score_bollinger(90.0, 100.0, 95.0), 0.0)

    def test_compute_score_returns_value_in_range(self):
        ind = tb.Indicators(
            symbol="BTC/EUR",
            price=50000.0,
            price_change_pct=3.0,
            volume_change_pct=200.0,
            rsi=60.0,
            macd=10.0,
            macd_signal=5.0,
            macd_hist=5.0,
            bb_upper=50100.0,
            bb_middle=49000.0,
            bb_lower=47000.0,
        )
        score = tb.compute_score(ind)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_perfect_momentum_score_above_threshold(self):
        ind = tb.Indicators(
            symbol="BTC/EUR",
            price=110.0,
            price_change_pct=10.0,
            volume_change_pct=500.0,
            rsi=65.0,
            macd=2.0,
            macd_signal=1.0,
            macd_hist=1.0,
            bb_upper=105.0,
            bb_middle=100.0,
            bb_lower=95.0,
        )
        score = tb.compute_score(ind)
        self.assertGreater(score, config.SCORE_THRESHOLD)


# ── Pump detection ─────────────────────────────────────────────────────────────

class TestPumpDetection(unittest.TestCase):
    def _make_ind(self, price_chg, vol_chg):
        return tb.Indicators(
            symbol="TEST/EUR",
            price_change_pct=price_chg,
            volume_change_pct=vol_chg,
        )

    def test_pump_both_conditions_met(self):
        ind = self._make_ind(3.0, 200.0)
        ind.is_pump = (
            ind.price_change_pct >= config.PRICE_INCREASE_THRESHOLD
            and ind.volume_change_pct >= config.VOLUME_SPIKE_THRESHOLD
        )
        self.assertTrue(ind.is_pump)

    def test_no_pump_low_volume(self):
        ind = self._make_ind(3.0, 50.0)
        ind.is_pump = (
            ind.price_change_pct >= config.PRICE_INCREASE_THRESHOLD
            and ind.volume_change_pct >= config.VOLUME_SPIKE_THRESHOLD
        )
        self.assertFalse(ind.is_pump)

    def test_no_pump_low_price_change(self):
        ind = self._make_ind(0.5, 200.0)
        ind.is_pump = (
            ind.price_change_pct >= config.PRICE_INCREASE_THRESHOLD
            and ind.volume_change_pct >= config.VOLUME_SPIKE_THRESHOLD
        )
        self.assertFalse(ind.is_pump)


# ── CSV logging ────────────────────────────────────────────────────────────────

class TestCSVLogging(unittest.TestCase):
    def _make_signal(self):
        return tb.TradeSignal(
            timestamp="2024-01-01T00:00:00+00:00",
            symbol="BTC/EUR",
            price=50000.0,
            price_change_pct=3.0,
            volume_change_pct=200.0,
            rsi=62.0,
            macd=5.0,
            macd_signal=3.0,
            macd_hist=2.0,
            bb_upper=50500.0,
            bb_middle=49000.0,
            bb_lower=47500.0,
            score=85.0,
            is_pump=True,
        )

    def test_csv_created_with_headers(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        os.unlink(path)  # ensure it doesn't exist yet
        try:
            signal = self._make_signal()
            tb.log_trade_signal(signal, path=path)
            self.assertTrue(os.path.exists(path))
            with open(path, "r", newline="") as fh:
                reader = csv.DictReader(fh)
                self.assertEqual(reader.fieldnames, tb.CSV_HEADERS)
                rows = list(reader)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["symbol"], "BTC/EUR")
            self.assertEqual(float(rows[0]["score"]), 85.0)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_multiple_signals_appended(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        os.unlink(path)
        try:
            for _ in range(3):
                tb.log_trade_signal(self._make_signal(), path=path)
            with open(path, "r", newline="") as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
            self.assertEqual(len(rows), 3)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_indicators_to_signal_conversion(self):
        ind = tb.Indicators(
            symbol="ETH/EUR",
            price=3000.0,
            price_change_pct=2.5,
            volume_change_pct=180.0,
            rsi=58.0,
            macd=1.5,
            macd_signal=0.8,
            macd_hist=0.7,
            bb_upper=3100.0,
            bb_middle=2900.0,
            bb_lower=2700.0,
            score=82.0,
            is_pump=True,
        )
        sig = tb.indicators_to_signal(ind)
        self.assertEqual(sig.symbol, "ETH/EUR")
        self.assertEqual(sig.price, 3000.0)
        self.assertTrue(sig.is_pump)


# ── analyze_symbol (mocked exchange) ──────────────────────────────────────────

class TestAnalyzeSymbol(unittest.TestCase):
    def _make_exchange(self, ohlcv_data):
        exchange = MagicMock(spec=ccxt.Exchange)
        exchange.fetch_ohlcv.return_value = ohlcv_data
        return exchange

    def test_returns_none_on_network_error(self):
        exchange = MagicMock(spec=ccxt.Exchange)
        exchange.fetch_ohlcv.side_effect = ccxt.NetworkError("timeout")
        result = tb.analyze_symbol(exchange, "BTC/EUR")
        self.assertIsNone(result)

    def test_returns_none_on_insufficient_data(self):
        exchange = self._make_exchange([[0, 1, 1, 1, 1, 100]] * 5)
        result = tb.analyze_symbol(exchange, "BTC/EUR")
        self.assertIsNone(result)

    def test_returns_indicators_with_valid_data(self):
        rows = _synthetic_ohlcv(n=80)
        exchange = self._make_exchange(rows)
        ind = tb.analyze_symbol(exchange, "BTC/EUR")
        self.assertIsNotNone(ind)
        self.assertEqual(ind.symbol, "BTC/EUR")
        self.assertGreater(ind.price, 0.0)
        self.assertGreaterEqual(ind.score, 0.0)
        self.assertLessEqual(ind.score, 100.0)

    def test_pump_detected_correctly(self):
        rows = _synthetic_ohlcv(n=80)
        # Force last candle to show big price increase and big volume spike
        # rows[-1] = [ts, open, high, low, close, volume]
        prev_close = rows[-2][4]
        rows[-1][4] = prev_close * 1.10   # +10% price
        # Make recent volumes much higher than baseline
        for i in range(-5, 0):
            rows[i][5] = rows[-10][5] * 4.0  # 4x baseline volume = 300% spike
        exchange = self._make_exchange(rows)
        ind = tb.analyze_symbol(exchange, "BTC/EUR")
        self.assertIsNotNone(ind)
        self.assertTrue(ind.is_pump)


# ── get_eur_pairs ──────────────────────────────────────────────────────────────

class TestGetEurPairs(unittest.TestCase):
    def test_filters_eur_pairs_only(self):
        exchange = MagicMock(spec=ccxt.Exchange)
        exchange.load_markets.return_value = {
            "BTC/EUR": {"quote": "EUR", "active": True, "spot": True},
            "ETH/EUR": {"quote": "EUR", "active": True, "spot": True},
            "BTC/USDT": {"quote": "USDT", "active": True, "spot": True},
            "BNB/EUR": {"quote": "EUR", "active": False, "spot": True},  # inactive
        }
        pairs = tb.get_eur_pairs(exchange)
        self.assertIn("BTC/EUR", pairs)
        self.assertIn("ETH/EUR", pairs)
        self.assertNotIn("BTC/USDT", pairs)
        self.assertNotIn("BNB/EUR", pairs)  # inactive

    def test_returns_empty_on_exchange_error(self):
        exchange = MagicMock(spec=ccxt.Exchange)
        exchange.load_markets.side_effect = ccxt.ExchangeError("down")
        pairs = tb.get_eur_pairs(exchange)
        self.assertEqual(pairs, [])


if __name__ == "__main__":
    unittest.main()
