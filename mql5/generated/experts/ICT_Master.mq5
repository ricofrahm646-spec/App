//+------------------------------------------------------------------+
//| ICT_Master.mq5                                                        |
//| JARVIS AI Trading System - ICT Strategy                          |
//+------------------------------------------------------------------+
#property copyright "JARVIS AI"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

input group "=== Trading Settings ==="
input double InpRiskPercent   = 1.0;
input int    InpMagicNumber   = 22001;
input string InpComment       = "JARVIS_ICT";

input group "=== ICT Settings ==="
input int    InpOBLookback    = 20;     // Order block lookback bars
input double InpFVGMinSize    = 5.0;    // Min FVG size in pips
input bool   InpUseKillzones  = true;   // Trade only in kill zones
input bool   InpUseMSS        = true;   // Market structure shift filter

input group "=== Risk Settings ==="
input int    InpStopLoss      = 30;
input int    InpTakeProfit    = 90;
input bool   InpUseTrailing   = true;
input int    InpTrailingStart = 30;
input int    InpTrailingStep  = 10;

CTrade        Trade;
CPositionInfo PositionInfo;
CAccountInfo  AccountInfo;

struct OrderBlock
{
   double high;
   double low;
   bool   isBullish;
   datetime time;
   bool   mitigated;
};

struct FVG
{
   double upper;
   double lower;
   bool   isBullish;
   datetime time;
   bool   filled;
};

OrderBlock bullishOBs[];
OrderBlock bearishOBs[];
FVG        fvgs[];
datetime   lastBar = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   Trade.SetExpertMagicNumber(InpMagicNumber);
   Trade.SetDeviationInPoints(20);
   Trade.SetTypeFilling(ORDER_FILLING_FOK);
   Print("ICT_Master (ICT) initialised on ", _Symbol);
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason) { }

//+------------------------------------------------------------------+
void OnTick()
{
   datetime currentBar = iTime(_Symbol, PERIOD_H1, 0);
   if(currentBar == lastBar) return;
   lastBar = currentBar;

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return;
   if(InpUseKillzones && !IsKillzone()) return;

   ScanOrderBlocks();
   ScanFVGs();
   ManagePositions();
   if(CountPositions() > 0) return;

   CheckEntrySignals();
}

//+------------------------------------------------------------------+
void ScanOrderBlocks()
{
   ArrayFree(bullishOBs);
   ArrayFree(bearishOBs);

   int bars = MathMin(InpOBLookback, iBars(_Symbol, PERIOD_H1));
   for(int i = bars; i >= 2; i--)
   {
      double o1 = iOpen (_Symbol, PERIOD_H1, i);
      double c1 = iClose(_Symbol, PERIOD_H1, i);
      double h1 = iHigh (_Symbol, PERIOD_H1, i);
      double l1 = iLow  (_Symbol, PERIOD_H1, i);
      double o0 = iOpen (_Symbol, PERIOD_H1, i-1);
      double c0 = iClose(_Symbol, PERIOD_H1, i-1);

      // Bullish OB: down-candle before significant up-move
      if(c1 < o1 && c0 > o0 && (c0 - o0) > (o1 - c1) * 1.5)
      {
         OrderBlock ob;
         ob.high      = h1;
         ob.low       = l1;
         ob.isBullish = true;
         ob.time      = iTime(_Symbol, PERIOD_H1, i);
         ob.mitigated = false;
         int sz = ArraySize(bullishOBs);
         ArrayResize(bullishOBs, sz + 1);
         bullishOBs[sz] = ob;
      }

      // Bearish OB: up-candle before significant down-move
      if(c1 > o1 && c0 < o0 && (o0 - c0) > (c1 - o1) * 1.5)
      {
         OrderBlock ob;
         ob.high      = h1;
         ob.low       = l1;
         ob.isBullish = false;
         ob.time      = iTime(_Symbol, PERIOD_H1, i);
         ob.mitigated = false;
         int sz = ArraySize(bearishOBs);
         ArrayResize(bearishOBs, sz + 1);
         bearishOBs[sz] = ob;
      }
   }
}

