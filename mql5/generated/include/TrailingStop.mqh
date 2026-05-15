//+------------------------------------------------------------------+
//| TrailingStop.mqh                                                  |
//| JARVIS AI - Advanced trailing stop implementations               |
//+------------------------------------------------------------------+
#ifndef JARVIS_TRAILING_STOP_MQH
#define JARVIS_TRAILING_STOP_MQH

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

CTrade        g_tsTrade;
CPositionInfo g_tsPosition;

enum ENUM_TRAILING_TYPE
{
   TRAILING_FIXED     = 0,  // Fixed pip distance
   TRAILING_ATR       = 1,  // ATR-based
   TRAILING_PARABOLIC = 2,  // Parabolic SAR style
   TRAILING_CHANDELIER= 3   // Chandelier exit
};

//+------------------------------------------------------------------+
// Fixed-distance trailing stop
//+------------------------------------------------------------------+
void ApplyFixedTrailing(ulong ticket, int startPips, int stepPips, int magicNumber)
{
   if(!g_tsPosition.SelectByTicket(ticket)) return;
   if(g_tsPosition.Magic() != magicNumber) return;

   string symbol  = g_tsPosition.Symbol();
   double open    = g_tsPosition.PriceOpen();
   double curSL   = g_tsPosition.StopLoss();
   double curTP   = g_tsPosition.TakeProfit();
   double point   = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double start   = startPips * point * 10;
   double step    = stepPips  * point * 10;

   if(g_tsPosition.PositionType() == POSITION_TYPE_BUY)
   {
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(bid - open < start) return;
      double newSL = bid - step;
      if(newSL > curSL + point)
         g_tsTrade.PositionModify(ticket, newSL, curTP);
   }
   else
   {
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(open - ask < start) return;
      double newSL = ask + step;
      if(curSL == 0 || newSL < curSL - point)
         g_tsTrade.PositionModify(ticket, newSL, curTP);
   }
}

//+------------------------------------------------------------------+
// ATR-based trailing stop
//+------------------------------------------------------------------+
void ApplyATRTrailing(ulong ticket, int atrHandle, double atrMultiplier,
                      int startPips, int magicNumber)
{
   if(!g_tsPosition.SelectByTicket(ticket)) return;
   if(g_tsPosition.Magic() != magicNumber) return;

   string symbol = g_tsPosition.Symbol();
   double open   = g_tsPosition.PriceOpen();
   double curSL  = g_tsPosition.StopLoss();
   double curTP  = g_tsPosition.TakeProfit();
   double point  = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double start  = startPips * point * 10;

   double atrBuf[1];
   if(CopyBuffer(atrHandle, 0, 1, 1, atrBuf) < 1) return;
   double atrDist = atrBuf[0] * atrMultiplier;

   if(g_tsPosition.PositionType() == POSITION_TYPE_BUY)
   {
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(bid - open < start) return;
      double newSL = bid - atrDist;
      if(newSL > curSL + point)
         g_tsTrade.PositionModify(ticket, newSL, curTP);
   }
   else
   {
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(open - ask < start) return;
      double newSL = ask + atrDist;
      if(curSL == 0 || newSL < curSL - point)
         g_tsTrade.PositionModify(ticket, newSL, curTP);
   }
}

//+------------------------------------------------------------------+
// Chandelier exit trailing stop
//+------------------------------------------------------------------+
void ApplyChandelierTrailing(ulong ticket, int lookback, double atrMult,
                              int atrHandle, int magicNumber)
{
   if(!g_tsPosition.SelectByTicket(ticket)) return;
   if(g_tsPosition.Magic() != magicNumber) return;

   string symbol = g_tsPosition.Symbol();
   double curSL  = g_tsPosition.StopLoss();
   double curTP  = g_tsPosition.TakeProfit();
   double point  = SymbolInfoDouble(symbol, SYMBOL_POINT);

   double atrBuf[1];
   if(CopyBuffer(atrHandle, 0, 1, 1, atrBuf) < 1) return;
   double atrVal = atrBuf[0] * atrMult;

   if(g_tsPosition.PositionType() == POSITION_TYPE_BUY)
   {
      // Chandelier long: highest high over lookback - ATR * mult
      double highest = iHigh(symbol, PERIOD_CURRENT, iHighest(symbol, PERIOD_CURRENT, MODE_HIGH, lookback, 1));
      double newSL   = highest - atrVal;
      if(newSL > curSL + point)
         g_tsTrade.PositionModify(ticket, newSL, curTP);
   }
   else
   {
      double lowest = iLow(symbol, PERIOD_CURRENT, iLowest(symbol, PERIOD_CURRENT, MODE_LOW, lookback, 1));
      double newSL  = lowest + atrVal;
      if(curSL == 0 || newSL < curSL - point)
         g_tsTrade.PositionModify(ticket, newSL, curTP);
   }
}

//+------------------------------------------------------------------+
// Move to break-even
//+------------------------------------------------------------------+
bool MoveToBreakEven(ulong ticket, int activatePips, int lockInPips, int magicNumber)
{
   if(!g_tsPosition.SelectByTicket(ticket)) return false;
   if(g_tsPosition.Magic() != magicNumber) return false;

   string symbol   = g_tsPosition.Symbol();
   double open     = g_tsPosition.PriceOpen();
   double curSL    = g_tsPosition.StopLoss();
   double curTP    = g_tsPosition.TakeProfit();
   double point    = SymbolInfoDouble(symbol, SYMBOL_POINT);
   double activate = activatePips * point * 10;
   double lockIn   = lockInPips   * point * 10;

   if(g_tsPosition.PositionType() == POSITION_TYPE_BUY)
   {
      double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(bid - open >= activate && curSL < open + lockIn)
      {
         g_tsTrade.PositionModify(ticket, open + lockIn, curTP);
         return true;
      }
   }
   else
   {
      double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(open - ask >= activate && (curSL > open - lockIn || curSL == 0))
      {
         g_tsTrade.PositionModify(ticket, open - lockIn, curTP);
         return true;
      }
   }
   return false;
}

#endif // JARVIS_TRAILING_STOP_MQH
