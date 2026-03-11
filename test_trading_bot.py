"""
Unit tests for trading_bot.py – 45+ tests covering:
  - Technical indicators (RSI, MACD, Bollinger Bands, volume change, price change)
  - Coin scorer
  - Pump detector
  - CSV logger (signals and trades)
  - Ranking helper
  - Risk management helpers (calculate_trade_amount)
  - Retry decorator
  - execute_trade integration (mocked exchange)
"""

from __future__ import annotations

import csv
import math
import os
import tempfile
import time
from typing import Any, Dict
from unittest.mock import MagicMock, patch, call

import pandas as pd
import pytest

import config
import trading_bot as tb


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _closes(values):
    return pd.Series(values, dtype=float)


def _volumes(values):
    return pd.Series(values, dtype=float)


# ---------------------------------------------------------------------------
# compute_rsi
# ---------------------------------------------------------------------------

class TestComputeRsi:
    def test_all_gains_returns_100(self):
        closes = _closes(list(range(1, 20)))  # monotonically rising
        assert tb.compute_rsi(closes) == 100.0

    def test_all_losses_returns_0(self):
        closes = _closes(list(range(20, 1, -1)))  # monotonically falling
        rsi = tb.compute_rsi(closes)
        assert rsi == pytest.approx(0.0, abs=1.0)

    def test_typical_value_in_range(self):
        # alternating 1-2-1-2-... should give RSI around 50
        vals = [10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11, 10, 11]
        rsi = tb.compute_rsi(_closes(vals))
        assert 0 < rsi < 100

    def test_insufficient_data_returns_nan(self):
        closes = _closes([1, 2, 3])
        assert math.isnan(tb.compute_rsi(closes, period=14))

    def test_custom_period(self):
        closes = _closes(list(range(1, 20)))
        rsi = tb.compute_rsi(closes, period=7)
        assert 0 <= rsi <= 100

    def test_exact_period_plus_one(self):
        closes = _closes([100] * 15)  # flat: avg_loss = 0
        rsi = tb.compute_rsi(closes, period=14)
        assert rsi == 100.0


# ---------------------------------------------------------------------------
# compute_macd
# ---------------------------------------------------------------------------

class TestComputeMacd:
    def _rising(self):
        return _closes([float(i) for i in range(1, 60)])

    def test_returns_three_floats(self):
        macd, sig, hist = tb.compute_macd(self._rising())
        for v in (macd, sig, hist):
            assert isinstance(v, float)

    def test_histogram_is_macd_minus_signal(self):
        macd, sig, hist = tb.compute_macd(self._rising())
        assert hist == pytest.approx(macd - sig, rel=1e-4)

    def test_insufficient_data_returns_nan_triple(self):
        closes = _closes(list(range(10)))
        m, s, h = tb.compute_macd(closes)
        assert all(math.isnan(v) for v in (m, s, h))

    def test_rising_series_positive_macd(self):
        macd, sig, _ = tb.compute_macd(self._rising())
        assert macd > sig  # fast EMA > slow EMA on rising series

    def test_falling_series_negative_macd(self):
        closes = _closes([float(60 - i) for i in range(60)])
        macd, sig, _ = tb.compute_macd(closes)
        assert macd < sig


# ---------------------------------------------------------------------------
# compute_bollinger_bands
# ---------------------------------------------------------------------------

class TestComputeBollingerBands:
    def test_upper_gt_middle_gt_lower(self):
        closes = _closes([10 + i * 0.1 for i in range(25)])
        upper, middle, lower = tb.compute_bollinger_bands(closes)
        assert upper > middle > lower

    def test_constant_series_zero_width(self):
        closes = _closes([5.0] * 25)
        upper, middle, lower = tb.compute_bollinger_bands(closes)
        assert upper == pytest.approx(middle, rel=1e-6)
        assert lower == pytest.approx(middle, rel=1e-6)

    def test_insufficient_data_returns_nan(self):
        closes = _closes([1.0] * 10)
        u, m, l = tb.compute_bollinger_bands(closes, period=20)
        assert all(math.isnan(v) for v in (u, m, l))

    def test_middle_is_rolling_mean(self):
        vals = list(range(1, 26))
        closes = _closes(vals)
        _, middle, _ = tb.compute_bollinger_bands(closes, period=20)
        expected_mean = sum(vals[-20:]) / 20
        assert middle == pytest.approx(expected_mean, rel=1e-4)

    def test_custom_std_multiplier(self):
        closes = _closes([10 + i * 0.1 for i in range(25)])
        _, m1, _ = tb.compute_bollinger_bands(closes, num_std=1.0)
        u2, m2, _ = tb.compute_bollinger_bands(closes, num_std=2.0)
        u3, _, _ = tb.compute_bollinger_bands(closes, num_std=3.0)
        assert u3 > u2 > m2 == pytest.approx(m1, rel=1e-6)


