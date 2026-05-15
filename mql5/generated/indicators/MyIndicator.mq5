//+------------------------------------------------------------------+
//| MyIndicator.mq5                                                        |
//| JARVIS AI Trading System - Custom Indicator                      |
//+------------------------------------------------------------------+
#property copyright   "JARVIS AI"
#property version     "1.00"
#property indicator_chart_window
#property indicator_buffers 1
#property indicator_plots   1
#property indicator_color1 clrDodgerBlue
#property indicator_style1 STYLE_SOLID
#property indicator_width1 2

input int    InpPeriod     = 21;
input ENUM_APPLIED_PRICE InpPrice = PRICE_CLOSE;

double MainBuffer[];
int handleMA;

//+------------------------------------------------------------------+
int OnInit()
{
   SetIndexBuffer(0, MainBuffer, INDICATOR_DATA);
   PlotIndexSetString(0, PLOT_LABEL, "MainBuffer");
   handleMA = iMA(_Symbol, PERIOD_CURRENT, InpPeriod, 0, MODE_EMA, InpPrice);
   if(handleMA == INVALID_HANDLE) { Print("Handle error"); return INIT_FAILED; }
   IndicatorSetString(INDICATOR_SHORTNAME, "MyIndicator(" + IntegerToString(InpPeriod) + ")");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(handleMA);
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double   &open[],
                const double   &high[],
                const double   &low[],
                const double   &close[],
                const long     &tick_volume[],
                const long     &volume[],
                const int      &spread[])
{
   if(rates_total < InpPeriod) return 0;

   int start = (prev_calculated > 0) ? prev_calculated - 1 : InpPeriod - 1;
   double maBuffer[];
   ArraySetAsSeries(maBuffer, false);

   if(CopyBuffer(handleMA, 0, 0, rates_total, maBuffer) < rates_total) return prev_calculated;

   for(int i = start; i < rates_total; i++)
   {
      MainBuffer[i] = maBuffer[i];
   }

   return rates_total;
}
