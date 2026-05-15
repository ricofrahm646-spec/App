//+------------------------------------------------------------------+
//| TrendBot.mq5                                                        |
//| JARVIS AI Trading System - Trend Following                       |
//+------------------------------------------------------------------+
#property copyright "JARVIS AI"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

input group "=== Trading Settings ==="
input double InpRiskPercent  = 2.0;
input int    InpMagicNumber  = 33001;
input string InpComment      = "JARVIS_TREND";

input group "=== EMA Settings ==="
input int    InpEMAFast      = 21;
input int    InpEMASlow      = 55;
input int    InpEMAFilter    = 200;
input ENUM_TIMEFRAMES InpHTF = PERIOD_H4;

input group "=== ADX Filter ==="
input int    InpADXPeriod    = 14;
input double InpADXMin       = 25.0;

input group "=== Risk Settings ==="
input int    InpStopLoss     = 50;
input int    InpTakeProfit   = 150;
input bool   InpUseTrailing  = true;
input int    InpTrailingStart= 50;
input int    InpTrailingStep = 15;

CTrade        Trade;
CPositionInfo PositionInfo;
CAccountInfo  AccountInfo;

int      handleFast, handleSlow, handleFilter, handleADX;
datetime lastBar = 0;
bool     lastBullish = false;

//+------------------------------------------------------------------+
int OnInit()
{
   Trade.SetExpertMagicNumber(InpMagicNumber);
   Trade.SetDeviationInPoints(20);

   handleFast   = iMA(_Symbol, PERIOD_H1, InpEMAFast,   0, MODE_EMA, PRICE_CLOSE);
   handleSlow   = iMA(_Symbol, PERIOD_H1, InpEMASlow,   0, MODE_EMA, PRICE_CLOSE);
   handleFilter = iMA(_Symbol, InpHTF,    InpEMAFilter, 0, MODE_EMA, PRICE_CLOSE);
   handleADX    = iADX(_Symbol, PERIOD_H1, InpADXPeriod);

   if(handleFast == INVALID_HANDLE || handleSlow   == INVALID_HANDLE ||
      handleFilter == INVALID_HANDLE || handleADX  == INVALID_HANDLE)
   {
      Print("Handle error: ", GetLastError());
      return INIT_FAILED;
   }
   Print("TrendBot initialised.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(handleFast);
   IndicatorRelease(handleSlow);
   IndicatorRelease(handleFilter);
   IndicatorRelease(handleADX);
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime cb = iTime(_Symbol, PERIOD_H1, 0);
   if(cb == lastBar) return;
   lastBar = cb;

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return;

   double fast[3], slow[3], filter[2], adxMain[2];
   if(CopyBuffer(handleFast,   0, 1, 3, fast)   < 3) return;
   if(CopyBuffer(handleSlow,   0, 1, 3, slow)   < 3) return;
   if(CopyBuffer(handleFilter, 0, 1, 2, filter) < 2) return;
   if(CopyBuffer(handleADX,    0, 1, 2, adxMain)< 2) return;

   double price = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   bool   aboveFilter = price > filter[0];
   bool   adxOk       = adxMain[0] >= InpADXMin;

   ManagePositions();

   // Golden cross: fast crosses above slow
   bool goldenCross = fast[0] > slow[0] && fast[1] <= slow[1];
   // Death cross: fast crosses below slow
   bool deathCross  = fast[0] < slow[0] && fast[1] >= slow[1];

   if(CountPositions() > 0) return;

   if(goldenCross && aboveFilter && adxOk) OpenBuy();
   if(deathCross  && !aboveFilter && adxOk) OpenSell();
}

//+------------------------------------------------------------------+
void OpenBuy()
{
   double ask  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl   = ask - InpStopLoss   * _Point * 10;
   double tp   = ask + InpTakeProfit * _Point * 10;
   double lots = CalculateLots(InpStopLoss * _Point * 10);
   if(lots <= 0) return;
   Trade.Buy(lots, _Symbol, ask, sl, tp, InpComment);
}

//+------------------------------------------------------------------+
void OpenSell()
{
   double bid  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl   = bid + InpStopLoss   * _Point * 10;
   double tp   = bid - InpTakeProfit * _Point * 10;
   double lots = CalculateLots(InpStopLoss * _Point * 10);
   if(lots <= 0) return;
   Trade.Sell(lots, _Symbol, bid, sl, tp, InpComment);
}

//+------------------------------------------------------------------+
void ManagePositions()
{
   if(!InpUseTrailing) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionInfo.SelectByIndex(i)) continue;
      if(PositionInfo.Symbol() != _Symbol || PositionInfo.Magic() != InpMagicNumber) continue;
      double open  = PositionInfo.PriceOpen();
      double curSL = PositionInfo.StopLoss();
      double curTP = PositionInfo.TakeProfit();
      double ask   = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double bid   = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double start = InpTrailingStart * _Point * 10;
      double step  = InpTrailingStep  * _Point * 10;
      if(PositionInfo.PositionType() == POSITION_TYPE_BUY)
      {
         if(bid - open < start) continue;
         double newSL = bid - step;
         if(newSL > curSL + step) Trade.PositionModify(PositionInfo.Ticket(), newSL, curTP);
      }
      else
      {
         if(open - ask < start) continue;
         double newSL = ask + step;
         if(curSL == 0 || newSL < curSL - step) Trade.PositionModify(PositionInfo.Ticket(), newSL, curTP);
      }
   }
}

//+------------------------------------------------------------------+
double CalculateLots(double slDist)
{
   double balance  = AccountInfo.Balance();
   double risk     = balance * InpRiskPercent / 100.0;
   double tickVal  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickSize == 0 || tickVal == 0 || slDist == 0) return 0;
   double lots    = risk / (slDist / tickSize * tickVal);
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
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