# ---------------------------------------------------------------------------
# compute_volume_change
# ---------------------------------------------------------------------------

class TestComputeVolumeChange:
    def test_double_volume_gives_100_pct(self):
        # baseline of 5 candles all = 100, last candle = 200
        vols = _volumes([100.0] * 5 + [200.0])
        assert tb.compute_volume_change(vols) == pytest.approx(100.0, rel=1e-4)

    def test_zero_last_volume_gives_negative_100(self):
        vols = _volumes([100.0] * 5 + [0.0])
        assert tb.compute_volume_change(vols) == pytest.approx(-100.0, rel=1e-4)

    def test_insufficient_data_returns_nan(self):
        vols = _volumes([100.0] * 3)
        assert math.isnan(tb.compute_volume_change(vols, baseline_candles=5))

    def test_zero_baseline_returns_nan(self):
        vols = _volumes([0.0] * 6)
        assert math.isnan(tb.compute_volume_change(vols))

    def test_custom_baseline_window(self):
        vols = _volumes([50.0, 50.0, 100.0])
        result = tb.compute_volume_change(vols, baseline_candles=2)
        assert result == pytest.approx(100.0, rel=1e-4)


# ---------------------------------------------------------------------------
# compute_price_change
# ---------------------------------------------------------------------------

class TestComputePriceChange:
    def test_price_doubled_gives_100(self):
        closes = _closes([1.0, 2.0])
        assert tb.compute_price_change(closes) == pytest.approx(100.0, rel=1e-4)

    def test_price_halved_gives_minus_50(self):
        closes = _closes([2.0, 1.0])
        assert tb.compute_price_change(closes) == pytest.approx(-50.0, rel=1e-4)

    def test_single_candle_returns_nan(self):
        assert math.isnan(tb.compute_price_change(_closes([1.0])))

    def test_zero_previous_price_returns_nan(self):
        assert math.isnan(tb.compute_price_change(_closes([0.0, 1.0])))


# ---------------------------------------------------------------------------
# score_coin
# ---------------------------------------------------------------------------

class TestScoreCoin:
    def _perfect(self):
        return dict(
            price_change_pct=config.SCORE_PRICE_CAP_PCT,
            volume_change_pct=config.SCORE_VOLUME_CAP_PCT,
            rsi=config.SCORE_RSI_HIGH,
            macd_line=1.0,
            macd_signal_val=0.5,
            macd_hist=0.5,
            price=105.0,
            bb_upper=110.0,
            bb_middle=100.0,
        )

    def test_perfect_inputs_near_100(self):
        s = tb.score_coin(**self._perfect())
        assert s >= 95.0

    def test_all_zero_inputs(self):
        # price_change_pct=0, volume=0, rsi=0, macd_line == macd_signal (no cross),
        # macd_hist=0 (neutral), price < bb_middle (below bands)
        s = tb.score_coin(0, 0, 0, -1.0, -1.0, 0.0, 90.0, 110.0, 100.0)
        assert s == pytest.approx(0.0, abs=1.0)

    def test_nan_input_returns_zero(self):
        kw = self._perfect()
        kw["rsi"] = float("nan")
        assert tb.score_coin(**kw) == 0.0

    def test_score_bounded_0_to_100(self):
        # extremes
        for price_c in (-10, 0, 5, 100):
            s = tb.score_coin(price_c, 300, 60, 1, 0.5, 0.5, 105, 110, 100)
            assert 0.0 <= s <= 100.0

    def test_higher_price_change_gives_higher_score(self):
        s_low = tb.score_coin(1.0, 100, 60, 1, 0.5, 0.5, 105, 110, 100)
        s_high = tb.score_coin(4.0, 100, 60, 1, 0.5, 0.5, 105, 110, 100)
        assert s_high > s_low

    def test_rsi_overbought_reduces_score(self):
        s_optimal = tb.score_coin(3, 200, 65, 1, 0.5, 0.5, 105, 110, 100)
        s_overbought = tb.score_coin(3, 200, 95, 1, 0.5, 0.5, 105, 110, 100)
        assert s_optimal > s_overbought

    def test_negative_macd_reduces_score(self):
        s_pos = tb.score_coin(3, 200, 60, 1.0, 0.5, 0.5, 105, 110, 100)
        s_neg = tb.score_coin(3, 200, 60, -1.0, -0.5, -0.5, 105, 110, 100)
        assert s_pos > s_neg


