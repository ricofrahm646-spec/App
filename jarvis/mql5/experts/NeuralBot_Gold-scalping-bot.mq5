
//+------------------------------------------------------------------+
//|                                              NeuralBot_Gold-scalping-bot.mq5 |
//|                                  Copyright 2024, JARVIS AI |
//|                                             https://jarvis.ai |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, JARVIS AI"
#property link      "https://jarvis.ai"
#property version   "1.00"
#property strict

input double Risk = 1.0;
input int SL = 100;
input int TP = 200;

int OnInit() {
   Print("JARVIS Expert NeuralBot_Gold-scalping-bot Initialized");
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
   Print("JARVIS Expert NeuralBot_Gold-scalping-bot Deinitialized");
}

void OnTick() {
   // AI Generated Logic
   if(iRSI(Symbol(),0,14,PRICE_CLOSE,0) < 30) OrderSend(Symbol(),OP_BUY,0.1,Ask,3,0,0);
}
