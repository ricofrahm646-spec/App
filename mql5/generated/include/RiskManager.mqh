//+------------------------------------------------------------------+
//| RiskManager.mqh                                                   |
//| JARVIS AI - Risk management utilities                             |
//+------------------------------------------------------------------+
#ifndef JARVIS_RISK_MANAGER_MQH
#define JARVIS_RISK_MANAGER_MQH

#include <Trade\AccountInfo.mqh>

input group "=== Risk Manager ==="
input double RMInpMaxDailyLoss      = 5.0;   // Max daily loss %
input double RMInpMaxWeeklyLoss     = 10.0;  // Max weekly loss %
input double RMInpMaxDrawdown       = 15.0;  // Max total drawdown %
input int    RMInpMaxPositions      = 5;     // Max concurrent positions
input double RMInpMaxLotSize        = 5.0;   // Max lot size
input bool   RMInpPropFirmMode      = false; // Prop firm rules

CAccountInfo g_rmAccount;

double g_rmDailyStartBalance   = 0;
double g_rmWeeklyStartBalance  = 0;
datetime g_rmLastDayCheck      = 0;
datetime g_rmLastWeekCheck     = 0;

//+------------------------------------------------------------------+
void RMInit()
{
   g_rmDailyStartBalance  = g_rmAccount.Balance();
   g_rmWeeklyStartBalance = g_rmAccount.Balance();
   g_rmLastDayCheck       = TimeCurrent();
   g_rmLastWeekCheck      = TimeCurrent();
}

//+------------------------------------------------------------------+
void RMUpdatePeriods()
{
   MqlDateTime now;
   TimeToStruct(TimeCurrent(), now);

   MqlDateTime last;
   TimeToStruct(g_rmLastDayCheck, last);

   if(now.day != last.day)
   {
      g_rmDailyStartBalance = g_rmAccount.Balance();
      g_rmLastDayCheck      = TimeCurrent();
   }

   TimeToStruct(g_rmLastWeekCheck, last);
   if(now.day_of_week < last.day_of_week || (now.day - last.day) >= 7)
   {
      g_rmWeeklyStartBalance = g_rmAccount.Balance();
      g_rmLastWeekCheck      = TimeCurrent();
   }
}

//+------------------------------------------------------------------+
bool RMIsTradeAllowed()
{
   RMUpdatePeriods();

   double balance   = g_rmAccount.Balance();
   double equity    = g_rmAccount.Equity();

   // Daily loss check
   if(g_rmDailyStartBalance > 0)
   {
      double dailyLossPct = (g_rmDailyStartBalance - equity) / g_rmDailyStartBalance * 100.0;
      if(dailyLossPct >= RMInpMaxDailyLoss)
      {
         Print("RiskManager: Daily loss limit reached (", DoubleToString(dailyLossPct,2), "%)");
         return false;
      }
   }

   // Weekly loss check
   if(g_rmWeeklyStartBalance > 0)
   {
      double weeklyLossPct = (g_rmWeeklyStartBalance - equity) / g_rmWeeklyStartBalance * 100.0;
      if(weeklyLossPct >= RMInpMaxWeeklyLoss)
      {
         Print("RiskManager: Weekly loss limit reached (", DoubleToString(weeklyLossPct,2), "%)");
         return false;
      }
   }

   // Drawdown check
   double startBalance = MathMax(g_rmDailyStartBalance, balance);
   if(startBalance > 0)
   {
      double ddPct = (startBalance - equity) / startBalance * 100.0;
      if(ddPct >= RMInpMaxDrawdown)
      {
         Print("RiskManager: Max drawdown reached (", DoubleToString(ddPct,2), "%)");
         return false;
      }
   }

   // Position count check
   if(PositionsTotal() >= RMInpMaxPositions)
   {
      Print("RiskManager: Max positions reached (", PositionsTotal(), ")");
      return false;
   }

   return true;
}

//+------------------------------------------------------------------+
double RMCalculateLots(string symbol, double slDistance, double riskPct)
{
   double balance  = g_rmAccount.Balance();
   double risk     = balance * riskPct / 100.0;
   double tickVal  = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);

   if(tickSize == 0 || tickVal == 0 || slDistance == 0) return 0;

   double lots    = risk / (slDistance / tickSize * tickVal);
   double minLot  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot  = MathMin(SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX), RMInpMaxLotSize);
   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   lots = MathFloor(lots / lotStep) * lotStep;
   return MathMax(minLot, MathMin(maxLot, lots));
}

//+------------------------------------------------------------------+
double RMGetDailyPnL()
{
   return g_rmAccount.Equity() - g_rmDailyStartBalance;
}

//+------------------------------------------------------------------+
double RMGetCurrentDrawdown()
{
   double equity   = g_rmAccount.Equity();
   double balance  = g_rmAccount.Balance();
   double peak     = MathMax(balance, g_rmWeeklyStartBalance);
   if(peak <= 0) return 0;
   return (peak - equity) / peak * 100.0;
}

#endif // JARVIS_RISK_MANAGER_MQH