# ---------------------------------------------------------------------------
# detect_pump
# ---------------------------------------------------------------------------

class TestDetectPump:
    def test_both_thresholds_met(self):
        assert tb.detect_pump(
            config.PUMP_MIN_PRICE_CHANGE_PCT,
            config.PUMP_MIN_VOLUME_SPIKE_PCT,
        ) is True

    def test_only_price_threshold_met(self):
        assert tb.detect_pump(config.PUMP_MIN_PRICE_CHANGE_PCT, 0.0) is False

    def test_only_volume_threshold_met(self):
        assert tb.detect_pump(0.0, config.PUMP_MIN_VOLUME_SPIKE_PCT) is False

    def test_neither_threshold_met(self):
        assert tb.detect_pump(0.0, 0.0) is False

    def test_nan_inputs_returns_false(self):
        assert tb.detect_pump(float("nan"), 200.0) is False
        assert tb.detect_pump(3.0, float("nan")) is False

    def test_at_exact_thresholds(self):
        assert tb.detect_pump(
            config.PUMP_MIN_PRICE_CHANGE_PCT,
            config.PUMP_MIN_VOLUME_SPIKE_PCT,
        ) is True

    def test_above_thresholds(self):
        assert tb.detect_pump(10.0, 500.0) is True


# ---------------------------------------------------------------------------
# CSV loggers
# ---------------------------------------------------------------------------

class TestLogSignal:
    def test_creates_file_with_header(self, tmp_path):
        path = str(tmp_path / "signals.csv")
        sig = {k: "x" for k in tb.SIGNALS_FIELDNAMES}
        tb.log_signal(sig, path=path)
        assert os.path.exists(path)
        with open(path) as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames == tb.SIGNALS_FIELDNAMES

    def test_appends_rows(self, tmp_path):
        path = str(tmp_path / "signals.csv")
        for i in range(3):
            tb.log_signal({"symbol": f"COIN{i}/EUR", "score": i * 10}, path=path)
        with open(path) as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 3
        assert rows[1]["symbol"] == "COIN1/EUR"

    def test_missing_keys_written_as_empty(self, tmp_path):
        path = str(tmp_path / "signals.csv")
        tb.log_signal({"symbol": "X/EUR"}, path=path)
        with open(path) as fh:
            rows = list(csv.DictReader(fh))
        assert rows[0]["rsi"] == ""


class TestLogTrade:
    def test_creates_file_with_header(self, tmp_path):
        path = str(tmp_path / "trades.csv")
        trade = {k: "x" for k in tb.TRADES_FIELDNAMES}
        tb.log_trade(trade, path=path)
        with open(path) as fh:
            reader = csv.DictReader(fh)
            assert reader.fieldnames == tb.TRADES_FIELDNAMES

    def test_appends_multiple_trades(self, tmp_path):
        path = str(tmp_path / "trades.csv")
        for i in range(5):
            tb.log_trade({"symbol": f"C{i}/EUR", "status": "open"}, path=path)
        with open(path) as fh:
            rows = list(csv.DictReader(fh))
        assert len(rows) == 5

    def test_trade_fields_preserved(self, tmp_path):
        path = str(tmp_path / "trades.csv")
        trade = {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "symbol": "BTC/EUR",
            "score": 92.5,
            "entry_price": 30000.0,
            "stop_loss_price": 29400.0,
            "take_profit_price": 32100.0,
            "amount_eur": 500.0,
            "amount_coin": 0.016667,
            "exit_price": "",
            "pnl_eur": "",
            "status": "open",
        }
        tb.log_trade(trade, path=path)
        with open(path) as fh:
            rows = list(csv.DictReader(fh))
        assert rows[0]["entry_price"] == "30000.0"
        assert rows[0]["status"] == "open"


