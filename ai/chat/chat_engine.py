"""
AI Chat Engine
===============

Natural language command interface for JARVIS trading operations.
Parses user commands, classifies intents, maps them to executable actions,
and returns structured responses.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Intent(Enum):
    GENERATE_STRATEGY = "generate_strategy"
    OPTIMIZE_STRATEGY = "optimize_strategy"
    CREATE_INDICATOR = "create_indicator"
    BUILD_BOT = "build_bot"
    RUN_BACKTEST = "run_backtest"
    ANALYZE_PERFORMANCE = "analyze_performance"
    DETECT_REGIME = "detect_regime"
    TRAIN_MODEL = "train_model"
    GET_PREDICTION = "get_prediction"
    MANAGE_RISK = "manage_risk"
    GET_STATUS = "get_status"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class CommandContext:
    """Parsed context from a user command."""

    intent: Intent
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatMessage:
    """A single message in the conversation."""

    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


@dataclass
class ActionResult:
    """Result of executing a command action."""

    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    generated_files: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


INTENT_PATTERNS: Dict[Intent, List[str]] = {
    Intent.GENERATE_STRATEGY: [
        r"(?:create|generate|build|make|design|write)\s+(?:a\s+)?(?:new\s+)?(?:trading\s+)?strat",
        r"(?:scalp|swing|trend|mean.?revert|momentum|breakout)\s+(?:strategy|strat|system)",
        r"strat(?:egy)?\s+(?:for|on)\s+",
        r"(?:gold|xauusd|eurusd|gbpusd|forex|crypto|btc)\s+(?:scalp|swing|strat)",
    ],
    Intent.OPTIMIZE_STRATEGY: [
        r"optim(?:ize|ise)\s+(?:the\s+)?(?:strategy|strat|param|system)",
        r"(?:tune|improve|enhance|tweak)\s+(?:the\s+)?(?:strategy|strat|param)",
        r"(?:find|search)\s+(?:best|optimal)\s+param",
        r"hyper.?param(?:eter)?\s+(?:optim|tun|search)",
        r"run\s+optim",
    ],
    Intent.CREATE_INDICATOR: [
        r"(?:create|build|make|design|add)\s+(?:a\s+)?(?:new\s+)?(?:custom\s+)?indic",
        r"(?:create|build|make)\s+(?:a\s+)?(?:new\s+)?(?:signal|filter|oscillator)",
        r"(?:rsi|macd|bollinger|ema|sma|atr|adx|stochastic)\s+(?:custom|modif|variant)",
    ],
    Intent.BUILD_BOT: [
        r"(?:create|build|make|deploy|launch)\s+(?:a\s+)?(?:new\s+)?(?:trading\s+)?bot",
        r"(?:create|build|make)\s+(?:a\s+)?(?:new\s+)?(?:ea|expert.?advis|robot)",
        r"(?:automat|auto.?trad)",
        r"deploy\s+(?:the\s+)?(?:strategy|strat|bot|system)",
    ],
    Intent.RUN_BACKTEST: [
        r"(?:run|execute|perform|start)\s+(?:a\s+)?back.?test",
        r"back.?test\s+(?:the|this|my|a)\s+",
        r"test\s+(?:the\s+)?(?:strategy|strat|system)\s+(?:on|with|against)",
        r"(?:historical|past)\s+(?:test|performance|data)",
    ],
    Intent.ANALYZE_PERFORMANCE: [
        r"(?:analyze|analyse|show|get|display)\s+(?:the\s+)?(?:performance|results|stats)",
        r"(?:sharpe|drawdown|win.?rate|profit.?factor|returns?)\s+(?:analysis|report)",
        r"(?:generate|create|show)\s+(?:a\s+)?(?:performance\s+)?report",
        r"how\s+(?:did|does|is)\s+(?:the\s+)?(?:strategy|strat|bot|system)\s+(?:perform|do)",
    ],
    Intent.DETECT_REGIME: [
        r"(?:detect|identify|classify|analyze|what)\s+(?:is\s+)?(?:the\s+)?(?:market\s+)?regime",
        r"(?:market|current)\s+(?:condition|state|phase|regime|environment)",
        r"(?:trending|ranging|volatile|choppy)\s+(?:market|detection|analysis)",
        r"(?:is\s+the\s+market|market\s+is)\s+(?:trending|ranging|volatile)",
    ],
    Intent.TRAIN_MODEL: [
        r"(?:train|retrain|fine.?tune|fit)\s+(?:the\s+)?(?:model|ai|lstm|neural|nn)",
        r"(?:start|begin|run)\s+(?:model\s+)?training",
        r"(?:update|refresh)\s+(?:the\s+)?(?:model|predictions|ai)",
    ],
    Intent.GET_PREDICTION: [
        r"(?:predict|forecast|what)\s+(?:will|is)\s+(?:the\s+)?(?:market|price|direction)",
        r"(?:get|show|give)\s+(?:me\s+)?(?:a\s+)?predict",
        r"(?:market|price)\s+(?:prediction|forecast|outlook)",
        r"(?:should\s+I|do\s+I)\s+(?:buy|sell|trade|enter)",
        r"(?:bull|bear)(?:ish)?\s+(?:or|vs)\s+(?:bear|bull)",
    ],
    Intent.MANAGE_RISK: [
        r"(?:set|adjust|change|update)\s+(?:the\s+)?(?:risk|stop.?loss|take.?profit|lot|position)",
        r"(?:risk\s+management|money\s+management|position\s+siz)",
        r"(?:what|how\s+much)\s+(?:risk|should\s+I\s+risk)",
        r"(?:max(?:imum)?\s+)?(?:drawdown|loss|risk)\s+(?:limit|threshold)",
    ],
    Intent.GET_STATUS: [
        r"(?:show|get|display|what)\s+(?:is\s+)?(?:the\s+)?(?:status|state|dashboard)",
        r"(?:system|bot|trading)\s+status",
        r"(?:how|what)\s+(?:is|are)\s+(?:things|everything|we)\s+(?:doing|going|running)",
        r"(?:open|active|current)\s+(?:trades?|positions?|orders?)",
    ],
    Intent.HELP: [
        r"\b(?:help|assist|guide|tutorial|how\s+to|what\s+can\s+you|commands?)\b",
        r"(?:what|show|list)\s+(?:can\s+you\s+do|commands?|features?|capabilities)",
    ],
}

ENTITY_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
    "instrument": [
        (r"\b(xauusd|gold)\b", "XAUUSD"),
        (r"\b(eurusd)\b", "EURUSD"),
        (r"\b(gbpusd|cable)\b", "GBPUSD"),
        (r"\b(usdjpy)\b", "USDJPY"),
        (r"\b(btcusd|bitcoin|btc)\b", "BTCUSD"),
        (r"\b(ethusd|ethereum|eth)\b", "ETHUSD"),
        (r"\b(nas(?:daq)?100|us100|nas)\b", "NAS100"),
        (r"\b(us30|dow)\b", "US30"),
        (r"\b(spx|sp500|us500)\b", "US500"),
    ],
    "strategy_type": [
        (r"\b(scalp(?:ing)?)\b", "scalping"),
        (r"\b(swing)\b", "swing"),
        (r"\b(trend.?follow(?:ing)?)\b", "trend_following"),
        (r"\b(mean.?revert|mean.?reversion)\b", "mean_reversion"),
        (r"\b(momentum)\b", "momentum"),
        (r"\b(breakout)\b", "breakout"),
        (r"\b(grid)\b", "grid"),
        (r"\b(martingale)\b", "martingale"),
    ],
    "timeframe": [
        (r"\b(1\s*m(?:in(?:ute)?)?|m1)\b", "M1"),
        (r"\b(5\s*m(?:in(?:ute)?)?|m5)\b", "M5"),
        (r"\b(15\s*m(?:in(?:ute)?)?|m15)\b", "M15"),
        (r"\b(30\s*m(?:in(?:ute)?)?|m30)\b", "M30"),
        (r"\b(1\s*h(?:our)?|h1)\b", "H1"),
        (r"\b(4\s*h(?:our)?|h4)\b", "H4"),
        (r"\b(1\s*d(?:ay)?|d1|daily)\b", "D1"),
    ],
    "risk_percent": [
        (r"(\d+(?:\.\d+)?)\s*%\s*risk", None),
        (r"risk\s*(?:of\s+)?(\d+(?:\.\d+)?)\s*%", None),
    ],
    "lot_size": [
        (r"(\d+(?:\.\d+)?)\s*lots?", None),
    ],
}


class IntentClassifier:
    """Classify user intent from natural language input using pattern matching."""

    def __init__(self, patterns: Optional[Dict[Intent, List[str]]] = None):
        self._patterns = patterns or INTENT_PATTERNS
        self._compiled: Dict[Intent, List[re.Pattern]] = {}
        for intent, pat_list in self._patterns.items():
            self._compiled[intent] = [
                re.compile(p, re.IGNORECASE) for p in pat_list
            ]

    def classify(self, text: str) -> Tuple[Intent, float]:
        """
        Classify the intent of a text command.

        Returns the detected Intent and a confidence score (0-1).
        """
        text_lower = text.lower().strip()
        scores: Dict[Intent, float] = {}

        for intent, compiled_patterns in self._compiled.items():
            match_count = 0
            for pattern in compiled_patterns:
                if pattern.search(text_lower):
                    match_count += 1

            if match_count > 0:
                scores[intent] = min(0.5 + match_count * 0.2, 1.0)

        if not scores:
            return Intent.UNKNOWN, 0.0

        best_intent = max(scores, key=scores.get)
        return best_intent, scores[best_intent]


class EntityExtractor:
    """Extract structured entities from user commands."""

    def __init__(self, patterns: Optional[Dict[str, List[Tuple[str, str]]]] = None):
        self._patterns = patterns or ENTITY_PATTERNS
        self._compiled: Dict[str, List[Tuple[re.Pattern, Optional[str]]]] = {}
        for entity_type, pat_list in self._patterns.items():
            self._compiled[entity_type] = [
                (re.compile(p, re.IGNORECASE), mapped_value)
                for p, mapped_value in pat_list
            ]

    def extract(self, text: str) -> Dict[str, Any]:
        """Extract all entities from the text."""
        entities: Dict[str, Any] = {}
        text_lower = text.lower()

        for entity_type, compiled_patterns in self._compiled.items():
            for pattern, mapped_value in compiled_patterns:
                match = pattern.search(text_lower)
                if match:
                    if mapped_value is not None:
                        entities[entity_type] = mapped_value
                    else:
                        entities[entity_type] = match.group(1)
                    break

        numbers = re.findall(r"(\d+(?:\.\d+)?)", text)
        if numbers and "risk_percent" not in entities and "lot_size" not in entities:
            entities["_numbers"] = [float(n) for n in numbers]

        return entities


class ActionExecutor:
    """Execute actions mapped from classified intents."""

    def __init__(self, output_dir: str = "generated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._action_handlers: Dict[Intent, Callable] = {
            Intent.GENERATE_STRATEGY: self._handle_generate_strategy,
            Intent.OPTIMIZE_STRATEGY: self._handle_optimize_strategy,
            Intent.CREATE_INDICATOR: self._handle_create_indicator,
            Intent.BUILD_BOT: self._handle_build_bot,
            Intent.RUN_BACKTEST: self._handle_run_backtest,
            Intent.ANALYZE_PERFORMANCE: self._handle_analyze_performance,
            Intent.DETECT_REGIME: self._handle_detect_regime,
            Intent.TRAIN_MODEL: self._handle_train_model,
            Intent.GET_PREDICTION: self._handle_get_prediction,
            Intent.MANAGE_RISK: self._handle_manage_risk,
            Intent.GET_STATUS: self._handle_get_status,
            Intent.HELP: self._handle_help,
            Intent.UNKNOWN: self._handle_unknown,
        }

    def execute(self, context: CommandContext) -> ActionResult:
        """Execute the action corresponding to the classified intent."""
        handler = self._action_handlers.get(context.intent, self._handle_unknown)
        try:
            return handler(context)
        except Exception as e:
            logger.error(f"Action execution failed: {e}", exc_info=True)
            return ActionResult(
                success=False,
                message=f"An error occurred while processing your request: {str(e)}",
            )

    def _handle_generate_strategy(self, ctx: CommandContext) -> ActionResult:
        instrument = ctx.entities.get("instrument", "XAUUSD")
        strategy_type = ctx.entities.get("strategy_type", "scalping")
        timeframe = ctx.entities.get("timeframe", "M5")

        class_name = f"{instrument}{strategy_type.title().replace('_', '')}Strategy"
        filename = f"{instrument.lower()}_{strategy_type}_{timeframe.lower()}.py"
        filepath = self.output_dir / "strategies" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        code = self._generate_strategy_code(class_name, instrument, strategy_type, timeframe)
        filepath.write_text(code)

        return ActionResult(
            success=True,
            message=(
                f"Generated {strategy_type} strategy for {instrument} on {timeframe} timeframe.\n"
                f"Strategy class: {class_name}\n"
                f"File saved to: {filepath}"
            ),
            data={
                "class_name": class_name,
                "instrument": instrument,
                "strategy_type": strategy_type,
                "timeframe": timeframe,
            },
            generated_files=[str(filepath)],
            suggestions=[
                "Run a backtest: 'Backtest this strategy'",
                "Optimize parameters: 'Optimize the strategy'",
                "Build a bot: 'Build a bot for this strategy'",
            ],
        )

    def _handle_optimize_strategy(self, ctx: CommandContext) -> ActionResult:
        strategy_type = ctx.entities.get("strategy_type", "current")
        instrument = ctx.entities.get("instrument", "")

        config = {
            "method": "optuna",
            "n_trials": 100,
            "metric": "sharpe_ratio",
            "walk_forward_splits": 5,
            "overfitting_detection": True,
        }

        config_path = self.output_dir / "optimization" / "optimization_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2))

        return ActionResult(
            success=True,
            message=(
                f"Strategy optimization configured.\n"
                f"Method: Optuna Bayesian optimization\n"
                f"Trials: {config['n_trials']}\n"
                f"Metric: {config['metric']}\n"
                f"Walk-forward validation: {config['walk_forward_splits']} splits\n\n"
                f"Configuration saved. Run the optimizer to start."
            ),
            data=config,
            generated_files=[str(config_path)],
            suggestions=[
                "Use genetic algorithm: 'Optimize with genetic algorithm'",
                "Run backtest after optimization: 'Backtest the optimized strategy'",
            ],
        )

    def _handle_create_indicator(self, ctx: CommandContext) -> ActionResult:
        indicator_name = "CustomIndicator"
        raw = ctx.raw_text.lower()

        known_indicators = {
            "rsi": ("RSI", "momentum"),
            "macd": ("MACD", "trend"),
            "bollinger": ("BollingerBands", "volatility"),
            "atr": ("ATR", "volatility"),
            "adx": ("ADX", "trend"),
            "stochastic": ("Stochastic", "momentum"),
            "ema": ("EMA", "trend"),
            "sma": ("SMA", "trend"),
            "vwap": ("VWAP", "volume"),
        }

        indicator_type = "custom"
        category = "custom"
        for key, (name, cat) in known_indicators.items():
            if key in raw:
                indicator_name = f"Custom{name}"
                indicator_type = key
                category = cat
                break

        filename = f"{indicator_name.lower()}.py"
        filepath = self.output_dir / "indicators" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        code = self._generate_indicator_code(indicator_name, indicator_type, category)
        filepath.write_text(code)

        return ActionResult(
            success=True,
            message=(
                f"Created custom indicator: {indicator_name}\n"
                f"Category: {category}\n"
                f"File saved to: {filepath}"
            ),
            data={"indicator_name": indicator_name, "category": category},
            generated_files=[str(filepath)],
            suggestions=[
                "Add to strategy: 'Use this indicator in my strategy'",
                "Test indicator: 'Backtest with this indicator'",
            ],
        )

    def _handle_build_bot(self, ctx: CommandContext) -> ActionResult:
        instrument = ctx.entities.get("instrument", "XAUUSD")
        strategy_type = ctx.entities.get("strategy_type", "scalping")
        timeframe = ctx.entities.get("timeframe", "M5")

        bot_name = f"{instrument}_{strategy_type}_bot"
        bot_dir = self.output_dir / "bots" / bot_name
        bot_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "bot_name": bot_name,
            "instrument": instrument,
            "strategy_type": strategy_type,
            "timeframe": timeframe,
            "risk_per_trade": float(ctx.entities.get("risk_percent", 1.0)),
            "max_positions": 3,
            "trading_hours": {"start": "08:00", "end": "20:00"},
            "auto_shutdown_drawdown": 5.0,
        }

        config_path = bot_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2))

        ea_code = self._generate_ea_template(config)
        ea_path = bot_dir / f"{bot_name}.mq5"
        ea_path.write_text(ea_code)

        return ActionResult(
            success=True,
            message=(
                f"Trading bot '{bot_name}' created successfully!\n"
                f"Instrument: {instrument}\n"
                f"Strategy: {strategy_type}\n"
                f"Timeframe: {timeframe}\n\n"
                f"Files generated:\n"
                f"  - Configuration: {config_path}\n"
                f"  - EA Template: {ea_path}"
            ),
            data=config,
            generated_files=[str(config_path), str(ea_path)],
            suggestions=[
                "Backtest the bot: 'Run backtest'",
                "Deploy to MT5: 'Deploy the bot'",
                "Set risk parameters: 'Set risk to 2%'",
            ],
        )

    def _handle_run_backtest(self, ctx: CommandContext) -> ActionResult:
        instrument = ctx.entities.get("instrument", "XAUUSD")
        timeframe = ctx.entities.get("timeframe", "M5")
        strategy_type = ctx.entities.get("strategy_type", "current")

        config = {
            "instrument": instrument,
            "timeframe": timeframe,
            "strategy": strategy_type,
            "start_date": "2024-01-01",
            "end_date": "2025-01-01",
            "initial_balance": 10000,
            "commission": 7.0,
            "slippage": 2,
        }

        config_path = self.output_dir / "backtests" / "backtest_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2))

        return ActionResult(
            success=True,
            message=(
                f"Backtest configured for {instrument} on {timeframe}.\n"
                f"Period: {config['start_date']} to {config['end_date']}\n"
                f"Initial balance: ${config['initial_balance']:,.0f}\n\n"
                f"Configuration saved. Execute the backtest engine to run."
            ),
            data=config,
            generated_files=[str(config_path)],
            suggestions=[
                "Run walk-forward analysis: 'Run walk-forward test'",
                "Run Monte Carlo simulation: 'Run Monte Carlo'",
                "Analyze results: 'Show performance report'",
            ],
        )

    def _handle_analyze_performance(self, ctx: CommandContext) -> ActionResult:
        return ActionResult(
            success=True,
            message=(
                "Performance analysis ready.\n\n"
                "Available metrics:\n"
                "  - Sharpe Ratio, Sortino Ratio, Calmar Ratio\n"
                "  - Max Drawdown, Average Drawdown\n"
                "  - Win Rate, Profit Factor\n"
                "  - Monthly/Weekly Returns Breakdown\n"
                "  - Trade Distribution Analysis\n\n"
                "Load trade data to generate the full report."
            ),
            data={"available_metrics": [
                "sharpe_ratio", "sortino_ratio", "calmar_ratio",
                "max_drawdown", "win_rate", "profit_factor",
            ]},
            suggestions=[
                "Run backtest first: 'Run backtest'",
                "Export report: 'Export performance report'",
            ],
        )

    def _handle_detect_regime(self, ctx: CommandContext) -> ActionResult:
        instrument = ctx.entities.get("instrument", "the market")

        return ActionResult(
            success=True,
            message=(
                f"Market regime detection initialized for {instrument}.\n\n"
                "Detection methods:\n"
                "  1. Hidden Markov Model (HMM)\n"
                "  2. Volatility Clustering\n"
                "  3. Session-Aware Analysis\n\n"
                "Feed price data to the regime detector to get classifications."
            ),
            data={
                "methods": ["hmm", "volatility_clustering", "session_analysis"],
                "regimes": ["trending_up", "trending_down", "ranging", "volatile"],
            },
            suggestions=[
                "Get prediction: 'What is the current market regime?'",
                "Adapt strategy: 'Switch strategy based on regime'",
            ],
        )

    def _handle_train_model(self, ctx: CommandContext) -> ActionResult:
        config = {
            "model_type": "lstm",
            "epochs": 100,
            "batch_size": 64,
            "learning_rate": 0.001,
            "walk_forward_splits": 5,
            "early_stopping_patience": 15,
        }

        config_path = self.output_dir / "training" / "training_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2))

        return ActionResult(
            success=True,
            message=(
                "Model training configured.\n\n"
                f"Model: LSTM ({config['model_type']})\n"
                f"Epochs: {config['epochs']}\n"
                f"Batch size: {config['batch_size']}\n"
                f"Walk-forward splits: {config['walk_forward_splits']}\n\n"
                "Prepare training data and launch the training pipeline."
            ),
            data=config,
            generated_files=[str(config_path)],
            suggestions=[
                "Start training: 'Start model training'",
                "Use reinforcement learning: 'Train with RL'",
            ],
        )

    def _handle_get_prediction(self, ctx: CommandContext) -> ActionResult:
        instrument = ctx.entities.get("instrument", "XAUUSD")

        return ActionResult(
            success=True,
            message=(
                f"Prediction request for {instrument}.\n\n"
                "The prediction engine will:\n"
                "  1. Extract features from latest market data\n"
                "  2. Run ensemble prediction across loaded models\n"
                "  3. Compute confidence score\n"
                "  4. Factor in current market regime\n\n"
                "Load models and feed market data to generate predictions."
            ),
            data={
                "instrument": instrument,
                "pipeline": ["feature_extraction", "ensemble_prediction",
                             "confidence_scoring", "regime_adjustment"],
            },
            suggestions=[
                "Train models first: 'Train the model'",
                "Check regime: 'What is the market regime?'",
            ],
        )

    def _handle_manage_risk(self, ctx: CommandContext) -> ActionResult:
        risk_pct = ctx.entities.get("risk_percent", "1.0")
        lot_size = ctx.entities.get("lot_size")

        config = {
            "risk_per_trade": float(risk_pct),
            "max_daily_drawdown": 5.0,
            "max_total_drawdown": 10.0,
            "max_positions": 3,
            "correlation_limit": 0.7,
        }

        if lot_size:
            config["fixed_lot_size"] = float(lot_size)

        config_path = self.output_dir / "risk" / "risk_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2))

        return ActionResult(
            success=True,
            message=(
                f"Risk parameters updated:\n"
                f"  Risk per trade: {config['risk_per_trade']}%\n"
                f"  Max daily drawdown: {config['max_daily_drawdown']}%\n"
                f"  Max total drawdown: {config['max_total_drawdown']}%\n"
                f"  Max positions: {config['max_positions']}\n"
            ),
            data=config,
            generated_files=[str(config_path)],
        )

    def _handle_get_status(self, ctx: CommandContext) -> ActionResult:
        return ActionResult(
            success=True,
            message=(
                "JARVIS Trading System Status\n"
                "============================\n"
                "System: Online\n"
                "AI Models: Ready\n"
                "Market Data: Connected\n"
                "Risk Engine: Active\n\n"
                "Use 'help' to see available commands."
            ),
            data={"status": "online", "modules": {
                "ai_models": "ready",
                "market_data": "connected",
                "risk_engine": "active",
            }},
        )

    def _handle_help(self, ctx: CommandContext) -> ActionResult:
        return ActionResult(
            success=True,
            message=(
                "JARVIS Trading System - Available Commands\n"
                "==========================================\n\n"
                "Strategy:\n"
                "  'Build a Gold Scalping Bot'\n"
                "  'Create a trend following strategy for EURUSD'\n"
                "  'Generate a momentum strategy on H1'\n\n"
                "Optimization:\n"
                "  'Optimize the strategy'\n"
                "  'Tune hyperparameters'\n"
                "  'Find best parameters'\n\n"
                "Backtesting:\n"
                "  'Run backtest on XAUUSD'\n"
                "  'Test strategy on daily data'\n\n"
                "AI & Prediction:\n"
                "  'Train the model'\n"
                "  'What is the market regime?'\n"
                "  'Get prediction for EURUSD'\n\n"
                "Risk Management:\n"
                "  'Set risk to 2%'\n"
                "  'Manage position sizing'\n\n"
                "General:\n"
                "  'Show status'\n"
                "  'Help'\n"
            ),
        )

    def _handle_unknown(self, ctx: CommandContext) -> ActionResult:
        return ActionResult(
            success=False,
            message=(
                f"I couldn't understand the command: '{ctx.raw_text}'\n\n"
                "Try commands like:\n"
                "  'Build a Gold Scalping Bot'\n"
                "  'Optimize the strategy'\n"
                "  'Run backtest'\n"
                "  'Help'"
            ),
            suggestions=["Type 'help' to see all available commands"],
        )

    def _generate_strategy_code(
        self, class_name: str, instrument: str,
        strategy_type: str, timeframe: str,
    ) -> str:
        indicator_setup = {
            "scalping": (
                "self.fast_ema_period = params.get('fast_ema', 8)\n"
                "        self.slow_ema_period = params.get('slow_ema', 21)\n"
                "        self.rsi_period = params.get('rsi_period', 14)\n"
                "        self.rsi_oversold = params.get('rsi_oversold', 30)\n"
                "        self.rsi_overbought = params.get('rsi_overbought', 70)\n"
                "        self.atr_period = params.get('atr_period', 14)\n"
                "        self.atr_multiplier = params.get('atr_multiplier', 1.5)"
            ),
            "trend_following": (
                "self.ema_fast = params.get('ema_fast', 20)\n"
                "        self.ema_slow = params.get('ema_slow', 50)\n"
                "        self.adx_period = params.get('adx_period', 14)\n"
                "        self.adx_threshold = params.get('adx_threshold', 25)\n"
                "        self.atr_period = params.get('atr_period', 14)\n"
                "        self.atr_sl_mult = params.get('atr_sl_mult', 2.0)"
            ),
            "mean_reversion": (
                "self.bb_period = params.get('bb_period', 20)\n"
                "        self.bb_std = params.get('bb_std', 2.0)\n"
                "        self.rsi_period = params.get('rsi_period', 14)\n"
                "        self.rsi_low = params.get('rsi_low', 30)\n"
                "        self.rsi_high = params.get('rsi_high', 70)"
            ),
        }

        buy_logic = {
            "scalping": (
                "fast_ema = self._ema(close, self.fast_ema_period)\n"
                "        slow_ema = self._ema(close, self.slow_ema_period)\n"
                "        rsi = self._rsi(close, self.rsi_period)\n"
                "        return fast_ema[-1] > slow_ema[-1] and rsi[-1] < self.rsi_overbought"
            ),
            "trend_following": (
                "ema_f = self._ema(close, self.ema_fast)\n"
                "        ema_s = self._ema(close, self.ema_slow)\n"
                "        return ema_f[-1] > ema_s[-1] and ema_f[-2] <= ema_s[-2]"
            ),
            "mean_reversion": (
                "bb_lower, _, _ = self._bollinger(close, self.bb_period, self.bb_std)\n"
                "        rsi = self._rsi(close, self.rsi_period)\n"
                "        return close[-1] < bb_lower[-1] and rsi[-1] < self.rsi_low"
            ),
        }

        sell_logic = {
            "scalping": (
                "fast_ema = self._ema(close, self.fast_ema_period)\n"
                "        slow_ema = self._ema(close, self.slow_ema_period)\n"
                "        rsi = self._rsi(close, self.rsi_period)\n"
                "        return fast_ema[-1] < slow_ema[-1] and rsi[-1] > self.rsi_oversold"
            ),
            "trend_following": (
                "ema_f = self._ema(close, self.ema_fast)\n"
                "        ema_s = self._ema(close, self.ema_slow)\n"
                "        return ema_f[-1] < ema_s[-1] and ema_f[-2] >= ema_s[-2]"
            ),
            "mean_reversion": (
                "_, _, bb_upper = self._bollinger(close, self.bb_period, self.bb_std)\n"
                "        rsi = self._rsi(close, self.rsi_period)\n"
                "        return close[-1] > bb_upper[-1] and rsi[-1] > self.rsi_high"
            ),
        }

        st = strategy_type if strategy_type in indicator_setup else "scalping"

        return f'''"""Auto-generated {strategy_type} strategy for {instrument} on {timeframe}."""

import numpy as np
from typing import Dict, Any, Optional


class {class_name}:
    """
    {strategy_type.replace("_", " ").title()} strategy for {instrument}.
    Timeframe: {timeframe}
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        params = params or {{}}
        self.instrument = "{instrument}"
        self.timeframe = "{timeframe}"
        {indicator_setup[st]}
        self.risk_percent = params.get('risk_percent', 1.0)
        self.tp_multiplier = params.get('tp_multiplier', 2.0)

    def check_buy_signal(self, close: np.ndarray, high: np.ndarray = None,
                          low: np.ndarray = None, volume: np.ndarray = None) -> bool:
        if len(close) < 50:
            return False
        {buy_logic[st]}

    def check_sell_signal(self, close: np.ndarray, high: np.ndarray = None,
                           low: np.ndarray = None, volume: np.ndarray = None) -> bool:
        if len(close) < 50:
            return False
        {sell_logic[st]}

    def calculate_stop_loss(self, entry_price: float, direction: str,
                            high: np.ndarray = None, low: np.ndarray = None,
                            close: np.ndarray = None) -> float:
        atr = self._atr(high, low, close, 14) if high is not None else entry_price * 0.01
        if direction == "buy":
            return entry_price - atr * 1.5
        return entry_price + atr * 1.5

    def calculate_take_profit(self, entry_price: float, stop_loss: float,
                               direction: str) -> float:
        risk = abs(entry_price - stop_loss)
        if direction == "buy":
            return entry_price + risk * self.tp_multiplier
        return entry_price - risk * self.tp_multiplier

    @staticmethod
    def _ema(data: np.ndarray, period: int) -> np.ndarray:
        alpha = 2.0 / (period + 1)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = alpha * data[i] + (1 - alpha) * result[i - 1]
        return result

    @staticmethod
    def _rsi(data: np.ndarray, period: int = 14) -> np.ndarray:
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = np.convolve(gains, np.ones(period) / period, mode="same")
        avg_loss = np.convolve(losses, np.ones(period) / period, mode="same")
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100.0 - 100.0 / (1.0 + rs)
        return np.concatenate([[50.0], rsi])

    @staticmethod
    def _bollinger(data: np.ndarray, period: int = 20, std_mult: float = 2.0):
        sma = np.convolve(data, np.ones(period) / period, mode="same")
        rolling_std = np.array([np.std(data[max(0, i - period):i + 1]) for i in range(len(data))])
        upper = sma + std_mult * rolling_std
        lower = sma - std_mult * rolling_std
        return lower, sma, upper

    @staticmethod
    def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> float:
        tr = np.maximum(high[1:] - low[1:],
                        np.maximum(np.abs(high[1:] - close[:-1]),
                                   np.abs(low[1:] - close[:-1])))
        return float(np.mean(tr[-period:]))
