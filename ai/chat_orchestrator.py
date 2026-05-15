from __future__ import annotations

from dataclasses import dataclass

from backend.app.schemas import ChatResponse, GeneratedFile, StrategySpec
from mql5.generator import MQL5Generator
from strategies.registry import StrategyRegistry


@dataclass(frozen=True)
class Intent:
    name: str
    strategy_archetype: str | None = None
    wants_mql5: bool = False
    wants_telegram: bool = False
    wants_backtest: bool = False
    wants_risk: bool = False


class ChatOrchestrator:
    """Maps operator chat instructions to safe file-generation actions."""

    def __init__(self, registry: StrategyRegistry, mql5_generator: MQL5Generator) -> None:
        self.registry = registry
        self.mql5_generator = mql5_generator

    def handle(self, message: str, *, dry_run: bool = True) -> ChatResponse:
        intent = self._classify(message)
        generated_files: list[GeneratedFile] = []
        actions: list[str] = []

        if intent.strategy_archetype:
            spec = self.registry.create_spec_from_prompt(message, intent.strategy_archetype)
            actions.append(f"Created strategy specification for {spec.name}.")
            generated_files.append(self._strategy_file(spec))

            if intent.wants_mql5:
                artifact = self.mql5_generator.create_expert_advisor(
                    strategy_name=spec.name,
                    symbol=spec.symbols[0] if spec.symbols else "XAUUSD",
                    timeframe=spec.timeframes[0] if spec.timeframes else "M5",
                    risk_percent=0.5,
                    include_trailing_stop="trailing" in message.lower(),
                )
                generated_files.append(
                    GeneratedFile(
                        path=f"mql5/generated/{artifact.filename}",
                        language="mql5",
                        purpose="Expert Advisor source",
                        content=artifact.content,
                    )
                )
                actions.append("Prepared MQL5 Expert Advisor source.")

        if intent.wants_telegram:
            generated_files.append(
                GeneratedFile(
                    path="telegram/generated_signal_bot.py",
                    language="python",
                    purpose="Telegram notification extension",
                    content=self._telegram_extension(),
                )
            )
            actions.append("Prepared Telegram signal bot extension.")

        if intent.wants_backtest:
            actions.append("Queued backtest with spread, slippage, walk-forward and Monte Carlo checks.")

        if intent.wants_risk:
            actions.append("Risk profile review requested; drawdown and loss-control rules will be prioritized.")

        if not actions:
            actions.append("No file changes required; returned architectural guidance.")

        return ChatResponse(
            intent=intent.name,
            summary=self._summary(intent, dry_run=dry_run),
            actions=actions,
            generated_files=generated_files,
            safety_notes=[
                "JARVIS does not promise winrates or guaranteed profitability.",
                "Live trading is disabled unless explicitly enabled through environment configuration.",
                "Risk engine blocks hedged buy/sell exposure and more than one open trade.",
            ],
        )

    def _classify(self, message: str) -> Intent:
        lower = message.lower()
        archetype = None
        if "ict" in lower:
            archetype = "ict"
        elif "smart money" in lower or "liquidity" in lower or "orderblock" in lower:
            archetype = "smart_money"
        elif "scalp" in lower or "gold" in lower:
            archetype = "scalping"
        elif "breakout" in lower:
            archetype = "breakout"
        elif "mean reversion" in lower:
            archetype = "mean_reversion"
        elif "momentum" in lower:
            archetype = "momentum"
        elif "trend" in lower:
            archetype = "trend_following"

        return Intent(
            name="strategy_generation" if archetype else "platform_command",
            strategy_archetype=archetype,
            wants_mql5=bool(archetype or "mql5" in lower or "ea" in lower or "indikator" in lower),
            wants_telegram="telegram" in lower,
            wants_backtest="test" in lower or "backtest" in lower or "optimi" in lower,
            wants_risk="drawdown" in lower or "risk" in lower or "risiko" in lower or "verlust" in lower,
        )

    @staticmethod
    def _strategy_file(spec: StrategySpec) -> GeneratedFile:
        content = (
            f"name: {spec.name}\n"
            f"archetype: {spec.archetype}\n"
            f"symbols: {', '.join(spec.symbols)}\n"
            f"timeframes: {', '.join(spec.timeframes)}\n"
            f"risk_profile: {spec.risk_profile}\n"
            "rules:\n"
            + "".join(f"  - {rule}\n" for rule in spec.rules)
        )
        return GeneratedFile(
            path=f"strategies/generated/{spec.name.lower().replace(' ', '_')}.yaml",
            language="yaml",
            purpose="Strategy specification",
            content=content,
        )

    @staticmethod
    def _telegram_extension() -> str:
        return (
            "from telegram.client import TelegramNotifier\n\n"
            "async def notify_signal(notifier: TelegramNotifier, signal: dict) -> None:\n"
            "    await notifier.send_trade_signal(signal)\n"
        )

    @staticmethod
    def _summary(intent: Intent, *, dry_run: bool) -> str:
        mode = "Dry-run" if dry_run else "Execution"
        if intent.strategy_archetype:
            return f"{mode}: prepared a {intent.strategy_archetype} strategy workflow."
        return f"{mode}: interpreted command and prepared platform actions."
