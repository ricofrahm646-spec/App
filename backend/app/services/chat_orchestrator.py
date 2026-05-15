from app.models.schemas import ChatCommandResponse, CommandAction
from app.services.file_generator import FileGenerationPlanner
from app.services.strategy_lab import StrategyLab


class ChatOrchestrator:
    """Transforms operator prompts into concrete build and integration steps."""

    def __init__(self) -> None:
        self._planner = FileGenerationPlanner()
        self._strategies = StrategyLab()

    def handle(self, prompt: str) -> ChatCommandResponse:
        prompt_lower = prompt.lower()

        actions = [
            CommandAction(
                kind="strategy",
                description=f"Analyze the request '{prompt}' and align it with supported strategy families.",
            ),
            CommandAction(
                kind="optimization",
                description="Prepare a backtesting and optimization loop before any live deployment.",
            ),
        ]
        warnings = [
            "JARVIS reports architecture and workflow plans honestly and does not promise profitability.",
            "Live trading must stay behind the risk engine guardrails.",
        ]

        if "telegram" in prompt_lower:
            actions.append(
                CommandAction(
                    kind="integration",
                    description="Route trade and risk events to the Telegram delivery service.",
                )
            )

        if "indikator" in prompt_lower or "indicator" in prompt_lower:
            actions.append(
                CommandAction(
                    kind="indicator",
                    description="Generate an MQL5 indicator template and map installation targets.",
                )
            )

        if any(token in prompt_lower for token in ["drawdown", "winrate", "optimiere"]):
            actions.append(
                CommandAction(
                    kind="risk",
                    description="Run drawdown diagnostics and rebalance sizing constraints.",
                )
            )

        strategy_names = [strategy.name for strategy in self._strategies.suggest(prompt)]
        summary = (
            "JARVIS classified the command, prepared modular actions and attached relevant artifacts. "
            f"Suggested strategy context: {', '.join(strategy_names)}."
        )

        return ChatCommandResponse(
            summary=summary,
            actions=actions,
            artifacts=self._planner.plan_artifacts(prompt),
            warnings=warnings,
        )
