from dataclasses import dataclass, field
from typing import Literal


ArtifactKind = Literal["python", "mql5", "markdown", "json", "yaml"]


@dataclass(slots=True)
class ArtifactRequest:
    relative_path: str
    kind: ArtifactKind
    summary: str
    context: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class IntentBlueprint:
    intent: str
    title: str
    description: str
    actions: list[str]
    artifact_requests: list[ArtifactRequest]
    risk_notes: list[str]
    strategy_name: str
    symbol: str
    timeframe: str


class AIBlueprintService:
    """Deterministic command interpreter for the first JARVIS foundation."""

    def interpret(self, message: str) -> IntentBlueprint:
        normalized = message.strip().lower()
        if len(normalized) < 3:
            raise ValueError("The command is too short for JARVIS to process.")

        strategy_name = self._derive_strategy_name(normalized)
        symbol = "XAUUSD" if any(token in normalized for token in ("gold", "xauusd")) else "EURUSD"
        timeframe = "M5" if "scalp" in normalized else "M15"

        actions = [
            "Parse command intent and extract strategy requirements",
            "Generate or update strategy source files inside the managed workspace",
            "Prepare MQL5 artifacts and an installation-ready expert advisor stub",
            "Build a backtesting plan with walk-forward and Monte Carlo checkpoints",
            "Apply portfolio and trade-level risk rules before any execution path",
        ]
        risk_notes = [
            "Only one active trade may be managed by the execution layer at a time.",
            "Opposing Buy and Sell positions are blocked by the MT5 safety wrapper.",
            "Trades should be closed once floating loss exceeds 20% of allowed threshold.",
            "Live deployment requires explicit MT5 credentials and terminal connectivity.",
        ]

        if "news filter" in normalized:
            return IntentBlueprint(
                intent="build_news_filter",
                title="Build news filter module",
                description="Create a reusable volatility and event filter that can pause strategy execution around macro releases.",
                actions=actions + ["Create a strategy guard for high-impact news windows"],
                artifact_requests=[
                    ArtifactRequest(
                        relative_path="strategies/generated/news_filter.py",
                        kind="python",
                        summary="Python news filter strategy guard",
                        context={"strategy_name": "news_filter", "symbol": symbol, "timeframe": timeframe},
                    ),
                    ArtifactRequest(
                        relative_path="strategies/generated/news_filter.md",
                        kind="markdown",
                        summary="News filter operating notes",
                        context={"strategy_name": "news_filter", "symbol": symbol, "timeframe": timeframe},
                    ),
                ],
                risk_notes=risk_notes,
                strategy_name="news_filter",
                symbol=symbol,
                timeframe=timeframe,
            )

        if "indikator" in normalized or "indicator" in normalized:
            return IntentBlueprint(
                intent="build_indicator",
                title="Create indicator package",
                description="Generate a custom indicator scaffold and supporting strategy notes for further iteration.",
                actions=actions + ["Generate an indicator-oriented MQL5 artifact"],
                artifact_requests=[
                    ArtifactRequest(
                        relative_path=f"mql5/generated/{strategy_name}_indicator.mq5",
                        kind="mql5",
                        summary="MQL5 custom indicator scaffold",
                        context={"strategy_name": strategy_name, "symbol": symbol, "timeframe": timeframe},
                    ),
                    ArtifactRequest(
                        relative_path=f"strategies/generated/{strategy_name}_indicator.md",
                        kind="markdown",
                        summary="Indicator design note",
                        context={"strategy_name": strategy_name, "symbol": symbol, "timeframe": timeframe},
                    ),
                ],
                risk_notes=risk_notes,
                strategy_name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
            )

        return IntentBlueprint(
            intent="build_strategy_bot",
            title=f"Create {strategy_name} trading bot",
            description="Generate a modular strategy scaffold, MQL5 expert advisor file, and deployment notes for JARVIS.",
            actions=actions + ["Generate strategy implementation scaffold for iterative optimization"],
            artifact_requests=[
                ArtifactRequest(
                    relative_path=f"strategies/generated/{strategy_name}.py",
                    kind="python",
                    summary="Python strategy scaffold",
                    context={"strategy_name": strategy_name, "symbol": symbol, "timeframe": timeframe},
                ),
                ArtifactRequest(
                    relative_path=f"mql5/generated/{strategy_name}.mq5",
                    kind="mql5",
                    summary="MQL5 expert advisor scaffold",
                    context={"strategy_name": strategy_name, "symbol": symbol, "timeframe": timeframe},
                ),
                ArtifactRequest(
                    relative_path=f"strategies/generated/{strategy_name}.md",
                    kind="markdown",
                    summary="Strategy operating specification",
                    context={"strategy_name": strategy_name, "symbol": symbol, "timeframe": timeframe},
                ),
            ],
            risk_notes=risk_notes,
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
        )

    def _derive_strategy_name(self, normalized: str) -> str:
        cleaned = normalized
        replacements = {
            "baue": "",
            "einen": "",
            "einen neuen": "",
            "erstelle": "",
            "neuen": "",
            "bot": "",
            "strategie": "",
            "aktuellen": "",
            "die": "",
            "den": "",
            "einen neuen indikator": "indicator",
        }
        for source, target in replacements.items():
            cleaned = cleaned.replace(source, target)

        tokens = [token.strip("-_ ") for token in cleaned.replace("/", " ").split() if token.strip("-_ ")]
        slug = "_".join(tokens[:4]) or "jarvis_strategy"
        return slug
