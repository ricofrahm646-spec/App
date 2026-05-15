"""
Base MQL5 Expert Advisor template with placeholders for JARVIS code generation.
"""

EA_BASE_TEMPLATE = """//+------------------------------------------------------------------+
//| {ea_name}.mq5                                                     |
//| JARVIS AI Trading System                                          |
//| Generated Expert Advisor - {strategy_type}                        |
//+------------------------------------------------------------------+
#property copyright "JARVIS AI Trading System"
#property link      "https://jarvis-trading.ai"
#property version   "1.00"
#property strict

#include <Trade\\Trade.mqh>
#include <Trade\\PositionInfo.mqh>
#include <Trade\\SymbolInfo.mqh>
#include <Trade\\AccountInfo.mqh>

//--- Input parameters
input group "=== Trade Settings ==="
input double   InpLotSize        = {lot_size};       // Lot Size (0 = auto)
input double   InpRiskPercent    = {risk_percent};   // Risk Percent per Trade
input int      InpStopLoss       = {stop_loss};      // Stop Loss in Points
input int      InpTakeProfit     = {take_profit};    // Take Profit in Points
input int      InpMagicNumber    = {magic_number};   // Magic Number
input string   InpTradeComment   = "{trade_comment}"; // Trade Comment

input group "=== Risk Management ==="
input int      InpMaxSpread      = {max_spread};     // Max Spread in Points
input int      InpMaxSlippage    = {max_slippage};   // Max Slippage in Points
input int      InpMaxDailyTrades = {max_daily_trades}; // Max Trades per Day (0=unlimited)
input double   InpMaxDailyLoss   = {max_daily_loss}; // Max Daily Loss % (0=unlimited)
input double   InpMaxDrawdown    = {max_drawdown};   // Max Drawdown % (0=unlimited)

input group "=== Trade Management ==="
input bool     InpUseTrailingStop  = {use_trailing};   // Use Trailing Stop
input int      InpTrailingStart    = {trailing_start};  // Trailing Start in Points
input int      InpTrailingStep     = {trailing_step};   // Trailing Step in Points
input bool     InpUseBreakeven     = {use_breakeven};   // Use Breakeven
input int      InpBreakevenStart   = {breakeven_start}; // Breakeven Trigger in Points
input int      InpBreakevenOffset  = {breakeven_offset}; // Breakeven Offset in Points

input group "=== Time Filter ==="
input bool     InpUseTimeFilter   = {use_time_filter}; // Use Time Filter
input int      InpStartHour       = {start_hour};      // Start Hour (Server Time)
input int      InpEndHour         = {end_hour};         // End Hour (Server Time)
input bool     InpTradeMonday     = true;  // Trade Monday
input bool     InpTradeTuesday    = true;  // Trade Tuesday
input bool     InpTradeWednesday  = true;  // Trade Wednesday
input bool     InpTradeThursday   = true;  // Trade Thursday
input bool     InpTradeFriday     = true;  // Trade Friday

{custom_inputs}

//--- Global variables
CTrade         trade;
CPositionInfo  posInfo;
CSymbolInfo    symInfo;
CAccountInfo   accInfo;

int            dailyTradeCount;
double         dailyStartBalance;
datetime       lastTradeDay;
double         maxEquity;

{custom_globals}

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{{
   //--- Validate inputs
   if(InpStopLoss < 0 || InpTakeProfit < 0)
   {{
      Print("Invalid SL/TP values");
      return(INIT_PARAMETERS_INCORRECT);
   }}

   //--- Setup trade object
   trade.SetExpertMagicNumber(InpMagicNumber);
   trade.SetDeviationInPoints(InpMaxSlippage);
   trade.SetTypeFilling(ORDER_FILLING_FOK);
   trade.SetMarginMode();

   //--- Initialize symbol info
   if(!symInfo.Name(_Symbol))
   {{
      Print("Failed to initialize symbol info");
      return(INIT_FAILED);
   }}

   //--- Initialize daily tracking
   dailyTradeCount  = 0;
   dailyStartBalance = accInfo.Balance();
   lastTradeDay     = 0;
   maxEquity        = accInfo.Equity();

{custom_init}

   Print("{ea_name} initialized on ", _Symbol, " ", EnumToString(_Period));
   return(INIT_SUCCEEDED);
}}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                    |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{{
{custom_deinit}
   Print("{ea_name} removed. Reason: ", reason);
}}

//+------------------------------------------------------------------+
//| Expert tick function                                                |
//+------------------------------------------------------------------+
void OnTick()
{{
   //--- Refresh symbol info
   if(!symInfo.RefreshRates())
      return;

   //--- Check new day for daily limits
   CheckNewDay();

   //--- Check risk limits
   if(!CheckRiskLimits())
      return;

   //--- Check spread filter
   if(InpMaxSpread > 0 && symInfo.Spread() > InpMaxSpread)
      return;

   //--- Check time filter
   if(InpUseTimeFilter && !IsWithinTradingHours())
      return;

   //--- Check day filter
   if(!IsTradingDay())
      return;

   //--- Manage existing positions (trailing stop, breakeven)
   ManagePositions();

{custom_on_tick}
}}

//+------------------------------------------------------------------+
//| Timer function                                                     |
//+------------------------------------------------------------------+
void OnTimer()
{{
{custom_on_timer}
}}

//+------------------------------------------------------------------+
//| Trade transaction handler                                          |
//+------------------------------------------------------------------+
void OnTradeTransaction(const MqlTradeTransaction& trans,
                        const MqlTradeRequest& request,
                        const MqlTradeResult& result)
{{
   if(trans.type == TRADE_TRANSACTION_DEAL_ADD)
   {{
      if(trans.deal_type == DEAL_TYPE_BUY || trans.deal_type == DEAL_TYPE_SELL)
         dailyTradeCount++;
   }}
}}

//+------------------------------------------------------------------+
//| Check if new trading day started                                   |
//+------------------------------------------------------------------+
void CheckNewDay()
{{
   datetime today = StringToTime(TimeToString(TimeCurrent(), TIME_DATE));
   if(today != lastTradeDay)
   {{
      lastTradeDay      = today;
      dailyTradeCount   = 0;
      dailyStartBalance = accInfo.Balance();
   }}
}}

//+------------------------------------------------------------------+
//| Check risk management limits                                       |
//+------------------------------------------------------------------+
bool CheckRiskLimits()
{{
   //--- Daily trade limit
   if(InpMaxDailyTrades > 0 && dailyTradeCount >= InpMaxDailyTrades)
      return false;

   //--- Daily loss limit
   if(InpMaxDailyLoss > 0.0)
   {{
      double dailyPnL = accInfo.Balance() - dailyStartBalance;
      double maxLoss  = dailyStartBalance * InpMaxDailyLoss / 100.0;
      if(dailyPnL < -maxLoss)
         return false;
   }}

   //--- Max drawdown limit
   if(InpMaxDrawdown > 0.0)
   {{
      double equity = accInfo.Equity();
      if(equity > maxEquity)
         maxEquity = equity;
      double drawdown = (maxEquity - equity) / maxEquity * 100.0;
      if(drawdown > InpMaxDrawdown)
         return false;
   }}

   return true;
}}

//+------------------------------------------------------------------+
//| Calculate lot size based on risk                                   |
//+------------------------------------------------------------------+
double CalculateLotSize(double slPoints)
{{
   if(InpLotSize > 0)
      return NormalizeLots(InpLotSize);

   if(slPoints <= 0)
      slPoints = InpStopLoss;
   if(slPoints <= 0)
      return NormalizeLots(symInfo.LotsMin());

   double tickValue  = symInfo.TickValue();
   double tickSize   = symInfo.TickSize();
   double pointValue = tickValue / tickSize * _Point;
   double riskMoney  = accInfo.Balance() * InpRiskPercent / 100.0;
   double lots       = riskMoney / (slPoints * pointValue);

   return NormalizeLots(lots);
}}

//+------------------------------------------------------------------+
//| Normalize lot size to broker constraints                           |
//+------------------------------------------------------------------+
double NormalizeLots(double lots)
{{
   double minLot  = symInfo.LotsMin();
   double maxLot  = symInfo.LotsMax();
   double lotStep = symInfo.LotsStep();

   lots = MathMax(minLot, lots);
   lots = MathMin(maxLot, lots);
   lots = MathRound(lots / lotStep) * lotStep;

   return NormalizeDouble(lots, 2);
}}

//+------------------------------------------------------------------+
//| Check if current time is within trading hours                      |
//+------------------------------------------------------------------+
bool IsWithinTradingHours()
{{
   MqlDateTime dt;
   TimeCurrent(dt);
   int hour = dt.hour;

   if(InpStartHour < InpEndHour)
      return (hour >= InpStartHour && hour < InpEndHour);
   else
      return (hour >= InpStartHour || hour < InpEndHour);
}}

//+------------------------------------------------------------------+
//| Check if today is a trading day                                    |
//+------------------------------------------------------------------+
bool IsTradingDay()
{{
   MqlDateTime dt;
   TimeCurrent(dt);

   switch(dt.day_of_week)
   {{
      case 1: return InpTradeMonday;
      case 2: return InpTradeTuesday;
      case 3: return InpTradeWednesday;
      case 4: return InpTradeThursday;
      case 5: return InpTradeFriday;
      default: return false;
   }}
}}

//+------------------------------------------------------------------+
//| Open a buy position                                                |
//+------------------------------------------------------------------+
bool OpenBuy(double slPoints, double tpPoints, string comment="")
{{
   double ask = symInfo.Ask();
   double sl  = (slPoints > 0) ? ask - slPoints * _Point : 0;
   double tp  = (tpPoints > 0) ? ask + tpPoints * _Point : 0;
   double lots = CalculateLotSize(slPoints);

   sl = NormalizeDouble(sl, _Digits);
   tp = NormalizeDouble(tp, _Digits);

   if(comment == "")
      comment = InpTradeComment;

   if(!trade.Buy(lots, _Symbol, ask, sl, tp, comment))
   {{
      Print("Buy failed: ", trade.ResultRetcodeDescription());
      return false;
   }}
   return true;
}}

//+------------------------------------------------------------------+
//| Open a sell position                                               |
//+------------------------------------------------------------------+
bool OpenSell(double slPoints, double tpPoints, string comment="")
{{
   double bid = symInfo.Bid();
   double sl  = (slPoints > 0) ? bid + slPoints * _Point : 0;
   double tp  = (tpPoints > 0) ? bid - tpPoints * _Point : 0;
   double lots = CalculateLotSize(slPoints);

   sl = NormalizeDouble(sl, _Digits);
   tp = NormalizeDouble(tp, _Digits);

   if(comment == "")
      comment = InpTradeComment;

   if(!trade.Sell(lots, _Symbol, bid, sl, tp, comment))
   {{
      Print("Sell failed: ", trade.ResultRetcodeDescription());
      return false;
   }}
   return true;
}}

//+------------------------------------------------------------------+
//| Close all positions for this EA                                    |
//+------------------------------------------------------------------+
void CloseAllPositions()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      if(posInfo.SelectByIndex(i))
      {{
         if(posInfo.Symbol() == _Symbol && posInfo.Magic() == InpMagicNumber)
            trade.PositionClose(posInfo.Ticket());
      }}
   }}
}}

//+------------------------------------------------------------------+
//| Count open positions for this EA                                   |
//+------------------------------------------------------------------+
int CountPositions(ENUM_POSITION_TYPE posType = -1)
{{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      if(posInfo.SelectByIndex(i))
      {{
         if(posInfo.Symbol() == _Symbol && posInfo.Magic() == InpMagicNumber)
         {{
            if(posType == -1 || posInfo.PositionType() == posType)
               count++;
         }}
      }}
   }}
   return count;
}}

//+------------------------------------------------------------------+
//| Manage open positions: trailing stop, breakeven                    |
//+------------------------------------------------------------------+
void ManagePositions()
{{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {{
      if(!posInfo.SelectByIndex(i))
         continue;
      if(posInfo.Symbol() != _Symbol || posInfo.Magic() != InpMagicNumber)
         continue;

      double openPrice = posInfo.PriceOpen();
      double currentSL = posInfo.StopLoss();
      double currentTP = posInfo.TakeProfit();

      if(posInfo.PositionType() == POSITION_TYPE_BUY)
      {{
         double bid = symInfo.Bid();

         //--- Breakeven
         if(InpUseBreakeven && InpBreakevenStart > 0)
         {{
            double beLevel = openPrice + InpBreakevenStart * _Point;
            if(bid >= beLevel && currentSL < openPrice)
            {{
               double newSL = openPrice + InpBreakevenOffset * _Point;
               newSL = NormalizeDouble(newSL, _Digits);
               trade.PositionModify(posInfo.Ticket(), newSL, currentTP);
               continue;
            }}
         }}

         //--- Trailing stop
         if(InpUseTrailingStop && InpTrailingStart > 0)
         {{
            double trailLevel = openPrice + InpTrailingStart * _Point;
            if(bid >= trailLevel)
            {{
               double newSL = bid - InpTrailingStep * _Point;
               newSL = NormalizeDouble(newSL, _Digits);
               if(newSL > currentSL)
                  trade.PositionModify(posInfo.Ticket(), newSL, currentTP);
            }}
         }}
      }}
      else if(posInfo.PositionType() == POSITION_TYPE_SELL)
      {{
         double ask = symInfo.Ask();

         //--- Breakeven
         if(InpUseBreakeven && InpBreakevenStart > 0)
         {{
            double beLevel = openPrice - InpBreakevenStart * _Point;
            if(ask <= beLevel && (currentSL > openPrice || currentSL == 0))
            {{
               double newSL = openPrice - InpBreakevenOffset * _Point;
               newSL = NormalizeDouble(newSL, _Digits);
               trade.PositionModify(posInfo.Ticket(), newSL, currentTP);
               continue;
            }}
         }}

         //--- Trailing stop
         if(InpUseTrailingStop && InpTrailingStart > 0)
         {{
            double trailLevel = openPrice - InpTrailingStart * _Point;
            if(ask <= trailLevel)
            {{
               double newSL = ask + InpTrailingStep * _Point;
               newSL = NormalizeDouble(newSL, _Digits);
               if(newSL < currentSL || currentSL == 0)
                  trade.PositionModify(posInfo.Ticket(), newSL, currentTP);
            }}
         }}
      }}
   }}
}}

{custom_functions}
//+------------------------------------------------------------------+
"""

