from backend.app.models.schemas import ChatRequest, ChatResponse, GeneratedFile, StrategySpec
from backend.app.services.mql5_generator import MQL5Generator
from backend.app.services.strategy_factory import StrategyFactory
from backend.app.services.tradingview_service import TradingViewService


class JarvisChatService:
    def __init__(self) -> None:
        self.strategy_factory = StrategyFactory()
        self.mql5_generator = MQL5Generator()
        self.tradingview = TradingViewService()

    def respond(self, request: ChatRequest) -> ChatResponse:
        message = request.message.lower()
        generated_files: list[GeneratedFile] = []
        actions: list[str] = []

        if any(keyword in message for keyword in ["bot", "strategie", "strategy", "indicator", "indikator"]):
            strategy = self.strategy_factory.from_prompt(request.message)
            generated_files.extend(
                [
                    self.mql5_generator.create_expert_advisor(strategy),
                    self.mql5_generator.create_indicator(strategy),
                    self.tradingview.pine_script(strategy),
                    self._strategy_manifest(strategy),
                ]
            )
            actions.extend(
                [
                    "strategy_spec_created",
                    "mql5_expert_advisor_created",
                    "mql5_indicator_created",
                    "tradingview_pine_script_created",
                ]
            )
            answer = (
                f"Ich habe die Strategie '{strategy.name}' als {strategy.strategy_type.value} "
                "entworfen. Die Ausführung bleibt an Risiko-Engine, Backtesting und MT5-Installation gebunden."
            )
            return ChatResponse(
                answer=answer,
                intent="generate_strategy",
                generated_files=generated_files,
                actions=actions,
            )

        if any(keyword in message for keyword in ["drawdown", "risk", "risiko", "verlust"]):
            return ChatResponse(
                answer=(
                    "Ich priorisiere Drawdown-Kontrolle: maximal ein Trade, kein Hedging, "
                    "Positionsgröße über Stop-Distanz und Notfall-Schließung ab 20% Verlust."
                ),
                intent="risk_optimization",
                actions=["review_risk_policy", "run_backtest_before_live"],
            )

        if any(keyword in message for keyword in ["telegram", "signal"]):
            return ChatResponse(
                answer="Telegram-Signale sind vorbereitet. Token und Chat-ID werden verschlüsselt gespeichert.",
                intent="configure_telegram",
                actions=["open_settings", "encrypt_token", "send_test_message"],
            )

        return ChatResponse(
            answer=(
                "Ich kann Strategien, MQL5-Dateien, TradingView-Skripte, Backtests, "
                "Risiko-Regeln und Telegram-Automationen erzeugen. Beschreibe den gewünschten Bot."
            ),
            intent="help",
            actions=["await_user_instruction"],
        )

    @staticmethod
    def _strategy_manifest(strategy: StrategySpec) -> GeneratedFile:
        content = strategy.model_dump_json(indent=2)
        strategy_id = StrategyFactory.strategy_id(strategy)
        return GeneratedFile(
            path=f"strategies/generated/{strategy_id}.json",
            language="json",
            purpose="Strategy manifest",
            content=content,
        )