# ---------------------------------------------------------------------------
# rank_coins
# ---------------------------------------------------------------------------

class TestRankCoins:
    def _signals(self, scores):
        return [{"symbol": f"C{i}/EUR", "score": s} for i, s in enumerate(scores)]

    def test_returns_top_n(self):
        signals = self._signals([90, 80, 70, 60, 50])
        top = tb.rank_coins(signals, top_n=3)
        assert len(top) == 3
        assert top[0]["score"] == 90

    def test_returns_all_if_fewer_than_n(self):
        signals = self._signals([85, 75])
        top = tb.rank_coins(signals, top_n=5)
        assert len(top) == 2

    def test_empty_signals_returns_empty(self):
        assert tb.rank_coins([], top_n=3) == []

    def test_preserves_order(self):
        signals = self._signals([95, 88, 77, 66])
        top = tb.rank_coins(signals, top_n=3)
        scores = [s["score"] for s in top]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# calculate_trade_amount
# ---------------------------------------------------------------------------

class TestCalculateTradeAmount:
    def test_score_100_uses_max_pct(self):
        amount = tb.calculate_trade_amount(1000.0, 100.0)
        assert amount == pytest.approx(1000.0 * config.TRADE_BALANCE_MAX_PCT, rel=1e-4)

    def test_score_0_uses_min_pct(self):
        amount = tb.calculate_trade_amount(1000.0, 0.0)
        assert amount == pytest.approx(1000.0 * config.TRADE_BALANCE_MIN_PCT, rel=1e-4)

    def test_score_50_between_min_and_max(self):
        amount = tb.calculate_trade_amount(1000.0, 50.0)
        min_a = 1000.0 * config.TRADE_BALANCE_MIN_PCT
        max_a = 1000.0 * config.TRADE_BALANCE_MAX_PCT
        assert min_a < amount < max_a

    def test_result_does_not_exceed_balance(self):
        amount = tb.calculate_trade_amount(500.0, 100.0)
        assert amount <= 500.0

    def test_zero_balance_gives_zero(self):
        assert tb.calculate_trade_amount(0.0, 80.0) == 0.0

    def test_score_above_100_clamped(self):
        amount_100 = tb.calculate_trade_amount(1000.0, 100.0)
        amount_200 = tb.calculate_trade_amount(1000.0, 200.0)
        assert amount_100 == amount_200


# ---------------------------------------------------------------------------
# retry_on_error decorator
# ---------------------------------------------------------------------------

class TestRetryOnError:
    def test_succeeds_on_first_try(self):
        call_count = {"n": 0}

        @tb.retry_on_error(max_attempts=3, delay_seconds=0)
        def fn():
            call_count["n"] += 1
            return "ok"

        result = fn()
        assert result == "ok"
        assert call_count["n"] == 1

    def test_retries_and_eventually_succeeds(self):
        import ccxt

        attempts = {"n": 0}

        @tb.retry_on_error(max_attempts=3, delay_seconds=0)
        def fn():
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise ccxt.NetworkError("temporary")
            return "ok"

        result = fn()
        assert result == "ok"
        assert attempts["n"] == 3

    def test_raises_after_max_attempts(self):
        import ccxt

        @tb.retry_on_error(max_attempts=2, delay_seconds=0)
        def fn():
            raise ccxt.ExchangeError("persistent")

        with pytest.raises(ccxt.ExchangeError):
            fn()

    def test_non_api_exception_not_retried(self):
        call_count = {"n": 0}

        @tb.retry_on_error(max_attempts=3, delay_seconds=0)
        def fn():
            call_count["n"] += 1
            raise ValueError("not an API error")

        with pytest.raises(ValueError):
            fn()
        assert call_count["n"] == 1


# ---------------------------------------------------------------------------
# execute_trade (integration with mocked exchange)
# ---------------------------------------------------------------------------

