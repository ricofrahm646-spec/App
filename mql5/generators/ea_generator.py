"""Expert Advisor MQL5 code generator using Jinja2 templates."""
import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, BaseLoader

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


class StrategyType(Enum):
    SCALPING = "scalping"
    ICT = "ict"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    CUSTOM = "custom"


@dataclass
class EAConfig:
    """Configuration for generating an Expert Advisor."""
    ea_name: str = "JARVIS_EA"
    magic_number: int = 234000
    default_lot: float = 0.01
    default_sl: float = 500.0
    default_tp: float = 1000.0
    risk_percent: float = 1.0
    use_fixed_lot: str = "false"
    max_slippage: int = 20
    use_trailing_stop: str = "true"
    trailing_activation: float = 200.0
    trailing_distance: float = 100.0
    trailing_step: float = 10.0
    strategy_type: StrategyType = StrategyType.CUSTOM

    strategy_logic: str = ""
    entry_condition_buy: str = "return false;"
    entry_condition_sell: str = "return false;"
    exit_condition_buy: str = ""
    exit_condition_sell: str = ""
    extra_inputs: str = ""
    custom_includes: str = ""
    on_init_extra: str = ""
    on_deinit_extra: str = ""
    custom_functions: str = ""


# ---------------------------------------------------------------------------
# Pre-built strategy snippets
# ---------------------------------------------------------------------------

_SCALPING_BUY = """\
   // Scalping: fast EMA crosses above slow EMA on M1
   int fastHandle = iMA(_Symbol, PERIOD_M1, InpFastMA, 0, MODE_EMA, PRICE_CLOSE);
   int slowHandle = iMA(_Symbol, PERIOD_M1, InpSlowMA, 0, MODE_EMA, PRICE_CLOSE);
   double fast[], slow[];
   ArraySetAsSeries(fast, true); ArraySetAsSeries(slow, true);
   CopyBuffer(fastHandle, 0, 0, 3, fast);
   CopyBuffer(slowHandle, 0, 0, 3, slow);
   IndicatorRelease(fastHandle); IndicatorRelease(slowHandle);
   if(fast[1] <= slow[1] && fast[0] > slow[0])
      return true;
   return false;"""

_SCALPING_SELL = """\
   int fastHandle = iMA(_Symbol, PERIOD_M1, InpFastMA, 0, MODE_EMA, PRICE_CLOSE);
   int slowHandle = iMA(_Symbol, PERIOD_M1, InpSlowMA, 0, MODE_EMA, PRICE_CLOSE);
   double fast[], slow[];
   ArraySetAsSeries(fast, true); ArraySetAsSeries(slow, true);
   CopyBuffer(fastHandle, 0, 0, 3, fast);
   CopyBuffer(slowHandle, 0, 0, 3, slow);
   IndicatorRelease(fastHandle); IndicatorRelease(slowHandle);
   if(fast[1] >= slow[1] && fast[0] < slow[0])
      return true;
   return false;"""

_SCALPING_INPUTS = """\
input int InpFastMA = 8;   // Fast EMA period
input int InpSlowMA = 21;  // Slow EMA period"""


_ICT_BUY = """\
   // ICT: Bullish Order Block + FVG on H1
   double high[], low[], close[], open[];
   ArraySetAsSeries(high, true); ArraySetAsSeries(low, true);
   ArraySetAsSeries(close, true); ArraySetAsSeries(open, true);
   CopyHigh(_Symbol, PERIOD_H1, 0, 20, high);
   CopyLow(_Symbol, PERIOD_H1, 0, 20, low);
   CopyClose(_Symbol, PERIOD_H1, 0, 20, close);
   CopyOpen(_Symbol, PERIOD_H1, 0, 20, open);

   // Detect bullish order block: bearish candle followed by strong bullish
   bool orderBlock = (close[2] < open[2]) && (close[1] > open[1])
                     && (close[1] - open[1]) > 2 * (open[2] - close[2]);
   // Fair Value Gap: gap between candle 3 low and candle 1 high
   bool fvg = (low[1] > high[3]);
   // Price retracing into OB zone
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   bool inOBZone = (bid >= low[2] && bid <= high[2]);

   if(orderBlock && fvg && inOBZone)
      return true;
   return false;"""

_ICT_SELL = """\
   double high[], low[], close[], open[];
   ArraySetAsSeries(high, true); ArraySetAsSeries(low, true);
   ArraySetAsSeries(close, true); ArraySetAsSeries(open, true);
   CopyHigh(_Symbol, PERIOD_H1, 0, 20, high);
   CopyLow(_Symbol, PERIOD_H1, 0, 20, low);
   CopyClose(_Symbol, PERIOD_H1, 0, 20, close);
   CopyOpen(_Symbol, PERIOD_H1, 0, 20, open);

   bool orderBlock = (close[2] > open[2]) && (close[1] < open[1])
                     && (open[1] - close[1]) > 2 * (close[2] - open[2]);
   bool fvg = (high[1] < low[3]);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   bool inOBZone = (ask <= high[2] && ask >= low[2]);

   if(orderBlock && fvg && inOBZone)
      return true;
   return false;"""

