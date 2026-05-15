import pytest
from jarvis.risk_management.engine import RiskEngine
from jarvis.ai.chat_system import AIChatSystem
from jarvis.mql5.generator import MQL5Generator
import os

def test_risk_engine_locking():
    engine = RiskEngine(daily_drawdown_limit=4.0)
    # Simulate 5% drawdown
    is_valid, msg = engine.validate_trade(10000, 9500, 100)
    assert is_valid is False
    assert engine.locked is True

def test_lot_size_calculation():
    engine = RiskEngine()
    lot = engine.calculate_lot_size(10000, 1.0, 100) # 1% risk on 10k with 100 pip SL
    assert lot == 0.1

def test_ai_bot_creation():
    chat = AIChatSystem()
    resp = chat.process_command("Baue einen neuen Gold-Scalping-Bot")
    assert resp["status"] == "success"
    assert "NeuralBot_Gold-scalping-bot" in resp["message"]
    assert os.path.exists(resp["path"])

def test_mql5_generator():
    gen = MQL5Generator(output_dir="jarvis/tests/temp_mql5")
    path = gen.generate_ea("TestBot", "// logic")
    assert path.endswith("TestBot.mq5")
    with open(path, "r") as f:
        content = f.read()
        assert "TestBot" in content
    # Cleanup
    os.remove(path)
    os.rmdir("jarvis/tests/temp_mql5")