class TestExecuteTrade:
    def _make_exchange(self, eur_balance=1000.0, entry_price=100.0):
        exchange = MagicMock()
        exchange.fetch_balance.return_value = {
            "EUR": {"free": eur_balance}
        }
        exchange.createMarketBuyOrderWithCost.return_value = {
            "average": entry_price,
            "filled": eur_balance * config.TRADE_BALANCE_MAX_PCT / entry_price,
            "amount": eur_balance * config.TRADE_BALANCE_MAX_PCT / entry_price,
        }
        # OCO orders go through exchange.create_order in place_oco_sell
        exchange.create_order.return_value = {"id": "oco123"}
        return exchange

    def _signal(self, score=90.0):
        return {
            "symbol": "BTC/EUR",
            "price": 100.0,
            "score": score,
        }

    def test_returns_trade_record(self, tmp_path):
        exchange = self._make_exchange()
        sig = self._signal()
        with patch.object(tb, "log_trade") as mock_log:
            result = tb.execute_trade(exchange, sig)
        assert result is not None
        assert result["symbol"] == "BTC/EUR"
        assert result["status"] == "open"

    def test_stop_loss_below_entry(self, tmp_path):
        exchange = self._make_exchange(entry_price=100.0)
        result = tb.execute_trade(exchange, self._signal())
        assert result is not None
        assert result["stop_loss_price"] < result["entry_price"]

    def test_take_profit_above_entry(self):
        exchange = self._make_exchange(entry_price=100.0)
        result = tb.execute_trade(exchange, self._signal())
        assert result is not None
        assert result["take_profit_price"] > result["entry_price"]

    def test_no_eur_balance_returns_none(self):
        exchange = self._make_exchange(eur_balance=0.0)
        result = tb.execute_trade(exchange, self._signal())
        assert result is None

    def test_buy_order_no_price_returns_none_and_logs_error(self, tmp_path):
        exchange = self._make_exchange()
        exchange.fetch_balance.return_value = {"EUR": {"free": 1000.0}}
        # Return an order with no price data
        exchange.createMarketBuyOrderWithCost.return_value = {"filled": 0.5}
        with patch.object(tb, "log_trade") as mock_log:
            result = tb.execute_trade(exchange, self._signal())
        assert result is None
        mock_log.assert_called_once()
        call_args = mock_log.call_args[0][0]
        assert "error" in call_args["status"]

    def test_buy_order_failure_returns_none_and_logs_error(self, tmp_path):
        import ccxt

        exchange = self._make_exchange()
        exchange.fetch_balance.return_value = {"EUR": {"free": 1000.0}}
        exchange.createMarketBuyOrderWithCost.side_effect = ccxt.ExchangeError("order fail")
        with patch.object(tb, "log_trade") as mock_log:
            result = tb.execute_trade(exchange, self._signal())
        assert result is None
        mock_log.assert_called_once()
        call_args = mock_log.call_args[0][0]
        assert "error" in call_args["status"]

    def test_trade_is_logged(self):
        exchange = self._make_exchange()
        with patch.object(tb, "log_trade") as mock_log:
            tb.execute_trade(exchange, self._signal())
        mock_log.assert_called()


# ---------------------------------------------------------------------------
# scan_pair (unit-level with mocked fetch_ohlcv)
# ---------------------------------------------------------------------------

class TestScanPair:
    def _make_df(self, n=50):
        import numpy as np

        closes = np.linspace(100, 110, n)
        volumes = np.ones(n) * 1000
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="5min", tz="UTC"),
            "open": closes,
            "high": closes + 0.5,
            "low": closes - 0.5,
            "close": closes,
            "volume": volumes,
        })
        return df

    def test_returns_signal_dict(self):
        exchange = MagicMock()
        df = self._make_df()
        with patch.object(tb, "fetch_ohlcv", return_value=df):
            result = tb.scan_pair(exchange, "BTC/EUR")
        assert result is not None
        assert result["symbol"] == "BTC/EUR"
        assert 0 <= result["score"] <= 100

    def test_returns_none_for_empty_df(self):
        exchange = MagicMock()
        with patch.object(tb, "fetch_ohlcv", return_value=None):
            result = tb.scan_pair(exchange, "BTC/EUR")
        assert result is None

    def test_contains_all_expected_keys(self):
        exchange = MagicMock()
        df = self._make_df()
        with patch.object(tb, "fetch_ohlcv", return_value=df):
            result = tb.scan_pair(exchange, "BTC/EUR")
        for key in tb.SIGNALS_FIELDNAMES:
            assert key in result
