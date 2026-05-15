"""
JARVIS Strategy System Package.

Provides trading strategy implementations, evaluation, and ranking tools
for the AI Trading Operating System.
"""


def __getattr__(name: str):
    if name == "BaseStrategy":
        from strategies.implementations.base_strategy import BaseStrategy
        return BaseStrategy
    if name == "StrategyEvaluator":
        from strategies.evaluation.strategy_evaluator import StrategyEvaluator
        return StrategyEvaluator
    raise AttributeError(f"module 'strategies' has no attribute {name!r}")


__all__ = ["BaseStrategy", "StrategyEvaluator"]
__version__ = "1.0.0"
