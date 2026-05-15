"""
Base MQL5 Custom Indicator templates with placeholders for JARVIS code generation.
"""

INDICATOR_BASE_TEMPLATE = """//+------------------------------------------------------------------+
//| {indicator_name}.mq5                                              |
//| JARVIS AI Trading System                                          |
//| Generated Custom Indicator - {indicator_type}                     |
//+------------------------------------------------------------------+
#property copyright "JARVIS AI Trading System"
#property link      "https://jarvis-trading.ai"
#property version   "1.00"
#property strict

#property indicator_chart_window {chart_window}
#property indicator_buffers {num_buffers}
#property indicator_plots   {num_plots}

{plot_properties}

{custom_inputs}

//--- Indicator buffers
{buffer_declarations}

//--- Internal variables
{custom_globals}

//+------------------------------------------------------------------+
//| Custom indicator initialization function                           |
//+------------------------------------------------------------------+
int OnInit()
{{
{buffer_setup}
{custom_init}
   return(INIT_SUCCEEDED);
}}

//+------------------------------------------------------------------+
//| Custom indicator iteration function                                |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{{
   if(rates_total < {min_bars})
      return(0);

   int start;
   if(prev_calculated == 0)
      start = {min_bars};
   else
      start = prev_calculated - 1;

{calculation_logic}

   return(rates_total);
}}
//+------------------------------------------------------------------+
"""

INDICATOR_MOVING_AVERAGE_LOGIC = """
   for(int i = start; i < rates_total; i++)
   {{
      //--- Simple Moving Average
      double sum = 0.0;
      for(int j = 0; j < InpMAPeriod; j++)
         sum += close[i - j];
      MaBuffer[i] = sum / InpMAPeriod;

      //--- Optional: Signal line (secondary MA)
      if(InpSignalPeriod > 0 && i >= InpSignalPeriod)
      {{
         double sigSum = 0.0;
         for(int j = 0; j < InpSignalPeriod; j++)
            sigSum += MaBuffer[i - j];
         SignalBuffer[i] = sigSum / InpSignalPeriod;
      }}
   }}
"""

INDICATOR_RSI_LOGIC = """
   //--- First calculation
   if(prev_calculated == 0)
   {{
      double sumGain = 0.0, sumLoss = 0.0;
      for(int i = 1; i <= InpRSIPeriod; i++)
      {{
         double change = close[i] - close[i-1];
         if(change > 0) sumGain += change;
         else           sumLoss -= change;
      }}
      AvgGainBuffer[InpRSIPeriod] = sumGain / InpRSIPeriod;
      AvgLossBuffer[InpRSIPeriod] = sumLoss / InpRSIPeriod;

      if(AvgLossBuffer[InpRSIPeriod] != 0)
         RsiBuffer[InpRSIPeriod] = 100.0 - 100.0 / (1.0 + AvgGainBuffer[InpRSIPeriod] / AvgLossBuffer[InpRSIPeriod]);
      else
         RsiBuffer[InpRSIPeriod] = 100.0;

      start = InpRSIPeriod + 1;
   }}

   for(int i = start; i < rates_total; i++)
   {{
      double change = close[i] - close[i-1];
      double gain = (change > 0) ? change : 0.0;
      double loss = (change < 0) ? -change : 0.0;

      AvgGainBuffer[i] = (AvgGainBuffer[i-1] * (InpRSIPeriod - 1) + gain) / InpRSIPeriod;
      AvgLossBuffer[i] = (AvgLossBuffer[i-1] * (InpRSIPeriod - 1) + loss) / InpRSIPeriod;

      if(AvgLossBuffer[i] != 0)
         RsiBuffer[i] = 100.0 - 100.0 / (1.0 + AvgGainBuffer[i] / AvgLossBuffer[i]);
      else
         RsiBuffer[i] = 100.0;
   }}

   //--- Overbought/Oversold levels
   for(int i = start; i < rates_total; i++)
   {{
      OverboughtBuffer[i] = InpOverbought;
      OversoldBuffer[i]   = InpOversold;
   }}
"""

INDICATOR_BOLLINGER_BANDS_LOGIC = """
   for(int i = start; i < rates_total; i++)
   {{
      //--- Middle band (SMA)
      double sum = 0.0;
      for(int j = 0; j < InpBBPeriod; j++)
         sum += close[i - j];
      MiddleBuffer[i] = sum / InpBBPeriod;

      //--- Standard deviation
      double sumSq = 0.0;
      for(int j = 0; j < InpBBPeriod; j++)
      {{
         double diff = close[i - j] - MiddleBuffer[i];
         sumSq += diff * diff;
      }}
      double stdDev = MathSqrt(sumSq / InpBBPeriod);

      //--- Upper and Lower bands
      UpperBuffer[i] = MiddleBuffer[i] + InpBBDeviation * stdDev;
      LowerBuffer[i] = MiddleBuffer[i] - InpBBDeviation * stdDev;
   }}
"""

