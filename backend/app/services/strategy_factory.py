import re

from backend.app.models.schemas import StrategySpec, StrategyType


class StrategyFactory:
    KEYWORDS: dict[str, StrategyType] = {
        "gold": StrategyType.SCALPING,
        "xau": StrategyType.SCALPING,
        "scalp": StrategyType.SCALPING,
        "ict": StrategyType.ICT,
        "smart money": StrategyType.SMART_MONEY,
        "liquidity": StrategyType.LIQUIDITY_SWEEP,
        "orderblock": StrategyType.ORDERBLOCK,
        "trend": StrategyType.TREND_FOLLOWING,
        "mean": StrategyType.MEAN_REVERSION,
        "breakout": StrategyType.BREAKOUT,
        "momentum": StrategyType.MOMENTUM,
        "session": StrategyType.SESSION,
    }

    def from_prompt(self, prompt: str) -> StrategySpec:
        normalized = prompt.lower()
        strategy_type = StrategyType.MOMENTUM
        for keyword, candidate in self.KEYWORDS.items():
            if keyword in normalized:
                strategy_type = candidate
                break

        symbols = ["XAUUSD"] if any(token in normalized for token in ["gold", "xau"]) else ["EURUSD"]
        if "forex" in normalized:
            symbols = ["EURUSD", "GBPUSD", "USDJPY"]

        name = self._name_from_prompt(prompt, strategy_type)
        return StrategySpec(
            name=name,
            strategy_type=strategy_type,
            symbols=symbols,
            timeframes=["M5", "M15"],
            description=(
                f"Generated {strategy_type.value} strategy with explicit SL/TP, "
                "single-position execution and risk-engine gating."
            ),
            parameters={
                "session_filter": "london_new_york_overlap",
                "confirmation_candles": 2,
                "max_spread_points": 25,
                "trailing_stop": "atr_based" if "trailing" in normalized else "disabled",
            },
        )

    @staticmethod
    def strategy_id(strategy: StrategySpec) -> str:
        value = re.sub(r"[^a-zA-Z0-9]+", "_", strategy.name).strip("_").lower()
        return value or "jarvis_strategy"

    @staticmethod
    def _name_from_prompt(prompt: str, strategy_type: StrategyType) -> str:
        words = [word.strip(".,!?") for word in prompt.split() if len(word.strip(".,!?")) > 2]
        compact = " ".join(words[:5]).title() or strategy_type.value.replace("_", " ").title()
        return f"Jarvis {compact}"
