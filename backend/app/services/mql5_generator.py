from backend.app.models.schemas import GeneratedFile, StrategySpec, TradeSide
from backend.app.services.strategy_factory import StrategyFactory


class MQL5Generator:
    def create_expert_advisor(self, strategy: StrategySpec) -> GeneratedFile:
        strategy_id = StrategyFactory.strategy_id(strategy)
        symbol = strategy.symbols[0]
        content = f"""//+------------------------------------------------------------------+
//| JARVIS generated Expert Advisor                                 |
//| Strategy: {strategy.name}
//+------------------------------------------------------------------+
#property strict
#include <Trade/Trade.mqh>

input double RiskPercent = {strategy.risk_percent};
input int MaxSpreadPoints = {strategy.parameters.get("max_spread_points", 25)};
input int MagicNumber = 55001;
input bool EnableTrailingStop = {"true" if strategy.parameters.get("trailing_stop") != "disabled" else "false"};

CTrade trade;

bool HasOpenPosition()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      ulong ticket = PositionGetTicket(i);
      if(PositionSelectByTicket(ticket) && PositionGetInteger(POSITION_MAGIC) == MagicNumber)
      {{
         return true;
      }}
   }}
   return false;
}}

int OnInit()
{{
   trade.SetExpertMagicNumber(MagicNumber);
   Print("JARVIS EA initialized for {strategy.name}");
   return INIT_SUCCEEDED;
}}

void OnTick()
{{
   if(_Symbol != "{symbol}") return;
   if(HasOpenPosition()) return;

   double spread = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point;
   if(spread > MaxSpreadPoints) return;

   double currentClose = iClose(_Symbol, PERIOD_CURRENT, 1);
   double previousClose = iClose(_Symbol, PERIOD_CURRENT, 2);

   if(currentClose > previousClose)
   {{
      OpenTrade(ORDER_TYPE_BUY);
   }}
   else if(currentClose < previousClose)
   {{
      OpenTrade(ORDER_TYPE_SELL);
   }}
}}

void OpenTrade(ENUM_ORDER_TYPE orderType)
{{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double price = orderType == ORDER_TYPE_BUY ? ask : bid;
   double stopDistance = 300 * _Point;
   double sl = orderType == ORDER_TYPE_BUY ? price - stopDistance : price + stopDistance;
   double tp = orderType == ORDER_TYPE_BUY ? price + stopDistance * 2 : price - stopDistance * 2;
   double lots = 0.01;

   if(orderType == ORDER_TYPE_BUY)
      trade.Buy(lots, _Symbol, price, sl, tp, "JARVIS {strategy_id}");
   else
      trade.Sell(lots, _Symbol, price, sl, tp, "JARVIS {strategy_id}");
}}
"""
        return GeneratedFile(
            path=f"mql5/Experts/{strategy_id}.mq5",
            language="mql5",
            purpose="MetaTrader 5 Expert Advisor",
            content=content,
        )

    def create_indicator(self, strategy: StrategySpec) -> GeneratedFile:
        strategy_id = StrategyFactory.strategy_id(strategy)
        content = f"""//+------------------------------------------------------------------+
//| JARVIS generated signal indicator                               |
//+------------------------------------------------------------------+
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots 2

double BuyBuffer[];
double SellBuffer[];

int OnInit()
{{
   SetIndexBuffer(0, BuyBuffer, INDICATOR_DATA);
   SetIndexBuffer(1, SellBuffer, INDICATOR_DATA);
   PlotIndexSetInteger(0, PLOT_ARROW, 233);
   PlotIndexSetInteger(1, PLOT_ARROW, 234);
   return INIT_SUCCEEDED;
}}

int OnCalculate(const int rates_total, const int prev_calculated, const datetime &time[],
                const double &open[], const double &high[], const double &low[],
                const double &close[], const long &tick_volume[], const long &volume[],
                const int &spread[])
{{
   for(int i = MathMax(1, prev_calculated - 1); i < rates_total; i++)
   {{
      BuyBuffer[i] = EMPTY_VALUE;
      SellBuffer[i] = EMPTY_VALUE;
      if(close[i] > open[i] && close[i - 1] < open[i - 1]) BuyBuffer[i] = low[i];
      if(close[i] < open[i] && close[i - 1] > open[i - 1]) SellBuffer[i] = high[i];
   }}
   return rates_total;
}}
"""
        return GeneratedFile(
            path=f"mql5/Indicators/{strategy_id}_signals.mq5",
            language="mql5",
            purpose="MetaTrader 5 custom indicator",
            content=content,
        )

    @staticmethod
    def side_to_order(side: TradeSide) -> str:
        return "ORDER_TYPE_BUY" if side == TradeSide.BUY else "ORDER_TYPE_SELL"