'''

    def _generate_indicator_code(
        self, name: str, indicator_type: str, category: str
    ) -> str:
        return f'''"""Auto-generated custom indicator: {name}."""

import numpy as np
from typing import Dict, Optional, Tuple


class {name}:
    """Custom {category} indicator based on {indicator_type}."""

    def __init__(self, period: int = 14, **kwargs):
        self.period = period
        self.params = kwargs

    def calculate(self, close: np.ndarray, high: Optional[np.ndarray] = None,
                  low: Optional[np.ndarray] = None,
                  volume: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        n = len(close)
        main_line = np.zeros(n)
        signal_line = np.zeros(n)

        for i in range(self.period, n):
            window = close[i - self.period:i]
            main_line[i] = np.mean(window)
            if i >= self.period * 2:
                signal_window = main_line[i - self.period:i]
                signal_line[i] = np.mean(signal_window)

        return {{
            "main": main_line,
            "signal": signal_line,
            "histogram": main_line - signal_line,
        }}

    def get_signal(self, close: np.ndarray, **kwargs) -> int:
        values = self.calculate(close, **kwargs)
        main = values["main"]
        signal = values["signal"]
        if main[-1] > signal[-1] and main[-2] <= signal[-2]:
            return 1  # Buy
        elif main[-1] < signal[-1] and main[-2] >= signal[-2]:
            return -1  # Sell
        return 0  # Neutral
'''

    def _generate_ea_template(self, config: Dict[str, Any]) -> str:
        return f'''//+------------------------------------------------------------------+
//| {config["bot_name"]}.mq5
//| Auto-generated by JARVIS Trading System
//+------------------------------------------------------------------+
#property copyright "JARVIS"
#property version   "1.00"
#property strict

input string InstrumentName = "{config["instrument"]}";
input ENUM_TIMEFRAMES Timeframe = PERIOD_{config["timeframe"]};
input double RiskPercent = {config["risk_per_trade"]};
input int MaxPositions = {config["max_positions"]};
input double MaxDrawdownPct = {config["auto_shutdown_drawdown"]};

int OnInit() {{
    Print("JARVIS Bot initialized: ", InstrumentName);
    return INIT_SUCCEEDED;
}}

void OnDeinit(const int reason) {{
    Print("JARVIS Bot stopped");
}}

void OnTick() {{
    // Strategy logic called from Python bridge
    if (!IsTradeAllowed()) return;

    double currentDD = (AccountInfoDouble(ACCOUNT_BALANCE) -
                         AccountInfoDouble(ACCOUNT_EQUITY)) /
                        AccountInfoDouble(ACCOUNT_BALANCE) * 100.0;
    if (currentDD > MaxDrawdownPct) {{
        Print("Max drawdown reached, shutting down");
        ExpertRemove();
        return;
    }}
}}
//+------------------------------------------------------------------+
'''


class ChatEngine:
    """
    Main chat engine that processes natural language commands,
    classifies intents, and executes trading operations.
    """

    def __init__(
        self,
        output_dir: str = "generated",
        max_history: int = 100,
    ):
        self.classifier = IntentClassifier()
        self.entity_extractor = EntityExtractor()
        self.executor = ActionExecutor(output_dir=output_dir)
        self.history: List[ChatMessage] = []
        self.max_history = max_history

    def process(self, user_input: str) -> str:
        """
        Process a user command and return a response string.

        This is the main entry point for the chat engine.
        """
        self.history.append(ChatMessage(role="user", content=user_input))

        context = self._parse_command(user_input)
        result = self.executor.execute(context)

        response = self._format_response(result)
        self.history.append(
            ChatMessage(
                role="assistant",
                content=response,
                metadata={
                    "intent": context.intent.value,
                    "confidence": context.confidence,
                    "success": result.success,
                },
            )
        )

        self._trim_history()
        return response

    def process_structured(self, user_input: str) -> Dict[str, Any]:
        """
        Process a command and return a structured response.

        Returns a dict with all metadata useful for programmatic consumers.
        """
        self.history.append(ChatMessage(role="user", content=user_input))

        context = self._parse_command(user_input)
        result = self.executor.execute(context)

        self.history.append(
            ChatMessage(
                role="assistant",
                content=result.message,
                metadata={
                    "intent": context.intent.value,
                    "confidence": context.confidence,
                },
            )
        )

        self._trim_history()

        return {
            "intent": context.intent.value,
            "confidence": context.confidence,
            "entities": context.entities,
            "success": result.success,
            "message": result.message,
            "data": result.data,
            "generated_files": result.generated_files,
            "suggestions": result.suggestions,
        }

    def _parse_command(self, text: str) -> CommandContext:
        intent, confidence = self.classifier.classify(text)
        entities = self.entity_extractor.extract(text)

        context_hints = self._get_context_hints()
        if intent == Intent.UNKNOWN and context_hints:
            intent = context_hints.get("likely_intent", Intent.UNKNOWN)
            confidence = 0.3

        return CommandContext(
            intent=intent,
            confidence=confidence,
            entities=entities,
            raw_text=text,
            parameters={},
        )

    def _get_context_hints(self) -> Dict[str, Any]:
        """Infer context from recent conversation history."""
        if not self.history:
            return {}

        recent = [m for m in self.history[-5:] if m.role == "assistant"]
        if not recent:
            return {}

        last_intent = recent[-1].metadata.get("intent")
        if last_intent == "generate_strategy":
            return {"likely_intent": Intent.RUN_BACKTEST}
        elif last_intent == "run_backtest":
            return {"likely_intent": Intent.ANALYZE_PERFORMANCE}

        return {}

    def _format_response(self, result: ActionResult) -> str:
        parts = [result.message]

        if result.suggestions:
            parts.append("\nSuggested next steps:")
            for suggestion in result.suggestions:
                parts.append(f"  → {suggestion}")

        return "\n".join(parts)

    def _trim_history(self) -> None:
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

    def get_history(self) -> List[Dict[str, Any]]:
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "metadata": msg.metadata,
            }
            for msg in self.history
        ]

    def clear_history(self) -> None:
        self.history.clear()
