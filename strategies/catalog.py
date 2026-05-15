from dataclasses import dataclass


@dataclass(slots=True)
class StrategyProfile:
    name: str
    category: str
    preferred_markets: list[str]
    strengths: list[str]
    risks: list[str]


STRATEGY_CATALOG: list[StrategyProfile] = [
    StrategyProfile(
        name="gold-scalping",
        category="scalping",
        preferred_markets=["XAUUSD"],
        strengths=["Fast session-based entries", "Clear risk constraints"],
        risks=["Sensitive to spread expansion", "Needs strong execution quality"],
    ),
    StrategyProfile(
        name="ict-core",
        category="ict",
        preferred_markets=["EURUSD", "GBPUSD", "XAUUSD"],
        strengths=["Liquidity-focused structure", "Works with session logic"],
        risks=["Can overfit to narrative rules", "Requires strict confirmation"],
    ),
    StrategyProfile(
        name="mean-reversion-fx",
        category="mean_reversion",
        preferred_markets=["EURUSD", "USDJPY"],
        strengths=["Performs in rotational conditions", "Pairs well with volatility filters"],
        risks=["Weak during strong breakouts", "Requires disciplined stop placement"],
    ),
]
