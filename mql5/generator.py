from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


@dataclass(frozen=True)
class MQL5Artifact:
    filename: str
    content: str
    target_folder: str


class MQL5Generator:
    """Generates conservative Expert Advisor and indicator source files."""

    def create_expert_advisor(
        self,
        *,
        strategy_name: str,
        symbol: str,
        timeframe: str,
        risk_percent: float,
        include_trailing_stop: bool = True,
    ) -> MQL5Artifact:
        safe_name = self._safe_name(strategy_name)
        content = dedent(
            f"""
            //+------------------------------------------------------------------+
            //| JARVIS generated Expert Advisor                                  |
            //| Strategy: {strategy_name}                                        |
            //| Symbol: {symbol} | Timeframe: {timeframe}                        |
            //+------------------------------------------------------------------+
            #property strict
            #include <Trade/Trade.mqh>

            input double RiskPercent = {risk_percent:.2f};
            input int StopLossPoints = 250;
            input int TakeProfitPoints = 500;
            input bool EnableTrailingStop = {'true' if include_trailing_stop else 'false'};
            input int TrailingStopPoints = 150;
            input ulong MagicNumber = 20260515;

            CTrade trade;

            int OnInit()
              {{
               trade.SetExpertMagicNumber(MagicNumber);
               return(INIT_SUCCEEDED);
              }}

            void OnTick()
              {{
               ManageRisk();
               if(PositionsTotal() > 0)
                 {{
                  if(EnableTrailingStop) ApplyTrailingStop();
                  return;
                 }}

               double fastMa = iMA(_Symbol, PERIOD_CURRENT, 9, 0, MODE_EMA, PRICE_CLOSE, 0);
               double slowMa = iMA(_Symbol, PERIOD_CURRENT, 21, 0, MODE_EMA, PRICE_CLOSE, 0);
               double previousFastMa = iMA(_Symbol, PERIOD_CURRENT, 9, 0, MODE_EMA, PRICE_CLOSE, 1);
               double previousSlowMa = iMA(_Symbol, PERIOD_CURRENT, 21, 0, MODE_EMA, PRICE_CLOSE, 1);

               if(previousFastMa <= previousSlowMa && fastMa > slowMa)
                  OpenTrade(ORDER_TYPE_BUY);
               else if(previousFastMa >= previousSlowMa && fastMa < slowMa)
                  OpenTrade(ORDER_TYPE_SELL);
              }}

            void OpenTrade(ENUM_ORDER_TYPE orderType)
              {{
               if(PositionsTotal() > 0) return;

               double lot = CalculateLotSize();
               double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
               double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
               double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

               if(orderType == ORDER_TYPE_BUY)
                 {{
                  double sl = ask - StopLossPoints * point;
                  double tp = ask + TakeProfitPoints * point;
                  trade.Buy(lot, _Symbol, ask, sl, tp, "JARVIS generated buy");
                 }}
               else
                 {{
                  double sl = bid + StopLossPoints * point;
                  double tp = bid - TakeProfitPoints * point;
                  trade.Sell(lot, _Symbol, bid, sl, tp, "JARVIS generated sell");
                 }}
              }}

            double CalculateLotSize()
              {{
               double balance = AccountInfoDouble(ACCOUNT_BALANCE);
               double riskAmount = balance * (RiskPercent / 100.0);
               double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
               double rawLot = riskAmount / MathMax(StopLossPoints * tickValue, 1.0);
               double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
               double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
               return MathMax(minLot, MathFloor(rawLot / lotStep) * lotStep);
              }}

            void ManageRisk()
              {{
               for(int i = PositionsTotal() - 1; i >= 0; i--)
                 {{
                  ulong ticket = PositionGetTicket(i);
                  if(!PositionSelectByTicket(ticket)) continue;
                  double profit = PositionGetDouble(POSITION_PROFIT);
                  double balance = AccountInfoDouble(ACCOUNT_BALANCE);
                  if(profit < 0 && MathAbs(profit) >= balance * 0.20)
                    {{
                     trade.PositionClose(ticket);
                    }}
                 }}
              }}

            void ApplyTrailingStop()
              {{
               double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
               for(int i = PositionsTotal() - 1; i >= 0; i--)
                 {{
                  ulong ticket = PositionGetTicket(i);
                  if(!PositionSelectByTicket(ticket)) continue;
                  if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;

                  long type = PositionGetInteger(POSITION_TYPE);
                  double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
                  double currentSl = PositionGetDouble(POSITION_SL);
                  double currentTp = PositionGetDouble(POSITION_TP);
                  double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
                  double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

                  if(type == POSITION_TYPE_BUY)
                    {{
                     double newSl = bid - TrailingStopPoints * point;
                     if(newSl > openPrice && newSl > currentSl)
                        trade.PositionModify(ticket, newSl, currentTp);
                    }}
                  else if(type == POSITION_TYPE_SELL)
                    {{
                     double newSl = ask + TrailingStopPoints * point;
                     if(newSl < openPrice && (currentSl == 0 || newSl < currentSl))
                        trade.PositionModify(ticket, newSl, currentTp);
                    }}
                 }}
              }}
            """
        ).strip()
        return MQL5Artifact(filename=f"{safe_name}.mq5", content=content, target_folder="Experts/JARVIS")

    def create_indicator(self, *, indicator_name: str) -> MQL5Artifact:
        safe_name = self._safe_name(indicator_name)
        content = dedent(
            f"""
            //+------------------------------------------------------------------+
            //| JARVIS generated indicator: {indicator_name}                      |
            //+------------------------------------------------------------------+
            #property indicator_chart_window
            #property indicator_buffers 1
            #property indicator_plots 1

            double SignalBuffer[];

            int OnInit()
              {{
               SetIndexBuffer(0, SignalBuffer, INDICATOR_DATA);
               PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_LINE);
               return(INIT_SUCCEEDED);
              }}

            int OnCalculate(
               const int rates_total,
               const int prev_calculated,
               const datetime &time[],
               const double &open[],
               const double &high[],
               const double &low[],
               const double &close[],
               const long &tick_volume[],
               const long &volume[],
               const int &spread[])
              {{
               for(int i = prev_calculated; i < rates_total; i++)
                  SignalBuffer[i] = close[i];
               return(rates_total);
              }}
            """
        ).strip()
        return MQL5Artifact(filename=f"{safe_name}.mq5", content=content, target_folder="Indicators/JARVIS")

    def write_artifact(self, artifact: MQL5Artifact, root: Path) -> Path:
        target_dir = root / artifact.target_folder
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / artifact.filename
        target.write_text(artifact.content, encoding="utf-8")
        return target

    @staticmethod
    def _safe_name(value: str) -> str:
        cleaned = "".join(character if character.isalnum() else "_" for character in value)
        return cleaned.strip("_") or "JarvisStrategy"