EA_SCALPING_LOGIC = """
   //--- Strategy: Scalping (EMA Crossover + RSI + Volume)
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == lastBarTime)
      return;
   lastBarTime = currentBarTime;

   if(CountPositions() > 0)
      return;

   double emaFastArr[], emaSlowArr[], rsiArr[];
   ArraySetAsSeries(emaFastArr, true);
   ArraySetAsSeries(emaSlowArr, true);
   ArraySetAsSeries(rsiArr, true);

   CopyBuffer(hEmaFast, 0, 0, 3, emaFastArr);
   CopyBuffer(hEmaSlow, 0, 0, 3, emaSlowArr);
   CopyBuffer(hRsi, 0, 0, 3, rsiArr);

   long volume[];
   ArraySetAsSeries(volume, true);
   CopyTickVolume(_Symbol, _Period, 0, 20, volume);

   long avgVolume = 0;
   for(int i = 1; i < 20; i++)
      avgVolume += volume[i];
   avgVolume /= 19;

   bool highVolume = volume[1] > (long)(avgVolume * InpVolMultiplier);

   //--- Buy Signal: Fast EMA crosses above Slow EMA, RSI not overbought, high volume
   if(emaFastArr[1] > emaSlowArr[1] && emaFastArr[2] <= emaSlowArr[2])
   {{
      if(rsiArr[1] > InpRsiOversold && rsiArr[1] < InpRsiOverbought && highVolume)
         OpenBuy(InpStopLoss, InpTakeProfit, "Scalp Buy");
   }}

   //--- Sell Signal: Fast EMA crosses below Slow EMA, RSI not oversold, high volume
   if(emaFastArr[1] < emaSlowArr[1] && emaFastArr[2] >= emaSlowArr[2])
   {{
      if(rsiArr[1] < InpRsiOverbought && rsiArr[1] > InpRsiOversold && highVolume)
         OpenSell(InpStopLoss, InpTakeProfit, "Scalp Sell");
   }}
"""