_ICT_INPUTS = """\
input ENUM_TIMEFRAMES InpHTF = PERIOD_H4;  // Higher timeframe for bias
input int InpOBLookback = 20;              // Order block lookback bars"""


_TREND_BUY = """\
   // Trend Following: price above 200 EMA and RSI > 50
   int emaHandle = iMA(_Symbol, PERIOD_H1, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   int rsiHandle = iRSI(_Symbol, PERIOD_H1, InpRSIPeriod, PRICE_CLOSE);
   double ema[], rsi[];
   ArraySetAsSeries(ema, true); ArraySetAsSeries(rsi, true);
   CopyBuffer(emaHandle, 0, 0, 2, ema);
   CopyBuffer(rsiHandle, 0, 0, 2, rsi);
   IndicatorRelease(emaHandle); IndicatorRelease(rsiHandle);

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid > ema[0] && rsi[0] > 50 && rsi[1] <= 50)
      return true;
   return false;"""

_TREND_SELL = """\
   int emaHandle = iMA(_Symbol, PERIOD_H1, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
   int rsiHandle = iRSI(_Symbol, PERIOD_H1, InpRSIPeriod, PRICE_CLOSE);
   double ema[], rsi[];
   ArraySetAsSeries(ema, true); ArraySetAsSeries(rsi, true);
   CopyBuffer(emaHandle, 0, 0, 2, ema);
   CopyBuffer(rsiHandle, 0, 0, 2, rsi);
   IndicatorRelease(emaHandle); IndicatorRelease(rsiHandle);

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(ask < ema[0] && rsi[0] < 50 && rsi[1] >= 50)
      return true;
   return false;"""

_TREND_INPUTS = """\
input int InpTrendEMA  = 200;  // Trend EMA period
input int InpRSIPeriod = 14;   // RSI period"""


_BREAKOUT_BUY = """\
   // Breakout: price breaks above highest high of N bars
   double high[];
   ArraySetAsSeries(high, true);
   CopyHigh(_Symbol, PERIOD_H1, 1, InpBreakoutPeriod, high);
   double resistance = high[ArrayMaximum(high, 0, InpBreakoutPeriod)];

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(bid > resistance)
      return true;
   return false;"""

_BREAKOUT_SELL = """\
   double low[];
   ArraySetAsSeries(low, true);
   CopyLow(_Symbol, PERIOD_H1, 1, InpBreakoutPeriod, low);
   double support = low[ArrayMinimum(low, 0, InpBreakoutPeriod)];

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(ask < support)
      return true;
   return false;"""

_BREAKOUT_INPUTS = """\
input int InpBreakoutPeriod = 20;  // Breakout lookback period"""


_MEAN_REV_BUY = """\
   // Mean Reversion: RSI oversold + Bollinger Band lower touch
   int rsiH = iRSI(_Symbol, PERIOD_H1, InpMRRSI, PRICE_CLOSE);
   int bbH  = iBands(_Symbol, PERIOD_H1, InpBBPeriod, 0, InpBBDev, PRICE_CLOSE);
   double rsi[], bbLower[];
   ArraySetAsSeries(rsi, true); ArraySetAsSeries(bbLower, true);
   CopyBuffer(rsiH, 0, 0, 2, rsi);
   CopyBuffer(bbH, 2, 0, 2, bbLower);
   IndicatorRelease(rsiH); IndicatorRelease(bbH);

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(rsi[0] < 30 && bid <= bbLower[0])
      return true;
   return false;"""

_MEAN_REV_SELL = """\
   int rsiH = iRSI(_Symbol, PERIOD_H1, InpMRRSI, PRICE_CLOSE);
   int bbH  = iBands(_Symbol, PERIOD_H1, InpBBPeriod, 0, InpBBDev, PRICE_CLOSE);
   double rsi[], bbUpper[];
   ArraySetAsSeries(rsi, true); ArraySetAsSeries(bbUpper, true);
   CopyBuffer(rsiH, 0, 0, 2, rsi);
   CopyBuffer(bbH, 1, 0, 2, bbUpper);
   IndicatorRelease(rsiH); IndicatorRelease(bbH);

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   if(rsi[0] > 70 && ask >= bbUpper[0])
      return true;
   return false;"""

