#property strict
#property version   "1.00"
#property description "JARVIS EA Template"

input double RiskPercent = 1.0;
input int StopLossPoints = 200;
input int TakeProfitPoints = 300;

int OnInit()
{
   Print("JARVIS EA template initialized");
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   // TODO: Add strategy-specific signal logic.
}