EA_TREND_FOLLOWING_LOGIC = """
   //--- Strategy: Trend Following (ADX + MA + ATR)
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == lastBarTime)
      return;
   lastBarTime = currentBarTime;

   if(CountPositions() > 0)
      return;

   double adxArr[], plusDiArr[], minusDiArr[], maArr[], atrArr[];
   ArraySetAsSeries(adxArr, true);
   ArraySetAsSeries(plusDiArr, true);
   ArraySetAsSeries(minusDiArr, true);
   ArraySetAsSeries(maArr, true);
   ArraySetAsSeries(atrArr, true);

   CopyBuffer(hAdx, 0, 0, 3, adxArr);
   CopyBuffer(hAdx, 1, 0, 3, plusDiArr);
   CopyBuffer(hAdx, 2, 0, 3, minusDiArr);
   CopyBuffer(hMa, 0, 0, 3, maArr);
   CopyBuffer(hAtr, 0, 0, 3, atrArr);

   double close1 = iClose(_Symbol, _Period, 1);
   bool strongTrend = adxArr[1] > InpAdxThreshold;

   double slPoints = atrArr[1] * InpAtrMultSl / _Point;
   double tpPoints = atrArr[1] * InpAtrMultTp / _Point;

   //--- Buy: ADX strong, +DI > -DI, price above MA
   if(strongTrend && plusDiArr[1] > minusDiArr[1] && close1 > maArr[1])
   {{
      if(plusDiArr[2] <= minusDiArr[2])
         OpenBuy(slPoints, tpPoints, "Trend Buy");
   }}

   //--- Sell: ADX strong, -DI > +DI, price below MA
   if(strongTrend && minusDiArr[1] > plusDiArr[1] && close1 < maArr[1])
   {{
      if(minusDiArr[2] <= plusDiArr[2])
         OpenSell(slPoints, tpPoints, "Trend Sell");
   }}
"""

