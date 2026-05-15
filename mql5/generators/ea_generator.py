"""
JARVIS MQL5 Expert Advisor Generator.

Generates complete, syntactically correct .mq5 EA files for various
trading strategy types with full risk management and trade management.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

from mql5.templates.ea_base import (
    EA_BASE_TEMPLATE,
    EA_BREAKOUT_LOGIC,
    EA_ICT_SMART_MONEY_LOGIC,
    EA_MEAN_REVERSION_LOGIC,
    EA_SCALPING_LOGIC,
    EA_TREND_FOLLOWING_LOGIC,
)


class StrategyType(str, Enum):
    SCALPING = "scalping"
    TREND_FOLLOWING = "trend_following"
    BREAKOUT = "breakout"
    MEAN_REVERSION = "mean_reversion"
    ICT_SMART_MONEY = "ict_smart_money"


@dataclass
class EAParams:
    """Parameters for EA generation with sensible defaults."""

    lot_size: float = 0.0
    risk_percent: float = 1.0
    stop_loss: int = 100
    take_profit: int = 200
    magic_number: int = 123456
    trade_comment: str = "JARVIS"
    max_spread: int = 30
    max_slippage: int = 10
    max_daily_trades: int = 0
    max_daily_loss: float = 3.0
    max_drawdown: float = 10.0
    use_trailing: bool = True
    trailing_start: int = 100
    trailing_step: int = 50
    use_breakeven: bool = True
    breakeven_start: int = 50
    breakeven_offset: int = 5
    use_time_filter: bool = False
    start_hour: int = 8
    end_hour: int = 20
    extra: Dict[str, Any] = field(default_factory=dict)


_STRATEGY_CUSTOM_INPUTS: Dict[str, str] = {
    StrategyType.SCALPING: """
input group "=== Scalping Parameters ==="
input int      InpEmaFast       = 8;     // Fast EMA Period
input int      InpEmaSlow       = 21;    // Slow EMA Period
input int      InpRsiPeriod     = 14;    // RSI Period
input double   InpRsiOverbought = 70.0;  // RSI Overbought Level
input double   InpRsiOversold   = 30.0;  // RSI Oversold Level
input double   InpVolMultiplier = 1.5;   // Volume Multiplier
""",
    StrategyType.TREND_FOLLOWING: """
input group "=== Trend Following Parameters ==="
input int      InpAdxPeriod     = 14;    // ADX Period
input double   InpAdxThreshold  = 25.0;  // ADX Trend Threshold
input int      InpMaPeriod      = 50;    // Moving Average Period
input ENUM_MA_METHOD InpMaMethod = MODE_EMA; // MA Method
input int      InpAtrPeriod     = 14;    // ATR Period
input double   InpAtrMultSl     = 1.5;   // ATR Multiplier for SL
input double   InpAtrMultTp     = 3.0;   // ATR Multiplier for TP
""",
    StrategyType.BREAKOUT: """
input group "=== Breakout Parameters ==="
input int      InpRangePeriod   = 20;    // Range Lookback Period
input int      InpAtrPeriod     = 14;    // ATR Period
input double   InpAtrMultSl     = 1.0;   // ATR Multiplier for SL
input double   InpAtrMultTp     = 2.0;   // Range Multiplier for TP
input double   InpVolMultiplier = 1.5;   // Volume Multiplier
""",
    StrategyType.MEAN_REVERSION: """
input group "=== Mean Reversion Parameters ==="
input int      InpBBPeriod      = 20;    // Bollinger Bands Period
input double   InpBBDeviation   = 2.0;   // Bollinger Bands Deviation
input int      InpRsiPeriod     = 14;    // RSI Period
input double   InpRsiOverbought = 70.0;  // RSI Overbought Level
input double   InpRsiOversold   = 30.0;  // RSI Oversold Level
""",
    StrategyType.ICT_SMART_MONEY: """
input group "=== ICT/Smart Money Parameters ==="
input int      InpLookback      = 50;    // Lookback Period for OB/Liquidity
input double   InpOBStrength    = 1.5;   // Order Block Strength Multiplier
input int      InpAtrPeriod     = 14;    // ATR Period
input double   InpAtrMultSl     = 1.5;   // ATR Multiplier for SL
input double   InpAtrMultTp     = 3.0;   // ATR Multiplier for TP
""",
}

_STRATEGY_CUSTOM_GLOBALS: Dict[str, str] = {
    StrategyType.SCALPING: """
int hEmaFast, hEmaSlow, hRsi;
""",
    StrategyType.TREND_FOLLOWING: """
int hAdx, hMa, hAtr;
""",
    StrategyType.BREAKOUT: """
int hAtr;
""",
    StrategyType.MEAN_REVERSION: """
