//+------------------------------------------------------------------+
//| GoldScalper.mq5                                                        |
//| JARVIS AI Trading System - Gold Scalper                          |
//+------------------------------------------------------------------+
#property copyright "JARVIS AI"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

input group "=== Trading Settings ==="
input double   InpRiskPercent      = 1.0;
input int      InpMagicNumber      = 11001;
input string   InpComment          = "JARVIS_SCALPER";
input int      InpMaxTrades        = 3;

input group "=== Stop Loss / Take Profit ==="
input int      InpStopLoss         = 25;
input int      InpTakeProfit       = 50;
input bool     InpUseTrailingStop  = true;
input int      InpTrailingStart    = 15;
input int      InpTrailingStep     = 5;

input group "=== RSI Settings ==="
input int      InpRSIPeriod        = 14;
input double   InpRSIOversold      = 30.0;
input double   InpRSIOverbought    = 70.0;

input group "=== Stochastic Settings ==="
input int      InpStochK           = 5;
input int      InpStochD           = 3;
input int      InpStochSlowing     = 3;
input double   InpStochOversold    = 20.0;
input double   InpStochOverbought  = 80.0;

input group "=== ATR Filter ==="
input int      InpATRPeriod        = 14;
input double   InpMinATR           = 0.5;
input double   InpMaxATR           = 5.0;

input group "=== Session Filter ==="
input bool     InpLondonSession    = true;
input bool     InpNewYorkSession   = true;

CTrade        Trade;
CPositionInfo PositionInfo;
CAccountInfo  AccountInfo;

int     handleRSI, handleStoch, handleATR;
datetime lastBar = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   Trade.SetExpertMagicNumber(InpMagicNumber);
   Trade.SetDeviationInPoints(20);
   Trade.SetTypeFilling(ORDER_FILLING_FOK);

   handleRSI   = iRSI(_Symbol, PERIOD_M5, InpRSIPeriod, PRICE_CLOSE);
   handleStoch = iStochastic(_Symbol, PERIOD_M5, InpStochK, InpStochD,
                              InpStochSlowing, MODE_SMA, STO_LOWHIGH);
   handleATR   = iATR(_Symbol, PERIOD_M5, InpATRPeriod);

   if(handleRSI   == INVALID_HANDLE ||
      handleStoch == INVALID_HANDLE ||
      handleATR   == INVALID_HANDLE)
   {
      Print("Failed to create indicator handles. Error: ", GetLastError());
      return INIT_FAILED;
   }

   Print("GoldScalper initialised on ", _Symbol, " M5");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(handleRSI);
   IndicatorRelease(handleStoch);
   IndicatorRelease(handleATR);
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime currentBar = iTime(_Symbol, PERIOD_M5, 0);
   if(currentBar == lastBar) return;
   lastBar = currentBar;

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return;
   if(!IsSessionActive()) return;

   double rsi[2], stochMain[2], stochSig[2], atr[2];
   if(CopyBuffer(handleRSI,   0, 1, 2, rsi)       < 2) return;
   if(CopyBuffer(handleStoch, 0, 1, 2, stochMain) < 2) return;
   if(CopyBuffer(handleStoch, 1, 1, 2, stochSig)  < 2) return;
   if(CopyBuffer(handleATR,   0, 1, 2, atr)       < 2) return;

   ManagePositions();

   if(CountPositions() >= InpMaxTrades) return;
   if(!IsATRValid(atr[0])) return;

   bool buySignal  = rsi[0] < InpRSIOversold   && stochMain[0] < InpStochOversold  &&
                     stochMain[0] > stochSig[0] && stochMain[1] <= stochSig[1];
   bool sellSignal = rsi[0] > InpRSIOverbought  && stochMain[0] > InpStochOverbought &&
                     stochMain[0] < stochSig[0] && stochMain[1] >= stochSig[1];

   if(buySignal)  OpenBuy();
   if(sellSignal) OpenSell();
}

//+------------------------------------------------------------------+
void OpenBuy()
{
   double ask  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl   = ask - InpStopLoss   * _Point * 10;
   double tp   = ask + InpTakeProfit * _Point * 10;
   double lots = CalculateLots(InpStopLoss * _Point * 10);
   if(lots <= 0) return;
   if(!Trade.Buy(lots, _Symbol, ask, sl, tp, InpComment))
      Print("Buy error: ", Trade.ResultRetcodeDescription());
}

//+------------------------------------------------------------------+
void OpenSell()
{
   double bid  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl   = bid + InpStopLoss   * _Point * 10;
   double tp   = bid - InpTakeProfit * _Point * 10;
   double lots = CalculateLots(InpStopLoss * _Point * 10);
   if(lots <= 0) return;
   if(!Trade.Sell(lots, _Symbol, bid, sl, tp, InpComment))
      Print("Sell error: ", Trade.ResultRetcodeDescription());
}

//+------------------------------------------------------------------+
void ManagePositions()
{
   if(!InpUseTrailingStop) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionInfo.SelectByIndex(i)) continue;
      if(PositionInfo.Symbol() != _Symbol || PositionInfo.Magic() != InpMagicNumber) continue;

      ulong ticket  = PositionInfo.Ticket();
      double open   = PositionInfo.PriceOpen();
      double curSL  = PositionInfo.StopLoss();
      double curTP  = PositionInfo.TakeProfit();
      double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double step   = InpTrailingStep  * _Point * 10;
      double start  = InpTrailingStart * _Point * 10;

      if(PositionInfo.PositionType() == POSITION_TYPE_BUY)
      {
         if(bid - open < start) continue;
         double newSL = bid - step;
         if(newSL > curSL + step)
            Trade.PositionModify(ticket, newSL, curTP);
      }
      else
      {
         if(open - ask < start) continue;
         double newSL = ask + step;
         if(curSL == 0 || newSL < curSL - step)
            Trade.PositionModify(ticket, newSL, curTP);
      }
   }
}

//+------------------------------------------------------------------+
bool IsSessionActive()
{
   MqlDateTime t;
   TimeToStruct(TimeGMT(), t);
   int hour = t.hour;
   bool london   = InpLondonSession  && hour >= 7  && hour < 16;
   bool newyork  = InpNewYorkSession && hour >= 13 && hour < 21;
   return london || newyork;
}

//+------------------------------------------------------------------+
bool IsATRValid(double atrVal)
{
   double point = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double atrPips = atrVal / (point * 10);
   return atrPips >= InpMinATR && atrPips <= InpMaxATR;
}

//+------------------------------------------------------------------+
double CalculateLots(double slDist)
{
   double balance   = AccountInfo.Balance();
   double risk      = balance * InpRiskPercent / 100.0;
   double tickVal   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize == 0 || tickVal == 0 || slDist == 0) return 0;
   double lots     = risk / (slDist / tickSize * tickVal);
   double minLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot   = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   lots = MathFloor(lots / lotStep) * lotStep;
   return MathMax(minLot, MathMin(maxLot, lots));
}

//+------------------------------------------------------------------+
int CountPositions()
{
   int cnt = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
      if(PositionInfo.SelectByIndex(i) &&
         PositionInfo.Symbol() == _Symbol &&
         PositionInfo.Magic()  == InpMagicNumber) cnt++;
   return cnt;
}