EA_BREAKOUT_LOGIC = """
   //--- Strategy: Breakout (Range Detection + Volume Breakout)
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == lastBarTime)
      return;
   lastBarTime = currentBarTime;

   if(CountPositions() > 0)
      return;

   //--- Calculate range (highest high, lowest low over lookback)
   double highArr[], lowArr[];
   ArraySetAsSeries(highArr, true);
   ArraySetAsSeries(lowArr, true);
   CopyHigh(_Symbol, _Period, 1, InpRangePeriod, highArr);
   CopyLow(_Symbol, _Period, 1, InpRangePeriod, lowArr);

   double rangeHigh = highArr[ArrayMaximum(highArr)];
   double rangeLow  = lowArr[ArrayMinimum(lowArr)];
   double rangeSize = rangeHigh - rangeLow;

   double atrArr[];
   ArraySetAsSeries(atrArr, true);
   CopyBuffer(hAtr, 0, 0, 3, atrArr);

   //--- Volume confirmation
   long volume[];
   ArraySetAsSeries(volume, true);
   CopyTickVolume(_Symbol, _Period, 0, 20, volume);
   long avgVolume = 0;
   for(int i = 1; i < 20; i++)
      avgVolume += volume[i];
   avgVolume /= 19;
   bool highVolume = volume[0] > (long)(avgVolume * InpVolMultiplier);

   double close0 = iClose(_Symbol, _Period, 0);
   double slPoints = atrArr[1] * InpAtrMultSl / _Point;
   double tpPoints = rangeSize / _Point * InpAtrMultTp;

   //--- Bullish breakout
   if(close0 > rangeHigh && highVolume)
      OpenBuy(slPoints, tpPoints, "Breakout Buy");

   //--- Bearish breakout
   if(close0 < rangeLow && highVolume)
      OpenSell(slPoints, tpPoints, "Breakout Sell");
"""

