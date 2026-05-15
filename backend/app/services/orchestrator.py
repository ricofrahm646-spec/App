from app.core.config import Settings
from pathlib import Path
from app.schemas import ActionPlan, ChatCommandResponse, GeneratedArtifact, MetricCard, ModuleStatus, SystemOverview, TradeSnapshot
from app.services.ai_service import AIBlueprintService, ArtifactRequest, IntentBlueprint
from app.services.backtesting import BacktestingService
from app.services.file_generator import WorkspaceFileGenerator
from app.services.integrations import TelegramService, TradingViewService
from app.services.mql5_generator import Mql5Generator
from app.services.mt5_connector import SafeMt5Connector
from app.services.mt5_installer import Mt5InstallerService
from app.services.risk_engine import RiskEngine


class JarvisOrchestrator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ai_service = AIBlueprintService()
        self.file_generator = WorkspaceFileGenerator(settings)
        self.risk_engine = RiskEngine(settings)
        self.mql5_generator = Mql5Generator(settings)
        self.backtesting = BacktestingService()
        self.telegram = TelegramService(settings.telegram_bot_token, settings.telegram_chat_id)
        self.tradingview = TradingViewService(settings.tradingview_shared_secret)
        self.mt5 = SafeMt5Connector(settings, self.risk_engine)
        self.mt5_installer = Mt5InstallerService(settings)

    def process_command(self, message: str) -> ChatCommandResponse:
        blueprint = self.ai_service.interpret(message)
        created_files = self._materialize_blueprint(blueprint)
        backtesting_plan = self.backtesting.build_execution_plan(
            strategy_name=blueprint.strategy_name,
            symbol=blueprint.symbol,
            timeframe=blueprint.timeframe,
        )
        mql5_file_name = next(
            (
                Path(artifact.relative_path).name
                for artifact in blueprint.artifact_requests
                if artifact.kind == "mql5"
            ),
            f"{blueprint.strategy_name}.mq5",
        )
        installer_plan = self.mt5_installer.build_install_plan(
            file_name=mql5_file_name
        )
        plan = ActionPlan(
            title=blueprint.title,
            description=blueprint.description,
            actions=blueprint.actions + backtesting_plan + installer_plan,
            generated_artifacts=[
                GeneratedArtifact(
                    path=artifact.relative_path,
                    kind=artifact.kind,
                    summary=artifact.summary,
                )
                for artifact in blueprint.artifact_requests
            ],
            risk_notes=blueprint.risk_notes,
        )
        return ChatCommandResponse(
            intent=blueprint.intent,
            acknowledgement=f"JARVIS prepared the {blueprint.strategy_name} workflow and stored the generated artifacts.",
            plan=plan,
            created_files=created_files,
        )

    def system_overview(self) -> SystemOverview:
        return SystemOverview(
            metrics=[
                MetricCard(label="Balance", value="$100,000", detail="Paper environment baseline"),
                MetricCard(label="Equity", value="$100,000", detail="No live exposure configured"),
                MetricCard(label="Winrate", value="N/A", detail="No production results claimed"),
                MetricCard(label="Profit Factor", value="N/A", detail="Requires validated backtests"),
                MetricCard(label="Drawdown Limit", value="20%", detail="Emergency close threshold"),
                MetricCard(label="Open Trades", value="0", detail="One trade maximum by policy"),
            ],
            modules=[
                ModuleStatus(name="AI Planner", status="healthy", description="Intent-to-artifact orchestration available"),
                ModuleStatus(name="Risk Engine", status="healthy", description="Single-trade and max-loss policies active"),
                ModuleStatus(name="MT5 Connector", status="pending", description="Requires local terminal credentials"),
                ModuleStatus(name="MT5 Installer", status="pending", description="Requires terminal path and MetaEditor access"),
                ModuleStatus(name="MQL5 Generator", status="healthy", description="EA template rendering is available"),
                ModuleStatus(name="Telegram", status="pending", description="Token and chat ID must be configured"),
                ModuleStatus(name="TradingView", status="pending", description="Webhook secret required for activation"),
            ],
            open_trades=[
                TradeSnapshot(
                    symbol="EURUSD",
                    direction="buy",
                    entry_price=1.0,
                    stop_loss=0.995,
                    take_profit=1.01,
                    strategy="paper_preview",
                    state="draft",
                )
            ],
            active_strategy="No active live strategy",
            ai_status="Ready to generate strategy modules from chat commands",
        )

    def _materialize_blueprint(self, blueprint: IntentBlueprint) -> list[str]:
        created_files: list[str] = []
        for artifact in blueprint.artifact_requests:
            content = self._render_artifact(artifact, blueprint)
            created_files.append(self.file_generator.write_text(artifact.relative_path, content))
        return created_files

    def _render_artifact(self, artifact: ArtifactRequest, blueprint: IntentBlueprint) -> str:
        strategy_name = blueprint.strategy_name
        symbol = blueprint.symbol
        timeframe = blueprint.timeframe

        if artifact.kind == "python":
            return (
                "from dataclasses import dataclass\n\n\n"
                "@dataclass(slots=True)\n"
                f"class {self._class_name(strategy_name)}Strategy:\n"
                f"    symbol: str = \"{symbol}\"\n"
                f"    timeframe: str = \"{timeframe}\"\n"
                "    risk_per_trade: float = 0.01\n\n"
                "    def entry_signal(self, market_state: dict[str, float | str]) -> bool:\n"
                "        \"\"\"Replace this heuristic with validated logic before live usage.\"\"\"\n"
                "        return bool(market_state.get(\"trend_alignment\", False))\n\n"
                "    def exit_signal(self, position_state: dict[str, float | str]) -> bool:\n"
                "        return bool(position_state.get(\"risk_breach\", False))\n"
            )

        if artifact.kind == "mql5":
            return self.mql5_generator.render_expert_advisor(
                strategy_name=strategy_name,
                symbol=symbol,
                timeframe=timeframe,
            )

        if artifact.kind == "markdown":
            return (
                f"# {strategy_name}\n\n"
                f"- Symbol: {symbol}\n"
                f"- Timeframe: {timeframe}\n"
                f"- Intent: {blueprint.intent}\n\n"
                "## JARVIS execution notes\n\n"
                + "\n".join(f"- {step}" for step in blueprint.actions)
                + "\n\n## Backtesting\n\n"
                + self.backtesting.render_research_note(
                    strategy_name=strategy_name,
                    symbol=symbol,
                    timeframe=timeframe,
                )
            )

        raise ValueError(f"Unsupported artifact kind: {artifact.kind}")

    def _class_name(self, strategy_name: str) -> str:
        return "".join(part.capitalize() for part in strategy_name.split("_")) or "Jarvis"
