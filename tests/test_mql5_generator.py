"""MQL5 generator smoke tests."""
from __future__ import annotations

from mql5.generator import MQL5Generator


def test_generate_ea_writes_file(tmp_path, monkeypatch):
    gen = MQL5Generator()
    path = gen.generate_ea(
        name="TestEA",
        symbol="EURUSD",
        timeframe="M15",
        strategy_kind="trend_following",
        parameters={"fast": 10, "slow": 30},
    )
    assert path.exists()
    text = path.read_text()
    assert "TestEA" in text
    assert "EURUSD" in text
    assert "PERIOD_M15" in text
    assert "trade.Buy" in text


def test_generate_indicator():
    gen = MQL5Generator()
    path = gen.generate_indicator(name="TestRSI", kind="rsi_divergence", parameters={"length": 21})
    assert path.exists()
    assert "indicator_chart_window" in path.read_text()
