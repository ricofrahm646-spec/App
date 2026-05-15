from __future__ import annotations

from backend.app.schemas import StrategySpec


class StrategyRegistry:
    """Factory and ranking service for strategy specifications."""

    def __init__(self) -> None:
        self._strategies: dict[str, StrategySpec] = {}

    def list_supported_archetypes(self) -> list[str]:
        return [
            "scalping",
            "ict",
            "smart_money",
            "liquidity_sweeps",
            "orderblocks",
            "trend_following",
            "mean_reversion",
            "breakouts",
            "momentum",
            "session_trading",
        ]

    def create_spec_from_prompt(self, prompt: str, archetype: str) -> StrategySpec:
        lower = prompt.lower()
        symbol = "XAUUSD" if "gold" in lower or "xau" in lower else "EURUSD"
        timeframe = "M5" if "scalp" in lower else "M15"
        name = self._name_from_archetype(archetype, symbol)
        spec = StrategySpec(
            name=name,
            archetype=archetype,
            symbols=[symbol],
            timeframes=[timeframe, "H1"],
            rules=self._rules_for(archetype),
            risk_profile="conservative",
        )
        self._strategies[name] = spec
        return spec

    def register(self, spec: StrategySpec) -> StrategySpec:
        self._strategies[spec.name] = spec
        return spec

    def list_strategies(self) -> list[StrategySpec]:
        return list(self._strategies.values())

    def score_strategy(self, metrics: dict[str, float]) -> float:
        profit_factor = metrics.get("profit_factor", 0.0)
        drawdown = metrics.get("max_drawdown_percent", 100.0)
        winrate = metrics.get("winrate", 0.0)
        overfit_penalty = metrics.get("overfit_penalty", 0.0)
        return round(profit_factor * 35 + winrate * 0.4 - drawdown * 0.8 - overfit_penalty * 20, 2)

    @staticmethod
    def _name_from_archetype(archetype: str, symbol: str) -> str:
        title = archetype.replace("_", " ").title().replace(" ", "")
        return f"Jarvis{symbol}{title}"

    @staticmethod
    def _rules_for(archetype: str) -> list[str]:
        rules = {
            "scalping": [
                "Trade only liquid sessions with spread filter enabled.",
                "Use fast/slow EMA confirmation and volatility filter.",
                "Exit immediately when risk engine detects abnormal loss.",
            ],
            "ict": [
                "Identify session liquidity pools and displacement candles.",
                "Confirm fair value gap retests before entries.",
                "Avoid entries into high-impact news windows.",
            ],
            "smart_money": [
                "Detect liquidity sweeps around prior session highs/lows.",
                "Validate orderblock reaction with momentum confirmation.",
                "Prioritize higher-timeframe market structure.",
            ],
            "breakout": [
                "Require range compression before breakout.",
                "Simulate slippage and spread expansion.",
                "Disable strategy after failed retest clusters.",
            ],
            "mean_reversion": [
                "Enter only at statistically stretched deviations.",
                "Avoid trending regimes detected by AI classifier.",
                "Scale risk down during high-volatility transitions.",
            ],
            "momentum": [
                "Trade in direction of volume-supported impulse.",
                "Use trailing stop after first risk unit in profit.",
                "Avoid late-session illiquidity.",
            ],
            "trend_following": [
                "Align lower-timeframe entries with higher-timeframe trend.",
                "Use pullbacks instead of chasing extended candles.",
                "Trail stop after structure break confirmation.",
            ],
        }
        return rules.get(archetype, ["Validate setup with multi-timeframe confirmation."])
