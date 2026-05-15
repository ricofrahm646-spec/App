from dataclasses import dataclass


@dataclass(slots=True)
class StrategyBlueprint:
    name: str
    style: str
    description: str
    default_timeframes: list[str]
    risk_notes: list[str]


class StrategyLab:
    """Curates modular strategies that can be composed and improved over time."""

    def __init__(self) -> None:
        self._catalog = {
            "gold-scalping": StrategyBlueprint(
                name="gold-scalping",
                style="scalping",
                description="Short-horizon XAUUSD entries using session timing and volatility gates.",
                default_timeframes=["M1", "M5"],
                risk_notes=["Use spread filter before entry.", "Avoid news windows for aggressive sizing."],
            ),
            "ict-core": StrategyBlueprint(
                name="ict-core",
                style="ict",
                description="Liquidity sweeps, displacement and premium/discount array logic.",
                default_timeframes=["M5", "M15", "H1"],
                risk_notes=["Require liquidity event confirmation.", "Limit entries to defined sessions."],
            ),
            "trend-following": StrategyBlueprint(
                name="trend-following",
                style="momentum",
                description="Directional continuation model using structure breaks and volatility filters.",
                default_timeframes=["M15", "H1", "H4"],
                risk_notes=["Reduce size in choppy ranges.", "Trail only after structure confirmation."],
            ),
        }

    def suggest(self, prompt: str) -> list[StrategyBlueprint]:
        prompt_lower = prompt.lower()
        suggestions = [
            strategy
            for key, strategy in self._catalog.items()
            if any(token in key or token in strategy.style for token in prompt_lower.split())
        ]
        return suggestions or list(self._catalog.values())[:2]