_MEAN_REV_INPUTS = """\
input int    InpMRRSI    = 14;   // RSI period
input int    InpBBPeriod = 20;   // Bollinger Bands period
input double InpBBDev    = 2.0;  // Bollinger Bands deviation"""


STRATEGY_PRESETS: Dict[StrategyType, Dict[str, str]] = {
    StrategyType.SCALPING: {
        "entry_condition_buy": _SCALPING_BUY,
        "entry_condition_sell": _SCALPING_SELL,
        "extra_inputs": _SCALPING_INPUTS,
    },
    StrategyType.ICT: {
        "entry_condition_buy": _ICT_BUY,
        "entry_condition_sell": _ICT_SELL,
        "extra_inputs": _ICT_INPUTS,
    },
    StrategyType.TREND_FOLLOWING: {
        "entry_condition_buy": _TREND_BUY,
        "entry_condition_sell": _TREND_SELL,
        "extra_inputs": _TREND_INPUTS,
    },
    StrategyType.BREAKOUT: {
        "entry_condition_buy": _BREAKOUT_BUY,
        "entry_condition_sell": _BREAKOUT_SELL,
        "extra_inputs": _BREAKOUT_INPUTS,
    },
    StrategyType.MEAN_REVERSION: {
        "entry_condition_buy": _MEAN_REV_BUY,
        "entry_condition_sell": _MEAN_REV_SELL,
        "extra_inputs": _MEAN_REV_INPUTS,
    },
}


class EAGenerator:
    """Generates MQL5 Expert Advisor source files from Jinja2 templates."""

    def __init__(self, template_dir: Optional[Path] = None):
        tdir = template_dir or TEMPLATE_DIR
        if tdir.exists():
            self._env = Environment(
                loader=FileSystemLoader(str(tdir)),
                keep_trailing_newline=True,
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self._env = Environment(
                loader=BaseLoader(),
                keep_trailing_newline=True,
                trim_blocks=True,
                lstrip_blocks=True,
            )
        self._template_name = "ea_template.mq5"

    def generate(self, config: EAConfig) -> str:
        """Render the EA template with the given configuration.

        If the strategy type has a preset, its snippets are merged into the
        config (explicit values in *config* take precedence).
        """
        ctx = self._build_context(config)
        template = self._env.get_template(self._template_name)
        return template.render(**ctx)

    def generate_to_file(self, config: EAConfig, output_path: Path) -> Path:
        """Generate the EA and write the .mq5 file to *output_path*."""
        code = self.generate(config)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code, encoding="utf-8")
        logger.info("EA written to %s (%d bytes)", output_path, len(code))
        return output_path

    def generate_from_dict(self, params: Dict[str, Any]) -> str:
        """Generate EA code from a plain dictionary (useful for API calls)."""
        strategy_str = params.pop("strategy_type", "custom")
        try:
            strategy = StrategyType(strategy_str)
        except ValueError:
            strategy = StrategyType.CUSTOM
        cfg = EAConfig(strategy_type=strategy, **params)
        return self.generate(cfg)

    def list_strategies(self) -> List[str]:
        """Return available strategy type names."""
        return [s.value for s in StrategyType]

    def _build_context(self, config: EAConfig) -> Dict[str, Any]:
        preset = STRATEGY_PRESETS.get(config.strategy_type, {})

        return {
            "ea_name": config.ea_name,
            "magic_number": config.magic_number,
            "default_lot": config.default_lot,
            "default_sl": config.default_sl,
            "default_tp": config.default_tp,
            "risk_percent": config.risk_percent,
            "use_fixed_lot": config.use_fixed_lot,
            "max_slippage": config.max_slippage,
            "use_trailing_stop": config.use_trailing_stop,
            "trailing_activation": config.trailing_activation,
            "trailing_distance": config.trailing_distance,
            "trailing_step": config.trailing_step,
            "strategy_logic": config.strategy_logic or preset.get("strategy_logic", ""),
            "entry_condition_buy": config.entry_condition_buy
                if config.entry_condition_buy != "return false;"
                else preset.get("entry_condition_buy", "return false;"),
            "entry_condition_sell": config.entry_condition_sell
                if config.entry_condition_sell != "return false;"
                else preset.get("entry_condition_sell", "return false;"),
            "exit_condition_buy": config.exit_condition_buy or preset.get("exit_condition_buy", ""),
            "exit_condition_sell": config.exit_condition_sell or preset.get("exit_condition_sell", ""),
            "extra_inputs": config.extra_inputs or preset.get("extra_inputs", ""),
            "custom_includes": config.custom_includes,
            "on_init_extra": config.on_init_extra,
            "on_deinit_extra": config.on_deinit_extra,
            "custom_functions": config.custom_functions,
        }