int hBB, hRsi;
""",
    StrategyType.ICT_SMART_MONEY: """
int hAtr;
""",
}

_STRATEGY_CUSTOM_INIT: Dict[str, str] = {
    StrategyType.SCALPING: """
   //--- Create indicator handles
   hEmaFast = iMA(_Symbol, _Period, InpEmaFast, 0, MODE_EMA, PRICE_CLOSE);
   hEmaSlow = iMA(_Symbol, _Period, InpEmaSlow, 0, MODE_EMA, PRICE_CLOSE);
   hRsi     = iRSI(_Symbol, _Period, InpRsiPeriod, PRICE_CLOSE);

   if(hEmaFast == INVALID_HANDLE || hEmaSlow == INVALID_HANDLE || hRsi == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles");
      return(INIT_FAILED);
   }
""",
    StrategyType.TREND_FOLLOWING: """
   //--- Create indicator handles
   hAdx = iADX(_Symbol, _Period, InpAdxPeriod);
   hMa  = iMA(_Symbol, _Period, InpMaPeriod, 0, InpMaMethod, PRICE_CLOSE);
   hAtr = iATR(_Symbol, _Period, InpAtrPeriod);

   if(hAdx == INVALID_HANDLE || hMa == INVALID_HANDLE || hAtr == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles");
      return(INIT_FAILED);
   }
""",
    StrategyType.BREAKOUT: """
   //--- Create indicator handles
   hAtr = iATR(_Symbol, _Period, InpAtrPeriod);

   if(hAtr == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles");
      return(INIT_FAILED);
   }
""",
    StrategyType.MEAN_REVERSION: """
   //--- Create indicator handles
   hBB  = iBands(_Symbol, _Period, InpBBPeriod, 0, InpBBDeviation, PRICE_CLOSE);
   hRsi = iRSI(_Symbol, _Period, InpRsiPeriod, PRICE_CLOSE);

   if(hBB == INVALID_HANDLE || hRsi == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles");
      return(INIT_FAILED);
   }
""",
    StrategyType.ICT_SMART_MONEY: """
   //--- Create indicator handles
   hAtr = iATR(_Symbol, _Period, InpAtrPeriod);

   if(hAtr == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles");
      return(INIT_FAILED);
   }
""",
}

_STRATEGY_CUSTOM_DEINIT: Dict[str, str] = {
    StrategyType.SCALPING: """
   if(hEmaFast != INVALID_HANDLE) IndicatorRelease(hEmaFast);
   if(hEmaSlow != INVALID_HANDLE) IndicatorRelease(hEmaSlow);
   if(hRsi != INVALID_HANDLE)     IndicatorRelease(hRsi);
""",
    StrategyType.TREND_FOLLOWING: """
   if(hAdx != INVALID_HANDLE) IndicatorRelease(hAdx);
   if(hMa != INVALID_HANDLE)  IndicatorRelease(hMa);
   if(hAtr != INVALID_HANDLE) IndicatorRelease(hAtr);
""",
    StrategyType.BREAKOUT: """
   if(hAtr != INVALID_HANDLE) IndicatorRelease(hAtr);
""",
    StrategyType.MEAN_REVERSION: """
   if(hBB != INVALID_HANDLE)  IndicatorRelease(hBB);
   if(hRsi != INVALID_HANDLE) IndicatorRelease(hRsi);
""",
    StrategyType.ICT_SMART_MONEY: """
   if(hAtr != INVALID_HANDLE) IndicatorRelease(hAtr);
