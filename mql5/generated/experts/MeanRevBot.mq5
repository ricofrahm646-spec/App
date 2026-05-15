//+------------------------------------------------------------------+
//| MeanRevBot.mq5                                                        |
//| JARVIS AI Trading System - Mean Reversion                        |
//+------------------------------------------------------------------+
#property copyright "JARVIS AI"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\AccountInfo.mqh>

input group "=== Trading Settings ==="
input double InpRiskPercent  = 1.5;
input int    InpMagicNumber  = 44001;
input string InpComment      = "JARVIS_MR";

input group "=== Bollinger Bands ==="
input int    InpBBPeriod     = 20;
input double InpBBDeviation  = 2.0;
input double InpBBDevEntry   = 2.0;
input double InpBBDevExit    = 0.5;

input group "=== RSI Confirmation ==="
input int    InpRSIPeriod    = 14;
input double InpRSIOversold  = 35.0;
input double InpRSIOverbought= 65.0;

input group "=== ATR Volatility Filter ==="
input int    InpATRPeriod    = 14;
input double InpATRMultMin   = 0.5;
input double InpATRMultMax   = 3.0;

input group "=== Risk Settings ==="
input int    InpStopLoss     = 40;
input int    InpTakeProfit   = 40;
input bool   InpUseMidExit   = true;

CTrade        Trade;
CPositionInfo PositionInfo;
CAccountInfo  AccountInfo;

int      handleBB, handleRSI, handleATR;
datetime lastBar = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   Trade.SetExpertMagicNumber(InpMagicNumber);
   Trade.SetDeviationInPoints(20);

   handleBB  = iBands(_Symbol, PERIOD_H1, InpBBPeriod, 0, InpBBDeviation, PRICE_CLOSE);
   handleRSI = iRSI  (_Symbol, PERIOD_H1, InpRSIPeriod, PRICE_CLOSE);
   handleATR = iATR  (_Symbol, PERIOD_H1, InpATRPeriod);

   if(handleBB == INVALID_HANDLE || handleRSI == INVALID_HANDLE || handleATR == INVALID_HANDLE)
   {
      Print("Handle error: ", GetLastError());
      return INIT_FAILED;
   }
   Print("MeanRevBot initialised.");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(handleBB);
   IndicatorRelease(handleRSI);
   IndicatorRelease(handleATR);
}

//+------------------------------------------------------------------+
void OnTick()
{
   datetime cb = iTime(_Symbol, PERIOD_H1, 0);
   if(cb == lastBar) return;
   lastBar = cb;

   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED)) return;

   double bbUpper[2], bbLower[2], bbMid[2], rsi[2], atr[2];
   if(CopyBuffer(handleBB,  1, 1, 2, bbUpper) < 2) return;
   if(CopyBuffer(handleBB,  2, 1, 2, bbLower) < 2) return;
   if(CopyBuffer(handleBB,  0, 1, 2, bbMid)   < 2) return;
   if(CopyBuffer(handleRSI, 0, 1, 2, rsi)     < 2) return;
   if(CopyBuffer(handleATR, 0, 1, 2, atr)     < 2) return;

   double close = iClose(_Symbol, PERIOD_H1, 1);
   double atrVal = atr[0];
   double bbWidth = bbUpper[0] - bbLower[0];

   if(!IsVolatilityOk(atrVal)) return;

   ManagePositions(bbMid[0]);

   if(CountPositions() > 0) return;

   bool buySignal  = close < bbLower[0] && rsi[0] < InpRSIOversold;
   bool sellSignal = close > bbUpper[0] && rsi[0] > InpRSIOverbought;

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
void ManagePositions(double midBand)
{
   if(!InpUseMidExit) return;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(!PositionInfo.SelectByIndex(i)) continue;
      if(PositionInfo.Symbol() != _Symbol || PositionInfo.Magic() != InpMagicNumber) continue;
      double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(PositionInfo.PositionType() == POSITION_TYPE_BUY && bid >= midBand)
         Trade.PositionClose(PositionInfo.Ticket());
      if(PositionInfo.PositionType() == POSITION_TYPE_SELL && ask <= midBand)
         Trade.PositionClose(PositionInfo.Ticket());
   }
}

//+------------------------------------------------------------------+
bool IsVolatilityOk(double atrVal)
{
   double bbUpper[1], bbLower[1];
   CopyBuffer(handleBB, 1, 1, 1, bbUpper);
   CopyBuffer(handleBB, 2, 1, 1, bbLower);
   double bandwidth = (bbUpper[0] - bbLower[0]) / atrVal;
   return bandwidth >= InpATRMultMin && bandwidth <= InpATRMultMax;
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