EA_MEAN_REVERSION_LOGIC = """
   //--- Strategy: Mean Reversion (Bollinger Bands + RSI)
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == lastBarTime)
      return;
   lastBarTime = currentBarTime;

   if(CountPositions() > 0)
      return;

   double bbUpperArr[], bbMiddleArr[], bbLowerArr[], rsiArr[];
   ArraySetAsSeries(bbUpperArr, true);
   ArraySetAsSeries(bbMiddleArr, true);
   ArraySetAsSeries(bbLowerArr, true);
   ArraySetAsSeries(rsiArr, true);

   CopyBuffer(hBB, 0, 0, 3, bbMiddleArr);
   CopyBuffer(hBB, 1, 0, 3, bbUpperArr);
   CopyBuffer(hBB, 2, 0, 3, bbLowerArr);
   CopyBuffer(hRsi, 0, 0, 3, rsiArr);

   double close1 = iClose(_Symbol, _Period, 1);
   double close2 = iClose(_Symbol, _Period, 2);
   double tpPoints = (bbMiddleArr[1] - bbLowerArr[1]) / _Point;

   //--- Buy: Price touches lower band + RSI oversold
   if(close2 <= bbLowerArr[2] && close1 > bbLowerArr[1] && rsiArr[1] < InpRsiOversold)
      OpenBuy(InpStopLoss, tpPoints, "MeanRev Buy");

   //--- Sell: Price touches upper band + RSI overbought
   if(close2 >= bbUpperArr[2] && close1 < bbUpperArr[1] && rsiArr[1] > InpRsiOverbought)
      OpenSell(InpStopLoss, tpPoints, "MeanRev Sell");
"""