""",
}

_STRATEGY_TICK_LOGIC: Dict[str, str] = {
    StrategyType.SCALPING: EA_SCALPING_LOGIC,
    StrategyType.TREND_FOLLOWING: EA_TREND_FOLLOWING_LOGIC,
    StrategyType.BREAKOUT: EA_BREAKOUT_LOGIC,
    StrategyType.MEAN_REVERSION: EA_MEAN_REVERSION_LOGIC,
    StrategyType.ICT_SMART_MONEY: EA_ICT_SMART_MONEY_LOGIC,
}


class EAGenerator:
    """Generates complete MQL5 Expert Advisor source files.

    Supports multiple strategy types including Scalping, Trend Following,
    Breakout, Mean Reversion, and ICT/Smart Money approaches. Generated
    EAs include full risk management, trade management (trailing stop,
    breakeven), time filters, and daily limits.
    """

    SUPPORTED_STRATEGIES = list(StrategyType)

    def __init__(self, output_dir: str = "./output/experts") -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_ea(
        self,
        name: str,
        strategy_type: str | StrategyType,
        params: Optional[Dict[str, Any] | EAParams] = None,
    ) -> str:
        """Generate a complete .mq5 Expert Advisor file.

        Args:
            name: EA name (used for filename and internal identification).
            strategy_type: One of the supported strategy types.
            params: EA parameters. Can be a dict or EAParams instance.

        Returns:
            Absolute path to the generated .mq5 file.

        Raises:
            ValueError: If strategy_type is not supported.
        """
        if isinstance(strategy_type, str):
            strategy_type = StrategyType(strategy_type.lower())

        if strategy_type not in StrategyType:
            raise ValueError(
                f"Unsupported strategy type: {strategy_type}. "
                f"Choose from: {[s.value for s in StrategyType]}"
            )

        ea_params = self._resolve_params(params, strategy_type)
        mql5_code = self._build_ea_code(name, strategy_type, ea_params)

        file_path = os.path.join(self.output_dir, f"{name}.mq5")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(mql5_code)

        return os.path.abspath(file_path)

    def list_strategies(self) -> list[str]:
        """Return list of supported strategy type names."""
        return [s.value for s in StrategyType]

    def get_default_params(self, strategy_type: str | StrategyType) -> EAParams:
        """Return default parameters for a given strategy type."""
        if isinstance(strategy_type, str):
            strategy_type = StrategyType(strategy_type.lower())

        params = EAParams()

        if strategy_type == StrategyType.SCALPING:
            params.stop_loss = 50
            params.take_profit = 75
            params.trailing_start = 40
            params.trailing_step = 20
        elif strategy_type == StrategyType.TREND_FOLLOWING:
            params.stop_loss = 150
            params.take_profit = 300
            params.trailing_start = 100
            params.trailing_step = 50
        elif strategy_type == StrategyType.BREAKOUT:
            params.stop_loss = 100
            params.take_profit = 200
            params.trailing_start = 80
            params.trailing_step = 40
        elif strategy_type == StrategyType.MEAN_REVERSION:
            params.stop_loss = 80
            params.take_profit = 0
            params.use_trailing = False
        elif strategy_type == StrategyType.ICT_SMART_MONEY:
            params.stop_loss = 0
            params.take_profit = 0
            params.use_time_filter = True
            params.start_hour = 7
            params.end_hour = 17

        return params

    def _resolve_params(
        self,
        params: Optional[Dict[str, Any] | EAParams],
        strategy_type: StrategyType,
    ) -> EAParams:
        """Merge user params with defaults for the strategy type."""
        defaults = self.get_default_params(strategy_type)

        if params is None:
            return defaults

        if isinstance(params, dict):
            for key, value in params.items():
                if hasattr(defaults, key):
                    setattr(defaults, key, value)
                else:
                    defaults.extra[key] = value
            return defaults

        return params

    def _build_ea_code(
        self, name: str, strategy_type: StrategyType, params: EAParams
    ) -> str:
        """Assemble the final MQL5 EA source code from template + strategy logic."""
        replacements = {
            "ea_name": name,
            "strategy_type": strategy_type.value.replace("_", " ").title(),
            "lot_size": str(params.lot_size),
            "risk_percent": str(params.risk_percent),
            "stop_loss": str(params.stop_loss),
            "take_profit": str(params.take_profit),
            "magic_number": str(params.magic_number),
            "trade_comment": params.trade_comment,
            "max_spread": str(params.max_spread),
            "max_slippage": str(params.max_slippage),
            "max_daily_trades": str(params.max_daily_trades),
            "max_daily_loss": str(params.max_daily_loss),
            "max_drawdown": str(params.max_drawdown),
            "use_trailing": "true" if params.use_trailing else "false",
            "trailing_start": str(params.trailing_start),
            "trailing_step": str(params.trailing_step),
            "use_breakeven": "true" if params.use_breakeven else "false",
            "breakeven_start": str(params.breakeven_start),
            "breakeven_offset": str(params.breakeven_offset),
            "use_time_filter": "true" if params.use_time_filter else "false",
            "start_hour": str(params.start_hour),
            "end_hour": str(params.end_hour),
            "custom_inputs": _STRATEGY_CUSTOM_INPUTS.get(strategy_type, ""),
            "custom_globals": _STRATEGY_CUSTOM_GLOBALS.get(strategy_type, ""),
            "custom_init": _STRATEGY_CUSTOM_INIT.get(strategy_type, ""),
            "custom_deinit": _STRATEGY_CUSTOM_DEINIT.get(strategy_type, ""),
            "custom_on_tick": _STRATEGY_TICK_LOGIC.get(strategy_type, ""),
            "custom_on_timer": "",
            "custom_functions": "",
        }

        code = EA_BASE_TEMPLATE
        for key, value in replacements.items():
            code = code.replace("{" + key + "}", value)

        return code
