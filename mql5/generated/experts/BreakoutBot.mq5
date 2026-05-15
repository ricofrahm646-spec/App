//+------------------------------------------------------------------+
//| BreakoutBot.mq5                                                        |
//| JARVIS AI Trading System - Breakout Strategy                     |
//+------------------------------------------------------------------+
#property copyright "JARVIS AI"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

input group "=== Trading Settings ==="
input double InpRiskPercent   = 1.5;
input int    InpMagicNumber   = 55001;
input string InpComment       = "JARVIS_BREAKOUT";

input group "=== Breakout Settings ==="
input int    InpRangeBars     = 20;      // Bars to calculate range
input double InpBreakoutBuffer= 3.0;    // Buffer in pips beyond range
input bool   InpLondonBreakout= true;   // Use London open breakout
input int    InpLondonOpenHour = 7;     // London open (GMT)
input int    InpRangeEndHour  = 9;      // Range calculation end (GMT)

input group "=== Volume Confirmation ==="
input bool   InpUseVolume     = true;
input double InpVolumeMinMult = 1.5;    // Minimum volume multiplier vs avg

input group "=== Risk Settings ==="
input int    InpStopLoss      = 40;
input int    InpTakeProfit    = 120;
input bool   InpUseTrailing   = true;
input int    InpTrailingStart = 40;
input int    InpTrailingStep  = 15;
input bool   InpBreakEven     = true;
input int    InpBEActivate    = 20;

CTrade        Trade;
CPositionInfo PositionInfo;
CAccountInfo  AccountInfo;

double   rangeHigh = 0, rangeLow = 0;
bool     rangeSet  = false;
bool     tradedToday = false;
datetime lastDay   = 0;
datetime lastBar   = 0;
int      handleATR;

//+------------------------------------------------------------------+
int OnInit()
{
   Trade.SetExpertMagicNumber(InpMagicNumber);
   Trade.SetDeviationInPoints(20);
   handleATR = iATR(_Symbol, PERIOD_H1, 14);
   if(handleATR == INVALID_HANDLE) { Print("ATR handle error"); return INIT_FAILED; }
   Print("BreakoutBot initialised.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) { IndicatorRelease(handleATR); }

//+------------------------------------------------------------------+
void OnTick()
{
   datetime cb = iTime(_Symbol, PERIOD_H1, 0);
   if(cb == lastBar) return;
   lastBar = cb;

   MqlDateTime t;
   TimeToStruct(TimeGMT(), t);

   // Reset daily
   datetime today = StringToTime(TimeToString(TimeGMT(), TIME_DATE));
   if(today != lastDay)
   {
      lastDay      = today;
      rangeSet     = false;
      tradedToday  = false;
      rangeHigh    = 0;
      rangeLow     = 0;
   }

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return;

   // Calculate range during accumulation period
   if(InpLondonBreakout && t.hour >= InpLondonOpenHour && t.hour < InpRangeEndHour && !rangeSet)
      CalculateRange();

   // Look for breakout after range established
   if(rangeSet && !tradedToday && t.hour >= InpRangeEndHour && t.hour < 18)
   {
      ManagePositions();
      if(CountPositions() > 0) return;
      CheckBreakout();
   }
}

//+------------------------------------------------------------------+
void CalculateRange()
{
   int bars = InpRangeBars;
   rangeHigh = iHigh(_Symbol, PERIOD_H1, 1);
   rangeLow  = iLow (_Symbol, PERIOD_H1, 1);
   for(int i = 2; i <= bars; i++)
   {
      double h = iHigh(_Symbol, PERIOD_H1, i);
      double l = iLow (_Symbol, PERIOD_H1, i);
      if(h > rangeHigh) rangeHigh = h;
      if(l < rangeLow)  rangeLow  = l;
   }
   rangeSet = true;
   Print("Range set: H=", rangeHigh, " L=", rangeLow);
}

//+------------------------------------------------------------------+
void CheckBreakout()
{
   if(rangeHigh == 0 || rangeLow == 0) return;
   double buffer = InpBreakoutBuffer * _Point * 10;
   double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   if(!InpUseVolume || IsVolumeOk())
   {
      if(ask > rangeHigh + buffer) { OpenBuy();  tradedToday = true; }
      if(bid < rangeLow  - buffer) { OpenSell(); tradedToday = true; }
   }
}

//+------------------------------------------------------------------+
bool IsVolumeOk()
{
   long vol = iVolume(_Symbol, PERIOD_H1, 1);
   long avgVol = 0;
   for(int i = 2; i <= 21; i++) avgVol += iVolume(_Symbol, PERIOD_H1, i);
   avgVol /= 20;
   return avgVol > 0 && (double)vol >= avgVol * InpVolumeMinMult;
}

//+------------------------------------------------------------------+
void OpenBuy()
{
   double ask  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double sl   = rangeLow  - InpStopLoss   * _Point * 10;
   double tp   = ask + InpTakeProfit * _Point * 10;
   double lots = CalculateLots(MathAbs(ask - sl));
   if(lots <= 0) return;
   Trade.Buy(lots, _Symbol, ask, sl, tp, InpComment);
}

//+------------------------------------------------------------------+
void OpenSell()
{
   double bid  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double sl   = rangeHigh + InpStopLoss   * _Point * 10;
   double tp   = bid - InpTakeProfit * _Point * 10;
   double lots = CalculateLots(MathAbs(sl - bid));
   if(lots <= 0) return;
   Trade.Sell(lots, _Symbol, bid, sl, tp, InpComment);
}

//+------------------------------------------------------------------+
void ManagePositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionInfo.SelectByIndex(i)) continue;
      if(PositionInfo.Symbol() != _Symbol || PositionInfo.Magic() != InpMagicNumber) continue;

      ulong  ticket = PositionInfo.Ticket();
      double open   = PositionInfo.PriceOpen();
      double curSL  = PositionInfo.StopLoss();
      double curTP  = PositionInfo.TakeProfit();
      double ask    = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double bid    = SymbolInfoDouble(_Symbol, SYMBOL_BID);

      // Break-even
      if(InpBreakEven)
      {
         double beActivate = InpBEActivate * _Point * 10;
         if(PositionInfo.PositionType() == POSITION_TYPE_BUY)
         {
            if(bid - open >= beActivate && curSL < open)
               Trade.PositionModify(ticket, open + _Point, curTP);
         }
         else
         {
            if(open - ask >= beActivate && (curSL > open || curSL == 0))
               Trade.PositionModify(ticket, open - _Point, curTP);
         }
      }

      // Trailing
      if(InpUseTrailing)
      {
         double start = InpTrailingStart * _Point * 10;
         double step  = InpTrailingStep  * _Point * 10;
         if(PositionInfo.PositionType() == POSITION_TYPE_BUY)
         {
            if(bid - open < start) continue;
            double newSL = bid - step;
            if(newSL > curSL + step) Trade.PositionModify(ticket, newSL, curTP);
         }
         else
         {
            if(open - ask < start) continue;
            double newSL = ask + step;
            if(curSL == 0 || newSL < curSL - step) Trade.PositionModify(ticket, newSL, curTP);
         }
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