INDICATOR_ORDER_BLOCKS_LOGIC = """
   for(int i = start; i < rates_total; i++)
   {{
      BullOBBuffer[i] = EMPTY_VALUE;
      BearOBBuffer[i] = EMPTY_VALUE;

      if(i < 3) continue;

      //--- Bullish Order Block: bearish candle followed by strong bullish move
      bool isBearishCandle = close[i-2] < open[i-2];
      bool isBullishFollow = close[i-1] > open[i-1];
      double bearishBody = MathAbs(open[i-2] - close[i-2]);
      double bullishBody = MathAbs(close[i-1] - open[i-1]);

      if(isBearishCandle && isBullishFollow && bullishBody > bearishBody * InpOBStrength)
      {{
         BullOBBuffer[i-2] = low[i-2];
      }}

      //--- Bearish Order Block: bullish candle followed by strong bearish move
      bool isBullishCandle = close[i-2] > open[i-2];
      bool isBearishFollow = close[i-1] < open[i-1];
      double bullBody2 = MathAbs(close[i-2] - open[i-2]);
      double bearBody2 = MathAbs(open[i-1] - close[i-1]);

      if(isBullishCandle && isBearishFollow && bearBody2 > bullBody2 * InpOBStrength)
      {{
         BearOBBuffer[i-2] = high[i-2];
      }}
   }}
"""

INDICATOR_LIQUIDITY_ZONES_LOGIC = """
   for(int i = start; i < rates_total; i++)
   {{
      LiqHighBuffer[i] = EMPTY_VALUE;
      LiqLowBuffer[i]  = EMPTY_VALUE;

      if(i < InpLookback + 1) continue;

      //--- Find swing highs and lows within lookback
      double highestHigh = high[i - 1];
      double lowestLow   = low[i - 1];
      int highIdx = i - 1, lowIdx = i - 1;

      for(int j = 1; j <= InpLookback; j++)
      {{
         if(high[i - j] > highestHigh)
         {{
            highestHigh = high[i - j];
            highIdx = i - j;
         }}
         if(low[i - j] < lowestLow)
         {{
            lowestLow = low[i - j];
            lowIdx = i - j;
         }}
      }}

      //--- Count touches near highs (liquidity pool above)
      int highTouches = 0;
      for(int j = 1; j <= InpLookback; j++)
      {{
         if(MathAbs(high[i - j] - highestHigh) < InpZoneWidth * _Point)
            highTouches++;
      }}

      //--- Count touches near lows (liquidity pool below)
      int lowTouches = 0;
      for(int j = 1; j <= InpLookback; j++)
      {{
         if(MathAbs(low[i - j] - lowestLow) < InpZoneWidth * _Point)
            lowTouches++;
      }}

      if(highTouches >= InpMinTouches)
         LiqHighBuffer[i] = highestHigh;
      if(lowTouches >= InpMinTouches)
         LiqLowBuffer[i] = lowestLow;
   }}
"""

INDICATOR_CUSTOM_OSCILLATOR_LOGIC = """
   for(int i = start; i < rates_total; i++)
   {{
      //--- Calculate momentum component
      double momentum = close[i] - close[i - InpMomentumPeriod];

      //--- Calculate volatility normalization
      double sumRange = 0.0;
      for(int j = 0; j < InpSmoothPeriod; j++)
         sumRange += high[i - j] - low[i - j];
      double avgRange = sumRange / InpSmoothPeriod;

      //--- Normalized oscillator value
      if(avgRange > 0)
         OscBuffer[i] = (momentum / avgRange) * 100.0;
      else
         OscBuffer[i] = 0.0;

      //--- Signal line (EMA of oscillator)
      if(i == start)
         SignalBuffer[i] = OscBuffer[i];
      else
      {{
         double k = 2.0 / (InpSignalPeriod + 1.0);
         SignalBuffer[i] = OscBuffer[i] * k + SignalBuffer[i-1] * (1.0 - k);
      }}

      //--- Histogram
      HistBuffer[i] = OscBuffer[i] - SignalBuffer[i];

      //--- Zero line
      ZeroBuffer[i] = 0.0;
   }}
"""
