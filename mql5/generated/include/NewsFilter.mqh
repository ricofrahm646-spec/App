//+------------------------------------------------------------------+
//| NewsFilter.mqh                                                    |
//| JARVIS AI - News event filter                                     |
//+------------------------------------------------------------------+
#ifndef JARVIS_NEWS_FILTER_MQH
#define JARVIS_NEWS_FILTER_MQH

input group "=== News Filter ==="
input bool   NFInpEnabled         = true;
input int    NFInpMinutesBefore   = 30;
input int    NFInpMinutesAfter    = 30;
input bool   NFInpHighImpactOnly  = true;

struct NewsEvent
{
   datetime time;
   string   currency;
   string   title;
   int      impact;  // 1=Low 2=Medium 3=High
};

NewsEvent g_newsEvents[];
datetime  g_newsLastFetch = 0;

//+------------------------------------------------------------------+
bool IsNewsTime(string symbol = "")
{
   if(!NFInpEnabled) return false;

   datetime now = TimeCurrent();
   string cur1 = "", cur2 = "";

   if(symbol == "") symbol = _Symbol;
   if(StringLen(symbol) >= 6)
   {
      cur1 = StringSubstr(symbol, 0, 3);
      cur2 = StringSubstr(symbol, 3, 3);
   }

   for(int i = 0; i < ArraySize(g_newsEvents); i++)
   {
      NewsEvent& ev = g_newsEvents[i];
      if(NFInpHighImpactOnly && ev.impact < 3) continue;

      if(symbol != "" && ev.currency != cur1 && ev.currency != cur2) continue;

      datetime start = ev.time - NFInpMinutesBefore * 60;
      datetime end   = ev.time + NFInpMinutesAfter  * 60;

      if(now >= start && now <= end)
      {
         Print("News filter active: ", ev.title, " at ", TimeToString(ev.time));
         return true;
      }
   }
   return false;
}

//+------------------------------------------------------------------+
bool AddNewsEvent(datetime evTime, string currency, string title, int impact)
{
   int sz = ArraySize(g_newsEvents);
   ArrayResize(g_newsEvents, sz + 1);
   g_newsEvents[sz].time     = evTime;
   g_newsEvents[sz].currency = currency;
   g_newsEvents[sz].title    = title;
   g_newsEvents[sz].impact   = impact;
   return true;
}

//+------------------------------------------------------------------+
void ClearNewsEvents()
{
   ArrayFree(g_newsEvents);
}

//+------------------------------------------------------------------+
int CountUpcomingNews(int minutesAhead = 60)
{
   datetime now   = TimeCurrent();
   datetime limit = now + minutesAhead * 60;
   int count = 0;
   for(int i = 0; i < ArraySize(g_newsEvents); i++)
   {
      if(g_newsEvents[i].time >= now && g_newsEvents[i].time <= limit)
         count++;
   }
   return count;
}

#endif // JARVIS_NEWS_FILTER_MQH