EA_ICT_SMART_MONEY_LOGIC = """
   //--- Strategy: ICT/Smart Money (Order Blocks + Liquidity Sweeps + FVG)
   static datetime lastBarTime = 0;
   datetime currentBarTime = iTime(_Symbol, _Period, 0);
   if(currentBarTime == lastBarTime)
      return;
   lastBarTime = currentBarTime;

   if(CountPositions() > 0)
      return;

   //--- Get price data
   double open[], high[], low[], close[];
   ArraySetAsSeries(open, true);
   ArraySetAsSeries(high, true);
   ArraySetAsSeries(low, true);
   ArraySetAsSeries(close, true);
   CopyOpen(_Symbol, _Period, 0, InpLookback + 5, open);
   CopyHigh(_Symbol, _Period, 0, InpLookback + 5, high);
   CopyLow(_Symbol, _Period, 0, InpLookback + 5, low);
   CopyClose(_Symbol, _Period, 0, InpLookback + 5, close);

   //--- Detect Order Blocks (last bearish candle before bullish move, and vice versa)
   double bullOB_high = 0, bullOB_low = 0;
   double bearOB_high = 0, bearOB_low = 0;

   for(int i = 2; i < InpLookback; i++)
   {{
      //--- Bullish Order Block: bearish candle followed by strong bullish move
      if(close[i] < open[i] && close[i-1] > open[i-1])
      {{
         if((close[i-1] - open[i-1]) > (open[i] - close[i]) * InpOBStrength)
         {{
            bullOB_high = high[i];
            bullOB_low  = low[i];
            break;
         }}
      }}
   }}

   for(int i = 2; i < InpLookback; i++)
   {{
      //--- Bearish Order Block: bullish candle followed by strong bearish move
      if(close[i] > open[i] && close[i-1] < open[i-1])
      {{
         if((open[i-1] - close[i-1]) > (close[i] - open[i]) * InpOBStrength)
         {{
            bearOB_high = high[i];
            bearOB_low  = low[i];
            break;
         }}
      }}
   }}

   //--- Detect Fair Value Gaps (FVG)
   bool bullFVG = false, bearFVG = false;
   if(low[1] > high[3])
      bullFVG = true;
   if(high[1] < low[3])
      bearFVG = true;

   //--- Detect Liquidity Sweep (price swept recent high/low then reversed)
   double recentHigh = high[ArrayMaximum(high, 2, InpLookback)];
   double recentLow  = low[ArrayMinimum(low, 2, InpLookback)];
   bool bullSweep = (low[2] < recentLow && close[1] > open[1]);
   bool bearSweep = (high[2] > recentHigh && close[1] < open[1]);

   //--- Determine session (London/NY killzone)
   MqlDateTime dt;
   TimeCurrent(dt);
   bool inKillzone = (dt.hour >= 7 && dt.hour <= 10) || (dt.hour >= 13 && dt.hour <= 16);

   double atrArr[];
   ArraySetAsSeries(atrArr, true);
   CopyBuffer(hAtr, 0, 0, 3, atrArr);
   double slPoints = atrArr[1] * InpAtrMultSl / _Point;
   double tpPoints = atrArr[1] * InpAtrMultTp / _Point;

   //--- Buy: Price in bullish OB zone + (FVG or liquidity sweep) + killzone
   if(bullOB_low > 0 && close[1] >= bullOB_low && close[1] <= bullOB_high)
   {{
      if((bullFVG || bullSweep) && inKillzone)
         OpenBuy(slPoints, tpPoints, "ICT Buy");
   }}

   //--- Sell: Price in bearish OB zone + (FVG or liquidity sweep) + killzone
   if(bearOB_low > 0 && close[1] >= bearOB_low && close[1] <= bearOB_high)
   {{
      if((bearFVG || bearSweep) && inKillzone)
         OpenSell(slPoints, tpPoints, "ICT Sell");
   }}
"""
