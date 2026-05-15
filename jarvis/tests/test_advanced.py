import pytest
from jarvis.strategies.factory import StrategyFactory
from jarvis.backend.routers.bot_manager import bot_manager, BotInstance
import datetime

def test_strategy_factory_output():
    ict_logic = StrategyFactory.get_ict_logic()
    assert "ICT Liquidity Sweep" in ict_logic

    smc_logic = StrategyFactory.get_smc_logic()
    assert "SMC Orderblock" in smc_logic

    gold_logic = StrategyFactory.get_gold_scalper_logic()
    assert "Gold Scalping" in gold_logic

def test_bot_manager_registration():
    bot = BotInstance(
        id="test_bot_1",
        name="Test Bot",
        strategy="ICT",
        status="active",
        created_at=datetime.datetime.now()
    )
    registered = bot_manager.register_bot(bot)
    assert registered.id == "test_bot_1"
    assert len(bot_manager.get_all_bots()) >= 1

def test_mql5_generator_with_factory():
    from jarvis.mql5.generator import MQL5Generator
    import os
    gen = MQL5Generator(output_dir="jarvis/tests/temp_gen")
    path = gen.generate_ea("FactoryBot", strategy_type="ict")
    assert os.path.exists(path)
    with open(path, "r") as f:
        content = f.read()
        assert "ICT Liquidity Sweep" in content
    os.remove(path)
    os.rmdir("jarvis/tests/temp_gen")
