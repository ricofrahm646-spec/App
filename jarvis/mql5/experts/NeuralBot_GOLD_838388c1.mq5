
//+------------------------------------------------------------------+
//|                                              NeuralBot_GOLD_838388c1.mq5 |
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
   Print("JARVIS Expert NeuralBot_GOLD_838388c1 Initialized");
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason) {
   Print("JARVIS Expert NeuralBot_GOLD_838388c1 Deinitialized");
}

void OnTick() {

        // Gold Scalping Logic (XAUUSD)
        double rsi = iRSI(Symbol(),0,14,PRICE_CLOSE,0);
        if(rsi < 25) OrderSend(Symbol(),OP_BUY,0.1,Ask,3,Ask-100*_Point,Ask+200*_Point);
        if(rsi > 75) OrderSend(Symbol(),OP_SELL,0.1,Bid,3,Bid+100*_Point,Bid-200*_Point);

}