//+------------------------------------------------------------------+
void ScanFVGs()
{
   ArrayFree(fvgs);
   int bars = MathMin(InpOBLookback, iBars(_Symbol, PERIOD_H1));
   double minSize = InpFVGMinSize * _Point * 10;

   for(int i = bars; i >= 1; i--)
   {
      double h_prev = iHigh(_Symbol, PERIOD_H1, i+1);
      double l_prev = iLow (_Symbol, PERIOD_H1, i+1);
      double h_curr = iHigh(_Symbol, PERIOD_H1, i);
      double l_curr = iLow (_Symbol, PERIOD_H1, i);
      double h_next = iHigh(_Symbol, PERIOD_H1, i-1);
      double l_next = iLow (_Symbol, PERIOD_H1, i-1);

      // Bullish FVG: gap between candle[i+1] high and candle[i-1] low
      if(l_next > h_prev && (l_next - h_prev) >= minSize)
      {
         FVG fvg;
         fvg.upper     = l_next;
         fvg.lower     = h_prev;
         fvg.isBullish = true;
         fvg.time      = iTime(_Symbol, PERIOD_H1, i);
         fvg.filled    = false;
         int sz = ArraySize(fvgs);
         ArrayResize(fvgs, sz + 1);
         fvgs[sz] = fvg;
      }

      // Bearish FVG
      if(h_next < l_prev && (l_prev - h_next) >= minSize)
      {
         FVG fvg;
         fvg.upper     = l_prev;
         fvg.lower     = h_next;
         fvg.isBullish = false;
         fvg.time      = iTime(_Symbol, PERIOD_H1, i);
         fvg.filled    = false;
         int sz = ArraySize(fvgs);
         ArrayResize(fvgs, sz + 1);
         fvgs[sz] = fvg;
      }
   }
}

//+------------------------------------------------------------------+
void CheckEntrySignals()
{
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

   // Check bullish OB entries (price returns to OB)
   for(int i = 0; i < ArraySize(bullishOBs); i++)
   {
      if(bullishOBs[i].mitigated) continue;
      if(ask >= bullishOBs[i].low && ask <= bullishOBs[i].high)
      {
         if(!InpUseMSS || IsBullishMSS())
         {
            OpenBuy(bullishOBs[i].low - InpStopLoss * _Point * 10);
            bullishOBs[i].mitigated = true;
            return;
         }
      }
   }

   // Check bearish OB entries
   for(int i = 0; i < ArraySize(bearishOBs); i++)
   {
      if(bearishOBs[i].mitigated) continue;
      if(bid >= bearishOBs[i].low && bid <= bearishOBs[i].high)
      {
         if(!InpUseMSS || IsBearishMSS())
         {
            OpenSell(bearishOBs[i].high + InpStopLoss * _Point * 10);
            bearishOBs[i].mitigated = true;
            return;
         }
      }
   }
}

//+------------------------------------------------------------------+
bool IsBullishMSS()
{
   // Higher high + higher low structure on H1
   double hh1 = iHigh(_Symbol, PERIOD_H1, 2);
   double hh2 = iHigh(_Symbol, PERIOD_H1, 4);
   double hl1 = iLow (_Symbol, PERIOD_H1, 2);
   double hl2 = iLow (_Symbol, PERIOD_H1, 4);
   return hh1 > hh2 && hl1 > hl2;
}

//+------------------------------------------------------------------+
bool IsBearishMSS()
{
   double lh1 = iHigh(_Symbol, PERIOD_H1, 2);
   double lh2 = iHigh(_Symbol, PERIOD_H1, 4);
   double ll1 = iLow (_Symbol, PERIOD_H1, 2);
   double ll2 = iLow (_Symbol, PERIOD_H1, 4);
   return lh1 < lh2 && ll1 < ll2;
}

//+------------------------------------------------------------------+
bool IsKillzone()
{
   MqlDateTime t;
   TimeToStruct(TimeGMT(), t);
   int hour = t.hour;
   // London open (7-9), New York open (12-14), London close (15-17)
   return (hour >= 7 && hour < 9) || (hour >= 12 && hour < 14) || (hour >= 15 && hour < 17);
}

//+------------------------------------------------------------------+
void OpenBuy(double sl)
{
   double ask  = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double tp   = ask + InpTakeProfit * _Point * 10;
   double lots = CalculateLots(MathAbs(ask - sl));
   if(lots <= 0) return;
   if(!Trade.Buy(lots, _Symbol, ask, sl, tp, InpComment))
      Print("ICT Buy error: ", Trade.ResultRetcodeDescription());
}

//+------------------------------------------------------------------+
void OpenSell(double sl)
{
   double bid  = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double tp   = bid - InpTakeProfit * _Point * 10;
   double lots = CalculateLots(MathAbs(sl - bid));
   if(lots <= 0) return;
   if(!Trade.Sell(lots, _Symbol, bid, sl, tp, InpComment))
      Print("ICT Sell error: ", Trade.ResultRetcodeDescription());
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
