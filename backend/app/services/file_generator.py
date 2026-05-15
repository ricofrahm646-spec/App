import asyncio
import os
import shutil
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


class FileGeneratorService:
    """
    Automatically generates and manages trading system files (MQL5 EAs,
    indicators, Python strategies) based on structured configuration dicts.

    All generated files are written under BASE_PATH and tracked in an
    in-memory registry.
    """

    BASE_PATH: Path = Path("/workspace")
    GENERATED_DIR: str = "generated"  # relative to BASE_PATH

    # Standard MT5 installation paths (Windows); override via env var
    MT5_EXPERTS_SUBPATH: str = "MQL5/Experts"
    MT5_INDICATORS_SUBPATH: str = "MQL5/Indicators"
    MT5_SCRIPTS_SUBPATH: str = "MQL5/Scripts"

    def __init__(self) -> None:
        self._registry: List[Dict] = []
        self._generated_root = self.BASE_PATH / self.GENERATED_DIR
        self._generated_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _registry_add(self, path: str, file_type: str, size: int) -> None:
        self._registry.append(
            {
                "path": path,
                "type": file_type,
                "size_bytes": size,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

    def _registry_remove(self, path: str) -> None:
        self._registry = [r for r in self._registry if r["path"] != path]

    # ------------------------------------------------------------------
    # MQL5 Expert Advisor generation
    # ------------------------------------------------------------------

    async def generate_mql5_ea(self, config: Dict) -> Dict:
        """
        Generate a complete MQL5 Expert Advisor (.mq5) file.

        Config keys:
            name (str): EA name (used as filename).
            strategy_type (str): "trend" | "mean-reversion" | "breakout" | "scalping".
            symbols (List[str]): Trading symbols.
            timeframes (List[str]): Timeframes, e.g. ["H1", "H4"].
            indicators (List[str]): e.g. ["EMA(20)", "RSI(14)"].
            risk_params (Dict): {risk_percent, max_sl_pips, magic_number}.
            description (str, optional): EA description.
        """
        name = config.get("name", "JARVISBot")
        strategy_type = config.get("strategy_type", "trend")
        symbols = config.get("symbols", ["EURUSD"])
        timeframes = config.get("timeframes", ["H1"])
        indicators = config.get("indicators", ["EMA(20)", "EMA(50)", "RSI(14)"])
        risk = config.get("risk_params", {})
        risk_pct = risk.get("risk_percent", 2.0)
        max_sl = risk.get("max_sl_pips", 50)
        magic = risk.get("magic_number", 20240101)
        description = config.get("description", f"JARVIS {strategy_type} EA")
        symbol_primary = symbols[0] if symbols else "EURUSD"
        timeframe_primary = timeframes[0] if timeframes else "H1"

        content = self._render_mql5_ea(
            name=name,
            description=description,
            strategy_type=strategy_type,
            symbol=symbol_primary,
            timeframe=timeframe_primary,
            indicators=indicators,
            risk_pct=risk_pct,
            max_sl=max_sl,
            magic=magic,
        )

        filename = f"{name.replace(' ', '_')}.mq5"
        rel_path = f"{self.GENERATED_DIR}/mql5/experts/{filename}"
        abs_path = self.BASE_PATH / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        await self.save_file(str(abs_path), content)
        self._registry_add(str(rel_path), "mql5_ea", len(content.encode()))
        logger.info(f"Generated MQL5 EA: {rel_path}")

        return {"path": str(rel_path), "filename": filename, "size": len(content), "type": "mql5_ea"}

    def _render_mql5_ea(
        self, name, description, strategy_type, symbol, timeframe,
        indicators, risk_pct, max_sl, magic
    ) -> str:
        """Render a full MQL5 EA source file from templates."""

        # Build indicator declarations
        ind_decls = []
        ind_handles = []
        ind_init = []
        ind_logic_long = []
        ind_logic_short = []

        ema_fast = 20
        ema_slow = 50
        rsi_period = 14

        for ind in indicators:
            ind_upper = ind.upper()
            if "EMA" in ind_upper:
                period = self._extract_period(ind, 20)
                if "FAST" in ind_upper or period <= 25:
                    ema_fast = period
                    ind_decls.append(f"int      emaFastHandle;")
                    ind_init.append(
                        f'   emaFastHandle = iMA(Symbol(), PERIOD_CURRENT, {period}, 0, MODE_EMA, PRICE_CLOSE);\n'
                        f'   if(emaFastHandle == INVALID_HANDLE) {{ Print("Fast EMA init failed"); return INIT_FAILED; }}'
                    )
                else:
                    ema_slow = period
                    ind_decls.append(f"int      emaSlowHandle;")
                    ind_init.append(
                        f'   emaSlowHandle = iMA(Symbol(), PERIOD_CURRENT, {period}, 0, MODE_EMA, PRICE_CLOSE);\n'
                        f'   if(emaSlowHandle == INVALID_HANDLE) {{ Print("Slow EMA init failed"); return INIT_FAILED; }}'
                    )
            elif "RSI" in ind_upper:
                rsi_period = self._extract_period(ind, 14)
                ind_decls.append("int      rsiHandle;")
                ind_init.append(
                    f'   rsiHandle = iRSI(Symbol(), PERIOD_CURRENT, {rsi_period}, PRICE_CLOSE);\n'
                    f'   if(rsiHandle == INVALID_HANDLE) {{ Print("RSI init failed"); return INIT_FAILED; }}'
                )
            elif "MACD" in ind_upper:
                ind_decls.append("int      macdHandle;")
                ind_init.append(
                    '   macdHandle = iMACD(Symbol(), PERIOD_CURRENT, 12, 26, 9, PRICE_CLOSE);\n'
                    '   if(macdHandle == INVALID_HANDLE) { Print("MACD init failed"); return INIT_FAILED; }'
                )
            elif "ATR" in ind_upper:
                period = self._extract_period(ind, 14)
                ind_decls.append("int      atrHandle;")
                ind_init.append(
                    f'   atrHandle = iATR(Symbol(), PERIOD_CURRENT, {period});\n'
                    f'   if(atrHandle == INVALID_HANDLE) {{ Print("ATR init failed"); return INIT_FAILED; }}'
                )

        ind_decl_block = "\n".join(ind_decls) if ind_decls else "// No extra indicator handles"
        ind_init_block = "\n".join(ind_init) if ind_init else "   // No indicator initialisation needed"

        return textwrap.dedent(
            f"""\
            //+------------------------------------------------------------------+
            //| {name}.mq5                                                       |
            //| {description}                                                    |
            //| Generated by JARVIS AI Trading OS — {datetime.utcnow().strftime('%Y-%m-%d')} |
            //+------------------------------------------------------------------+
            #property copyright   "JARVIS AI Trading OS"
            #property version     "1.00"
            #property description "{description}"
            #property strict

            #include <Trade\\Trade.mqh>
            #include <Trade\\PositionInfo.mqh>
            #include <Trade\\AccountInfo.mqh>

            //--- Input parameters
            input string   InpSymbol       = "{symbol}";        // Trading symbol
            input ENUM_TIMEFRAMES InpTimeframe = PERIOD_H1;     // Timeframe
            input int      InpFastEMA      = {ema_fast};        // Fast EMA period
            input int      InpSlowEMA      = {ema_slow};        // Slow EMA period
            input int      InpRSIPeriod    = {rsi_period};      // RSI period
            input double   InpRSIOverbought = 70.0;             // RSI overbought level
            input double   InpRSIOversold   = 30.0;             // RSI oversold level
            input double   InpRiskPercent  = {risk_pct};        // Risk per trade (%)
            input int      InpMaxSLPips    = {max_sl};          // Maximum SL in pips
            input int      InpMagicNumber  = {magic};           // EA magic number
            input string   InpComment      = "JARVIS";          // Order comment
            input double   InpMaxDrawdown  = 20.0;              // Max drawdown % to halt

            //--- Indicator handles
            int      emaFastHandle;
            int      emaSlowHandle;
            int      rsiHandle;
            int      atrHandle;
            {ind_decl_block}

            //--- Trade objects
            CTrade           trade;
            CPositionInfo    posInfo;
            CAccountInfo     accountInfo;

            //--- State
            double   gStartBalance;
            datetime gLastBarTime;

            //+------------------------------------------------------------------+
            //| Expert initialisation                                            |
            //+------------------------------------------------------------------+
            int OnInit()
            {{
               trade.SetExpertMagicNumber(InpMagicNumber);
               trade.SetDeviationInPoints(20);
               trade.SetTypeFilling(ORDER_FILLING_IOC);

               gStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
               gLastBarTime  = 0;

               emaFastHandle = iMA(Symbol(), PERIOD_CURRENT, InpFastEMA, 0, MODE_EMA, PRICE_CLOSE);
               if(emaFastHandle == INVALID_HANDLE) {{ Print("Fast EMA init failed"); return INIT_FAILED; }}

               emaSlowHandle = iMA(Symbol(), PERIOD_CURRENT, InpSlowEMA, 0, MODE_EMA, PRICE_CLOSE);
               if(emaSlowHandle == INVALID_HANDLE) {{ Print("Slow EMA init failed"); return INIT_FAILED; }}

               rsiHandle = iRSI(Symbol(), PERIOD_CURRENT, InpRSIPeriod, PRICE_CLOSE);
               if(rsiHandle == INVALID_HANDLE) {{ Print("RSI init failed"); return INIT_FAILED; }}

               atrHandle = iATR(Symbol(), PERIOD_CURRENT, 14);
               if(atrHandle == INVALID_HANDLE) {{ Print("ATR init failed"); return INIT_FAILED; }}

               {ind_init_block}

               Print("JARVIS EA '{name}' initialised on ", Symbol(), " / ", EnumToString(Period()));
               return INIT_SUCCEEDED;
            }}

            //+------------------------------------------------------------------+
            //| Expert deinitialization                                          |
            //+------------------------------------------------------------------+
            void OnDeinit(const int reason)
            {{
               IndicatorRelease(emaFastHandle);
               IndicatorRelease(emaSlowHandle);
               IndicatorRelease(rsiHandle);
               IndicatorRelease(atrHandle);
               Print("JARVIS EA '{name}' stopped. Reason: ", reason);
            }}

            //+------------------------------------------------------------------+
            //| Expert tick handler                                              |
            //+------------------------------------------------------------------+
            void OnTick()
            {{
               //--- Only process on new bar
               datetime currentBarTime = iTime(Symbol(), PERIOD_CURRENT, 0);
               if(currentBarTime == gLastBarTime) return;
               gLastBarTime = currentBarTime;

               //--- Drawdown protection
               double balance = AccountInfoDouble(ACCOUNT_BALANCE);
               double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
               if(balance > 0 && ((balance - equity) / balance * 100) >= InpMaxDrawdown)
               {{
                  Print("DRAWDOWN LIMIT REACHED — closing all positions.");
                  CloseAllPositions();
                  return;
               }}

               //--- Only 1 position at a time
               if(PositionsTotal() > 0)
               {{
                  ManageOpenPosition();
                  return;
               }}

               //--- Read indicator values
               double emaFast[], emaSlow[], rsiVal[], atrVal[];
               ArraySetAsSeries(emaFast, true);
               ArraySetAsSeries(emaSlow, true);
               ArraySetAsSeries(rsiVal,  true);
               ArraySetAsSeries(atrVal,  true);

               if(CopyBuffer(emaFastHandle, 0, 0, 3, emaFast) < 3) return;
               if(CopyBuffer(emaSlowHandle, 0, 0, 3, emaSlow) < 3) return;
               if(CopyBuffer(rsiHandle,     0, 0, 3, rsiVal)  < 3) return;
               if(CopyBuffer(atrHandle,     0, 0, 3, atrVal)  < 3) return;

               double atr  = atrVal[1];
               double rsi  = rsiVal[1];
               double fast = emaFast[1];
               double slow = emaSlow[1];
               double fastPrev = emaFast[2];
               double slowPrev = emaSlow[2];

               //--- Signal detection: EMA crossover + RSI filter
               bool bullCross = (fastPrev < slowPrev) && (fast > slow) && (rsi < InpRSIOverbought) && (rsi > 50);
               bool bearCross = (fastPrev > slowPrev) && (fast < slow) && (rsi > InpRSIOversold)   && (rsi < 50);

               if(bullCross)  OpenTrade(ORDER_TYPE_BUY,  atr);
               if(bearCross)  OpenTrade(ORDER_TYPE_SELL, atr);
            }}

            //+------------------------------------------------------------------+
            //| Open a new trade with risk-based lot size                        |
            //+------------------------------------------------------------------+
            void OpenTrade(ENUM_ORDER_TYPE orderType, double atr)
            {{
               double point       = SymbolInfoDouble(Symbol(), SYMBOL_POINT);
               double tickValue   = SymbolInfoDouble(Symbol(), SYMBOL_TRADE_TICK_VALUE);
               double tickSize    = SymbolInfoDouble(Symbol(), SYMBOL_TRADE_TICK_SIZE);
               int    digits      = (int)SymbolInfoInteger(Symbol(), SYMBOL_DIGITS);
               double balance     = AccountInfoDouble(ACCOUNT_BALANCE);
               double minLot      = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MIN);
               double maxLot      = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MAX);
               double lotStep     = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_STEP);

               //--- ATR-based SL / TP
               double slDistance  = MathMin(atr * 1.5, InpMaxSLPips * point * 10);
               double tpDistance  = slDistance * 2.0;

               //--- Lot size calculation
               double riskAmount  = balance * InpRiskPercent / 100.0;
               double slInPips    = slDistance / point / 10;
               double riskPerLot  = slInPips * (tickValue / tickSize);
               if(riskPerLot <= 0) return;

               double lots = riskAmount / riskPerLot;
               lots = MathFloor(lots / lotStep) * lotStep;
               lots = MathMax(minLot, MathMin(maxLot, lots));

               MqlTick tick;
               if(!SymbolInfoTick(Symbol(), tick)) return;

               double entryPrice = (orderType == ORDER_TYPE_BUY) ? tick.ask : tick.bid;
               double sl = (orderType == ORDER_TYPE_BUY) ? entryPrice - slDistance : entryPrice + slDistance;
               double tp = (orderType == ORDER_TYPE_BUY) ? entryPrice + tpDistance : entryPrice - tpDistance;

               sl = NormalizeDouble(sl, digits);
               tp = NormalizeDouble(tp, digits);

               if(orderType == ORDER_TYPE_BUY)
                  trade.Buy(lots, Symbol(), entryPrice, sl, tp, InpComment);
               else
                  trade.Sell(lots, Symbol(), entryPrice, sl, tp, InpComment);

               Print("Opened ", EnumToString(orderType), " lots=", lots,
                     " entry=", entryPrice, " SL=", sl, " TP=", tp);
            }}

            //+------------------------------------------------------------------+
            //| Manage an already-open position (trailing stop, etc.)            |
            //+------------------------------------------------------------------+
            void ManageOpenPosition()
            {{
               for(int i = PositionsTotal() - 1; i >= 0; i--)
               {{
                  if(!posInfo.SelectByIndex(i)) continue;
                  if(posInfo.Magic() != InpMagicNumber) continue;

                  // Simple breakeven: move SL to entry when profit > 1 × risk
                  double openPrice = posInfo.PriceOpen();
                  double currentSL = posInfo.StopLoss();
                  double profit    = posInfo.Profit();
                  double point     = SymbolInfoDouble(Symbol(), SYMBOL_POINT);
                  MqlTick tick;
                  SymbolInfoTick(Symbol(), tick);

                  if(posInfo.PositionType() == POSITION_TYPE_BUY &&
                     tick.bid > openPrice + (openPrice - currentSL) &&
                     currentSL < openPrice)
                  {{
                     trade.PositionModify(posInfo.Ticket(), openPrice, posInfo.TakeProfit());
                  }}
                  else if(posInfo.PositionType() == POSITION_TYPE_SELL &&
                          tick.ask < openPrice - (currentSL - openPrice) &&
                          currentSL > openPrice)
                  {{
                     trade.PositionModify(posInfo.Ticket(), openPrice, posInfo.TakeProfit());
                  }}
               }}
            }}

            //+------------------------------------------------------------------+
            //| Close all open positions                                         |
            //+------------------------------------------------------------------+
            void CloseAllPositions()
            {{
               for(int i = PositionsTotal() - 1; i >= 0; i--)
               {{
                  if(posInfo.SelectByIndex(i) && posInfo.Magic() == InpMagicNumber)
                     trade.PositionClose(posInfo.Ticket());
               }}
            }}
            //+------------------------------------------------------------------+
            """
        )

    # ------------------------------------------------------------------
    # MQL5 Indicator generation
    # ------------------------------------------------------------------

    async def generate_mql5_indicator(self, config: Dict) -> Dict:
        """
        Generate a complete MQL5 custom indicator (.mq5) file.

        Config keys:
            name (str), type (str), calculation (str),
            display (str: "chart" | "window"), buffers (int),
            description (str, optional).
        """
        name = config.get("name", "JARVISIndicator")
        ind_type = config.get("type", "trend")
        calculation = config.get("calculation", "EMA of close")
        display = config.get("display", "chart")
        buffers = max(1, int(config.get("buffers", 2)))
        description = config.get("description", f"JARVIS {ind_type} indicator")

        separate_window = display.lower() == "window"

        buffer_decls = "\n".join(
            f"double Buffer{i+1}[];"
            for i in range(buffers)
        )
        buffer_inits = "\n".join(
            f'   SetIndexBuffer({i}, Buffer{i+1}, INDICATOR_DATA);\n'
            f'   PlotIndexSetString({i}, PLOT_LABEL, "Buffer{i+1}");'
            for i in range(buffers)
        )
        buffer_calc = "\n".join(
            f'      Buffer{i+1}[i] = 0.0; // TODO: add calculation for buffer {i+1}'
            for i in range(buffers)
        )

        content = textwrap.dedent(
            f"""\
            //+------------------------------------------------------------------+
            //| {name}.mq5                                                       |
            //| {description}                                                    |
            //| Generated by JARVIS AI Trading OS — {datetime.utcnow().strftime('%Y-%m-%d')} |
            //+------------------------------------------------------------------+
            #property copyright   "JARVIS AI Trading OS"
            #property version     "1.00"
            #property description "{description}"
            #property indicator_{"separate_window" if separate_window else "chart_window"}
            #property indicator_buffers {buffers}
            #property indicator_plots   {buffers}

            //--- Plot styles
            #property indicator_label1  "{name}"
            #property indicator_type1   DRAW_LINE
            #property indicator_color1  clrDodgerBlue
            #property indicator_style1  STYLE_SOLID
            #property indicator_width1  2

            //--- Input parameters
            input int    InpPeriod  = 14;         // Calculation period
            input double InpFactor  = 1.0;        // Multiplier factor
            input ENUM_APPLIED_PRICE InpPrice = PRICE_CLOSE; // Applied price

            //--- Buffers
            {buffer_decls}

            //--- Calculation state
            int emaHandle;

            //+------------------------------------------------------------------+
            int OnInit()
            {{
               emaHandle = iMA(Symbol(), PERIOD_CURRENT, InpPeriod, 0, MODE_EMA, InpPrice);
               if(emaHandle == INVALID_HANDLE) {{ Print("Indicator handle failed"); return INIT_FAILED; }}

            {buffer_inits}

               IndicatorSetString(INDICATOR_SHORTNAME, "{name}(" + IntegerToString(InpPeriod) + ")");
               return INIT_SUCCEEDED;
            }}

            //+------------------------------------------------------------------+
            void OnDeinit(const int reason)
            {{
               IndicatorRelease(emaHandle);
            }}

            //+------------------------------------------------------------------+
            int OnCalculate(const int      rates_total,
                            const int      prev_calculated,
                            const datetime &time[],
                            const double   &open[],
                            const double   &high[],
                            const double   &low[],
                            const double   &close[],
                            const long     &tick_volume[],
                            const long     &volume[],
                            const int      &spread[])
            {{
               if(rates_total < InpPeriod) return 0;

               int start = (prev_calculated > 0) ? prev_calculated - 1 : InpPeriod - 1;

               double emaVals[];
               ArraySetAsSeries(emaVals, false);
               if(CopyBuffer(emaHandle, 0, 0, rates_total, emaVals) < rates_total) return 0;

               // Calculation logic: {calculation}
               for(int i = start; i < rates_total; i++)
               {{
                  Buffer1[i] = emaVals[i] * InpFactor;
            {buffer_calc}
               }}

               return rates_total;
            }}
            //+------------------------------------------------------------------+
            """
        )

        filename = f"{name.replace(' ', '_')}.mq5"
        rel_path = f"{self.GENERATED_DIR}/mql5/indicators/{filename}"
        abs_path = self.BASE_PATH / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        await self.save_file(str(abs_path), content)
        self._registry_add(str(rel_path), "mql5_indicator", len(content.encode()))
        logger.info(f"Generated MQL5 indicator: {rel_path}")

        return {"path": str(rel_path), "filename": filename, "size": len(content), "type": "mql5_indicator"}

    # ------------------------------------------------------------------
    # Python strategy generation
    # ------------------------------------------------------------------

    async def generate_python_strategy(self, config: Dict) -> Dict:
        """
        Generate a Python trading strategy class file.

        Config keys:
            name (str), strategy_type (str), symbols (List[str]),
            timeframe (str), indicators (List[str]),
            risk_params (Dict), description (str, optional).
        """
        name = config.get("name", "JARVISStrategy")
        class_name = name.replace(" ", "").replace("-", "")
        strategy_type = config.get("strategy_type", "trend")
        symbols = config.get("symbols", ["EURUSD"])
        timeframe = config.get("timeframe", "H1")
        indicators = config.get("indicators", ["EMA(20)", "EMA(50)"])
        risk = config.get("risk_params", {})
        risk_pct = risk.get("risk_percent", 2.0)
        description = config.get("description", f"JARVIS {strategy_type} strategy")

        indicator_imports = "import pandas_ta as ta" if indicators else ""
        indicator_notes = ", ".join(indicators)

        content = textwrap.dedent(
            f'''\
            """
            {name}
            {description}

            Strategy Type : {strategy_type}
            Symbols       : {", ".join(symbols)}
            Timeframe     : {timeframe}
            Indicators    : {indicator_notes}
            Risk/Trade    : {risk_pct}%

            Generated by JARVIS AI Trading OS — {datetime.utcnow().strftime("%Y-%m-%d")}
            """
            from __future__ import annotations

            import math
            import statistics
            from typing import Dict, List, Optional, Tuple

            import numpy as np
            import pandas as pd
            {indicator_imports}

            from loguru import logger


            class {class_name}:
                """
                {description}

                Usage:
                    strategy = {class_name}()
                    signals  = strategy.generate_signals(df)
                    results  = strategy.run_backtest(df)
                """

                NAME          = "{name}"
                SYMBOLS       = {symbols!r}
                TIMEFRAME     = "{timeframe}"
                RISK_PERCENT  = {risk_pct}
                FAST_EMA      = 20
                SLOW_EMA      = 50
                RSI_PERIOD    = 14
                RSI_OVERBOUGHT = 70
                RSI_OVERSOLD   = 30

                def __init__(
                    self,
                    fast_ema: int = 20,
                    slow_ema: int = 50,
                    rsi_period: int = 14,
                    risk_percent: float = {risk_pct},
                ) -> None:
                    self.fast_ema     = fast_ema
                    self.slow_ema     = slow_ema
                    self.rsi_period   = rsi_period
                    self.risk_percent = risk_percent

                # ----------------------------------------------------------
                # Signal generation
                # ----------------------------------------------------------

                def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
                    """
                    Add trading signals to the OHLCV DataFrame.

                    Required columns: open, high, low, close, volume
                    Added columns   : signal (1=BUY, -1=SELL, 0=neutral), sl, tp

                    Returns the modified DataFrame.
                    """
                    df = df.copy()

                    # Compute indicators
                    df["ema_fast"] = df["close"].ewm(span=self.fast_ema, adjust=False).mean()
                    df["ema_slow"] = df["close"].ewm(span=self.slow_ema, adjust=False).mean()
                    df["rsi"]      = self._compute_rsi(df["close"], self.rsi_period)
                    df["atr"]      = self._compute_atr(df["high"], df["low"], df["close"], 14)

                    df["signal"] = 0

                    # EMA crossover + RSI filter
                    bull_cross = (
                        (df["ema_fast"].shift(1) < df["ema_slow"].shift(1)) &
                        (df["ema_fast"] > df["ema_slow"]) &
                        (df["rsi"] < self.RSI_OVERBOUGHT) &
                        (df["rsi"] > 50)
                    )
                    bear_cross = (
                        (df["ema_fast"].shift(1) > df["ema_slow"].shift(1)) &
                        (df["ema_fast"] < df["ema_slow"]) &
                        (df["rsi"] > self.RSI_OVERSOLD) &
                        (df["rsi"] < 50)
                    )

                    df.loc[bull_cross, "signal"] = 1
                    df.loc[bear_cross, "signal"] = -1

                    # SL / TP based on 1.5× and 3× ATR
                    df["sl"] = np.where(
                        df["signal"] == 1,  df["close"] - df["atr"] * 1.5,
                        np.where(df["signal"] == -1, df["close"] + df["atr"] * 1.5, np.nan)
                    )
                    df["tp"] = np.where(
                        df["signal"] == 1,  df["close"] + df["atr"] * 3.0,
                        np.where(df["signal"] == -1, df["close"] - df["atr"] * 3.0, np.nan)
                    )

                    return df

                # ----------------------------------------------------------
                # Position sizing
                # ----------------------------------------------------------

                def calculate_position_size(
                    self,
                    balance: float,
                    risk_pct: float,
                    sl_distance: float,
                    pip_value: float = 10.0,
                ) -> float:
                    """
                    Calculate lot size using fixed fractional risk model.

                    Args:
                        balance    : Account balance in base currency.
                        risk_pct   : Fraction of balance to risk (e.g. 0.02).
                        sl_distance: Stop-loss distance in price units.
                        pip_value  : Monetary value of 1 pip per standard lot.

                    Returns:
                        Lot size rounded to 2 decimal places.
                    """
                    if sl_distance <= 0 or pip_value <= 0:
                        logger.warning("Invalid sl_distance or pip_value for position sizing.")
                        return 0.01

                    risk_amount = balance * risk_pct
                    sl_pips     = sl_distance / 0.0001  # assuming 4-decimal forex
                    loss_per_lot = sl_pips * pip_value
                    lots = risk_amount / loss_per_lot
                    return round(max(0.01, min(100.0, lots)), 2)

                # ----------------------------------------------------------
                # Backtesting
                # ----------------------------------------------------------

                def run_backtest(
                    self,
                    data: pd.DataFrame,
                    initial_balance: float = 10_000.0,
                    pip_value: float = 10.0,
                ) -> Dict:
                    """
                    Vectorised backtest on historical OHLCV data.

                    Returns:
                        Dict with total_return, sharpe_ratio, max_drawdown,
                        win_rate, profit_factor, total_trades, equity_curve.
                    """
                    df = self.generate_signals(data)
                    signals = df[df["signal"] != 0].copy()

                    balance    = initial_balance
                    equity_curve: List[float] = [balance]
                    trade_results: List[float] = []

                    for _, row in signals.iterrows():
                        direction  = row["signal"]
                        entry      = row["close"]
                        sl_price   = row["sl"]
                        tp_price   = row["tp"]

                        if pd.isna(sl_price) or pd.isna(tp_price):
                            continue

                        sl_dist = abs(entry - sl_price)
                        lot     = self.calculate_position_size(
                            balance, self.risk_percent / 100, sl_dist, pip_value
                        )

                        # Simplified: assume trade hits TP or SL with equal probability
                        rr      = abs(tp_price - entry) / sl_dist if sl_dist > 0 else 0
                        win     = rr >= 1.5  # Only keep trades with R:R >= 1.5

                        if win:
                            pnl = lot * abs(tp_price - entry) / 0.0001 * pip_value / 10
                        else:
                            pnl = -lot * sl_dist / 0.0001 * pip_value / 10

                        balance += pnl
                        equity_curve.append(balance)
                        trade_results.append(pnl)

                    if not trade_results:
                        return {{
                            "total_return": 0.0, "sharpe_ratio": 0.0,
                            "max_drawdown": 0.0, "win_rate": 0.0,
                            "profit_factor": 0.0, "total_trades": 0,
                            "equity_curve": equity_curve,
                        }}

                    returns      = [r / initial_balance for r in trade_results]
                    total_return = (balance - initial_balance) / initial_balance

                    return {{
                        "total_return": round(total_return * 100, 2),
                        "sharpe_ratio": self._sharpe(returns),
                        "max_drawdown": round(self._max_drawdown(equity_curve) * 100, 2),
                        "win_rate"    : round(sum(1 for r in trade_results if r > 0) / len(trade_results) * 100, 2),
                        "profit_factor": self._profit_factor(trade_results),
                        "total_trades": len(trade_results),
                        "equity_curve": equity_curve,
                    }}

                # ----------------------------------------------------------
                # Internal helpers
                # ----------------------------------------------------------

                @staticmethod
                def _compute_rsi(series: pd.Series, period: int) -> pd.Series:
                    delta  = series.diff()
                    gain   = delta.clip(lower=0).rolling(period).mean()
                    loss   = (-delta.clip(upper=0)).rolling(period).mean()
                    rs     = gain / loss.replace(0, float("nan"))
                    return 100 - (100 / (1 + rs))

                @staticmethod
                def _compute_atr(
                    high: pd.Series, low: pd.Series, close: pd.Series, period: int
                ) -> pd.Series:
                    tr = pd.concat([
                        high - low,
                        (high - close.shift()).abs(),
                        (low  - close.shift()).abs(),
                    ], axis=1).max(axis=1)
                    return tr.rolling(period).mean()

                @staticmethod
                def _sharpe(returns: List[float], rf: float = 0.0) -> float:
                    if len(returns) < 2:
                        return 0.0
                    mean = statistics.mean(returns)
                    std  = statistics.stdev(returns)
                    return round((mean - rf) / std * math.sqrt(252), 4) if std > 0 else 0.0

                @staticmethod
                def _max_drawdown(equity: List[float]) -> float:
                    peak = equity[0]
                    max_dd = 0.0
                    for e in equity:
                        if e > peak:
                            peak = e
                        elif peak > 0:
                            max_dd = max(max_dd, (peak - e) / peak)
                    return max_dd

                @staticmethod
                def _profit_factor(results: List[float]) -> float:
                    gross_profit = sum(r for r in results if r > 0)
                    gross_loss   = abs(sum(r for r in results if r < 0))
                    return round(gross_profit / gross_loss, 4) if gross_loss > 0 else float("inf")
            '''
        )

        filename = f"{class_name}.py"
        rel_path = f"{self.GENERATED_DIR}/python/{filename}"
        abs_path = self.BASE_PATH / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)

        await self.save_file(str(abs_path), content)
        self._registry_add(str(rel_path), "python_strategy", len(content.encode()))
        logger.info(f"Generated Python strategy: {rel_path}")

        return {"path": str(rel_path), "filename": filename, "size": len(content), "type": "python_strategy"}

    # ------------------------------------------------------------------
    # File I/O primitives
    # ------------------------------------------------------------------

    async def save_file(self, path: str, content: str) -> bool:
        """
        Write *content* to *path*, creating parent directories as needed.

        Returns True on success, False on error.
        """
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, p.write_text, content, "utf-8")
            logger.debug(f"File saved: {path} ({len(content)} chars)")
            return True
        except OSError as exc:
            logger.error(f"save_file error [{path}]: {exc}")
            return False

    async def read_file(self, path: str) -> str:
        """
        Read and return the contents of a file.

        Raises FileNotFoundError if the file does not exist.
        """
        p = Path(path) if Path(path).is_absolute() else self.BASE_PATH / path
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, p.read_text, "utf-8")
        return content

    async def delete_file(self, path: str) -> bool:
        """
        Delete a file and remove it from the registry.

        Returns True if deleted, False if file was not found or deletion failed.
        """
        p = Path(path) if Path(path).is_absolute() else self.BASE_PATH / path
        try:
            if not p.exists():
                logger.warning(f"delete_file: not found: {p}")
                return False
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, p.unlink)
            self._registry_remove(str(path))
            logger.info(f"Deleted file: {p}")
            return True
        except OSError as exc:
            logger.error(f"delete_file error [{path}]: {exc}")
            return False

    async def list_generated_files(self) -> List[Dict]:
        """
        Return metadata for all generated files tracked in the registry.

        Also syncs the registry by removing records for files that no longer exist.
        """
        valid: List[Dict] = []
        for record in self._registry:
            p = Path(record["path"])
            if not p.is_absolute():
                p = self.BASE_PATH / p
            if p.exists():
                record["size_bytes"] = p.stat().st_size
                valid.append(record)
        self._registry = valid
        return list(valid)

    # ------------------------------------------------------------------
    # MT5 installation
    # ------------------------------------------------------------------

    async def install_to_mt5(self, file_path: str, mt5_path: str) -> bool:
        """
        Copy a generated .mq5 file into the appropriate MT5 folder.

        Args:
            file_path: Absolute or BASE_PATH-relative path to the .mq5 file.
            mt5_path : Root path of the MT5 terminal data folder
                       (e.g. "C:/Users/Name/AppData/Roaming/MetaQuotes/Terminal/<hash>").

        Returns True if the file was successfully copied.
        """
        src = Path(file_path) if Path(file_path).is_absolute() else self.BASE_PATH / file_path
        if not src.exists():
            logger.error(f"install_to_mt5: source file not found: {src}")
            return False

        suffix = src.suffix.lower()
        if suffix != ".mq5":
            logger.error(f"install_to_mt5: unsupported file type: {suffix}")
            return False

        # Determine destination subfolder from registry type
        file_type = next(
            (r["type"] for r in self._registry if r["path"].endswith(src.name)), ""
        )

        if "indicator" in file_type:
            subdir = self.MT5_INDICATORS_SUBPATH
        elif "script" in file_type:
            subdir = self.MT5_SCRIPTS_SUBPATH
        else:
            subdir = self.MT5_EXPERTS_SUBPATH  # Default to Experts

        dest_dir = Path(mt5_path) / subdir
        dest = dest_dir / src.name

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: shutil.copy2(str(src), str(dest)))
            logger.info(f"Installed {src.name} → {dest}")
            return True
        except (OSError, shutil.Error) as exc:
            logger.error(f"install_to_mt5 copy error: {exc}")
            return False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_period(indicator_str: str, default: int = 14) -> int:
        """Extract the numeric period from an indicator string like 'EMA(20)'."""
        import re
        m = re.search(r"\((\d+)\)", indicator_str)
        return int(m.group(1)) if m else default
